import re
import asyncio
from io import BytesIO
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatHistory, ChatRating, SymptomImageAnalysis
from .serializers import (
    ChatHistorySerializer,
    ChatMessageSerializer,
    ChatMessageWithImageSerializer,
    ChatRatingSerializer,
    CallRequestSerializer,
    PrescriptionUploadSerializer,
    PrescriptionChatMessageSerializer,
    TranslateSerializer,
    VoiceUploadSerializer,
    SeveritySerializer,
    SymptomImageAnalysisSerializer,
    SymptomImageUploadSerializer,
    MedicineImageUploadSerializer,
    AutoImageUploadSerializer,
)
from .services import (
    analyze_prescription_image,
    analyze_symptom_image,
    analyze_symptoms_with_gemini,
    analyze_medicine_image,
    normalize_symptom_message,
    build_tablet_suggestions,
    build_severity_prompt_text,
    build_severity_response_text,
    build_severe_care_locations,
    build_prescription_response_text,
    build_medicine_response_text,
    analyze_auto_image_message,
    transcribe_kannada_audio_to_english,
    translate_to_english,
    translate_to_kannada,
    is_twilio_calling_enabled,
    initiate_twilio_callback,
)
LANG_CHOICES = {"en", "kn"}

_TTS_VOICES = {
    "en": getattr(settings, "TTS_VOICE_EN", None) or "en-IN-NeerjaNeural",
    "kn": getattr(settings, "TTS_VOICE_KN", None) or "kn-IN-SapnaNeural",
}


def _synthesize_tts_mp3(text: str, lang: str) -> tuple[bytes, str, str]:
    """Return (mp3_bytes, provider, error).

    - Provider gTTS is attempted first (internet required).
    - Provider edge-tts is a secondary fallback and may be blocked.
    """

    cleaned = str(text or "").strip()
    if not cleaned:
        return b"", "", "empty text"

    resolved = _resolve_lang(lang)
    errors: list[str] = []

    # 1) gTTS
    try:
        from gtts import gTTS

        gtts_lang = "kn" if resolved == "kn" else "en"
        fp = BytesIO()
        gTTS(text=cleaned, lang=gtts_lang, tld="co.in", timeout=20).write_to_fp(fp)
        data = fp.getvalue()
        if data:
            return data, "gTTS", ""
        errors.append("gTTS produced empty audio")
    except Exception as exc:
        errors.append(f"gTTS failed: {exc.__class__.__name__}: {str(exc)[:200]}")

    # 2) edge-tts
    try:
        import edge_tts

        voice = _TTS_VOICES.get(resolved, _TTS_VOICES["en"])

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(cleaned, voice=voice)
            buf = BytesIO()
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    buf.write(chunk.get("data") or b"")
            return buf.getvalue()

        data = asyncio.run(_run())
        if data:
            return data, "edge-tts", ""
        errors.append("edge-tts produced empty audio")
    except Exception as exc:
        errors.append(f"edge-tts failed: {exc.__class__.__name__}: {str(exc)[:200]}")

    return b"", "", "; ".join(errors) or "unknown"


class TextToSpeechView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = str(request.data.get("text") or "")
        lang = _resolve_lang(request.data.get("lang"))

        if len(text) > 1200:
            return Response({"detail": "Text too long."}, status=status.HTTP_400_BAD_REQUEST)

        audio, provider, synth_error = _synthesize_tts_mp3(text, lang)
        if not audio:
            return Response(
                {
                    "detail": f"Could not synthesize audio. Ensure backend has internet access. ({synth_error})",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        resp = HttpResponse(audio, content_type="audio/mpeg")
        if provider:
            resp["X-TTS-Provider"] = provider
        resp["Cache-Control"] = "no-store"
        return resp



_KANNADA_HINTS = {
    "\u0cae\u0cca\u0ca3\u0c95\u0cbe\u0cb2\u0cc1 \u0ca8\u0ccb\u0cb5\u0cc1": "knee pain",
    "\u0cae\u0cca\u0ca3\u0c95\u0cbe\u0cb2\u0cc1 \u0cb5\u0cc7\u0ca6\u0ca8\u0cc6": "knee pain",
    "\u0c95\u0cbe\u0cb2\u0cc1 \u0ca8\u0ccb\u0cb5\u0cc1": "leg pain",
    "\u0cb8\u0c82\u0ca7\u0cbf \u0ca8\u0ccb\u0cb5\u0cc1": "joint pain",
    "\u0cac\u0cc6\u0ca8\u0ccd\u0ca8\u0cc1 \u0ca8\u0ccb\u0cb5\u0cc1": "back pain",
    "\u0c95\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0c97\u0cc6 \u0ca8\u0ccb\u0cb5\u0cc1": "neck pain",
    "\u0ca4\u0cb2\u0cc6\u0ca8\u0ccb\u0cb5\u0cc1": "headache",
    "\u0c9c\u0ccd\u0cb5\u0cb0": "fever",
    "\u0c95\u0cc6\u0cae\u0ccd\u0cae\u0cc1": "cough",
    "\u0c97\u0c82\u0c9f\u0cb2\u0cc1 \u0ca8\u0ccb\u0cb5\u0cc1": "sore throat",
    "\u0cb9\u0cca\u0c9f\u0ccd\u0c9f\u0cc6 \u0ca8\u0ccb\u0cb5\u0cc1": "stomach pain",
    "\u0cb9\u0cca\u0c9f\u0ccd\u0c9f\u0cc6\u0ca8\u0ccb\u0cb5\u0cc1": "stomach pain",
    "\u0cb5\u0cbe\u0cae\u0cbf\u0ca4\u0cbf": "vomiting",
    "\u0cb5\u0cbe\u0cae\u0cbf\u0ca4\u0cbf\u0c82\u0c97\u0ccd": "vomiting",
    "\u0cae\u0ccb\u0c95\u0ccd\u0c95\u0cc1 \u0ca8\u0cc0\u0cb0\u0cc1": "runny nose",
    "\u0ca6\u0cc1\u0cb0\u0ccd\u0cac\u0cb2\u0ca4\u0cc6": "weakness",
    "\u0ca4\u0cb2\u0cc6 \u0cb8\u0cc1\u0ca4\u0ccd\u0ca4\u0cc1\u0ca4\u0ccd\u0ca4\u0cbf\u0ca6\u0cc6": "dizziness",
}

_ROMAN_KANNADA_PATTERNS = [
    # Stomach / abdomen
    (re.compile(r"\bho+t+t+e\s*no+vu\b", re.IGNORECASE), "stomach pain"),
    (re.compile(r"\bho+t+e\s*novu\b", re.IGNORECASE), "stomach pain"),
    (re.compile(r"\budar(a)?\s*no+vu\b", re.IGNORECASE), "abdominal pain"),
    (re.compile(r"\budar(a)?\s*novu\b", re.IGNORECASE), "abdominal pain"),
    (re.compile(r"\bogara\s*no+vu\b", re.IGNORECASE), "gastric pain"),

    # Fever / cold / cough
    (re.compile(r"\bj(?:v|w)a+ra\b", re.IGNORECASE), "fever"),
    (re.compile(r"\bj(?:v|w)a+r\b", re.IGNORECASE), "fever"),
    (re.compile(r"\btemperature\b", re.IGNORECASE), "fever"),
    (re.compile(r"\bkem+mu\b", re.IGNORECASE), "cough"),
    (re.compile(r"\bko+l+u\b", re.IGNORECASE), "cold"),
    (re.compile(r"\bsardi\b", re.IGNORECASE), "cold"),
    (re.compile(r"\bmooku\s*ne+ru\b", re.IGNORECASE), "runny nose"),
    (re.compile(r"\bmooku\s*bee+su\b", re.IGNORECASE), "blocked nose"),
    (re.compile(r"\bganta(lu)?\s*no+vu\b", re.IGNORECASE), "sore throat"),
    (re.compile(r"\bthroat\s*pain\b", re.IGNORECASE), "sore throat"),

    # Head / body pain
    (re.compile(r"\btale\s*no+vu\b", re.IGNORECASE), "headache"),
    (re.compile(r"\btalai\s*no+vu\b", re.IGNORECASE), "headache"),
    (re.compile(r"\bhead\s*ache\b", re.IGNORECASE), "headache"),
    (re.compile(r"\bshari+ra\s*no+vu\b", re.IGNORECASE), "body ache"),
    (re.compile(r"\bde+ha\s*no+vu\b", re.IGNORECASE), "body ache"),

    # Back / leg / joints
    (re.compile(r"\bben+nu\s*no+vu\b", re.IGNORECASE), "back pain"),
    (re.compile(r"\bben+no+vu\b", re.IGNORECASE), "back pain"),
    (re.compile(r"\bka+lu\s*no+vu\b", re.IGNORECASE), "leg pain"),
    (re.compile(r"\bka+lun?o+vu\b", re.IGNORECASE), "leg pain"),
    (re.compile(r"\bka+lu\s*veda(ne)?\b", re.IGNORECASE), "leg pain"),
    (re.compile(r"\bsandhi\s*no+vu\b", re.IGNORECASE), "joint pain"),
    (re.compile(r"\bmoka+\s*ka+lu\s*no+vu\b", re.IGNORECASE), "knee pain"),
    (re.compile(r"\bnee\s*pain\b", re.IGNORECASE), "knee pain"),

    # GI symptoms
    (re.compile(r"\bvamit(ing)?\b", re.IGNORECASE), "vomiting"),
    (re.compile(r"\bul+ti\b", re.IGNORECASE), "vomiting"),
    (re.compile(r"\bvomit\b", re.IGNORECASE), "vomiting"),
    (re.compile(r"\bdiarr(h)?ea\b", re.IGNORECASE), "diarrhea"),
    (re.compile(r"\bloose\s*motion\b", re.IGNORECASE), "diarrhea"),
    (re.compile(r"\bnaus(ea)?\b", re.IGNORECASE), "nausea"),

    # Breathing / chest
    (re.compile(r"\bswa+sa\s*ka+shta\b", re.IGNORECASE), "breathing difficulty"),
    (re.compile(r"\bswa+sa\s*sa+nkata\b", re.IGNORECASE), "breathing difficulty"),
    (re.compile(r"\bbreath(ing)?\s*(problem|difficulty)\b", re.IGNORECASE), "breathing difficulty"),
    (re.compile(r"\bede\s*no+vu\b", re.IGNORECASE), "chest pain"),
    (re.compile(r"\bchest\s*pain\b", re.IGNORECASE), "chest pain"),

    # General
    (re.compile(r"\bta+le\s*sut+t+u\b", re.IGNORECASE), "dizziness"),
    (re.compile(r"\bdi+z+iness\b", re.IGNORECASE), "dizziness"),
    (re.compile(r"\bba+la+hi+na\b", re.IGNORECASE), "weakness"),
]





def _augment_with_kannada_hints(message: str) -> str:
    message = str(message or "")
    additions = [en for kn, en in _KANNADA_HINTS.items() if kn and kn in message]
    lowered = message.lower()
    for pattern, en in _ROMAN_KANNADA_PATTERNS:
        if pattern.search(lowered):
            additions.append(en)
    if not additions:
        return message
    seen = set()
    unique = []
    for item in additions:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return message + " " + " ".join(unique)


def _resolve_lang(value: str) -> str:
    value = str(value or "").strip().lower()
    return value if value in LANG_CHOICES else "en"


def _prepare_message_for_analysis(message: str) -> str:
    message = str(message or "").strip()
    if not message:
        return ""

    hinted = _augment_with_kannada_hints(message)
    if hinted != message:
        return hinted

    if re.search(r"[^\\x00-\\x7F]", message):
        translated = translate_to_english(message)
        if translated and not re.search(r"[^\\x00-\\x7F]", translated):
            return translated
        return translated or message

    return message


def _localize_response_text(response_text_en: str, lang: str) -> tuple[str, str]:
    if lang == "kn":
        response_kn = translate_to_kannada(response_text_en)
        return response_kn, response_kn
    return response_text_en, response_text_en

class SymptomPredictionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]
        message = normalize_symptom_message(message)

        analysis_message = _prepare_message_for_analysis(message)


        result = analyze_symptoms_with_gemini(analysis_message)
        return Response(
            {
                "message": message,
                "predicted_disease": result["predicted_disease"],
                "tablets": result["tablets"],
                "tablet_suggestions": build_tablet_suggestions(result.get("tablets", ""), result.get("predicted_disease", "")),
                "advice": result["advice"],
            },
            status=status.HTTP_200_OK,
        )


class ChatbotMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = ChatMessageWithImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]
        message = normalize_symptom_message(message)
        image = serializer.validated_data.get("image")

        lang = _resolve_lang(serializer.validated_data.get("lang"))
        analysis_message = _prepare_message_for_analysis(message)
        if image is not None:
            content_type = getattr(image, "content_type", "")
            if content_type and not content_type.startswith("image/"):
                return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
            if getattr(image, "size", 0) and image.size > 5 * 1024 * 1024:
                return Response({"detail": "Image must be 5MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)
        result = analyze_symptoms_with_gemini(analysis_message)
        response_text_en = build_severity_prompt_text(result["predicted_disease"])
        response_text, speech_text = _localize_response_text(response_text_en, lang)
        chat = ChatHistory.objects.create(
            user=request.user,
            message=message,
            image=image,
            response=response_text,
            predicted_disease=result["predicted_disease"],
            advice=result["advice"],
        )

        image_url = None
        if getattr(chat, "image", None):
            try:
                image_url = request.build_absolute_uri(chat.image.url)
            except ValueError:
                image_url = None

        return Response(
            {
                "chat_id": chat.id,
                "message": message,
                "image_url": image_url,
                "predicted_disease": result["predicted_disease"],
                "tablets": result["tablets"],
                "tablet_suggestions": build_tablet_suggestions(result.get("tablets", ""), result.get("predicted_disease", "")),
                "advice": result["advice"],
                "response": response_text,
                "speech_text": speech_text,

                "care_locations": [],
                "response_lang": lang,
                "speech_lang": lang,
                "pending_severity": True,
                "severity_options": ["mild", "moderate", "severe"],
            },
            status=status.HTTP_200_OK,
        )


class ChatHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        history = ChatHistory.objects.filter(user=request.user)[:50]
        return Response(ChatHistorySerializer(history, many=True, context={"request": request}).data)

    def delete(self, request):
        deleted_count, _ = ChatHistory.objects.filter(user=request.user).delete()
        return Response({"deleted": deleted_count}, status=status.HTTP_200_OK)


class SymptomImageAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = SymptomImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data["image"]
        category = serializer.validated_data["category"]
        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
        result = analyze_symptom_image(image, category)
        image.seek(0)

        analysis = SymptomImageAnalysis.objects.create(
            user=request.user,
            image=image,
            category=category,
            assessment=result["assessment"],
            confidence=result["confidence"],
            guidance=result["guidance"],
        )

        return Response(SymptomImageAnalysisSerializer(analysis).data, status=status.HTTP_201_CREATED)




class PrescriptionHelperView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PrescriptionUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data["image"]
        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(image, "size", 0) and image.size > 5 * 1024 * 1024:
            return Response({"detail": "Image must be 5MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        result = analyze_prescription_image(image, user_context="")
        return Response(result, status=status.HTTP_200_OK)



class TranslateToEnglishView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TranslateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]
        text_en = translate_to_english(text)
        return Response({"text_en": text_en}, status=status.HTTP_200_OK)


class VoiceChatMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VoiceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lang = _resolve_lang(serializer.validated_data.get("lang"))
        audio = serializer.validated_data["audio"]
        content_type = getattr(audio, "content_type", "")
        if content_type and not content_type.startswith("audio/"):
            return Response({"detail": "Please upload a valid audio file."}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(audio, "size", 0) and audio.size > 10 * 1024 * 1024:
            return Response({"detail": "Audio must be 10MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        transcript_en = transcribe_kannada_audio_to_english(audio)
        transcript_en = normalize_symptom_message(transcript_en)
        if not transcript_en:
            return Response(
                {"detail": "Could not transcribe the audio. Please try again, or use the mic button."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = analyze_symptoms_with_gemini(transcript_en)
        response_text_en = build_severity_prompt_text(result["predicted_disease"])
        response_text, speech_text = _localize_response_text(response_text_en, lang)
        chat = ChatHistory.objects.create(
            user=request.user,
            message=transcript_en,
            response=response_text,
            predicted_disease=result["predicted_disease"],
            advice=result["advice"],
        )

        return Response(
            {
                "chat_id": chat.id,
                "transcript_en": transcript_en,
                "predicted_disease": result["predicted_disease"],
                "tablets": result["tablets"],
                "tablet_suggestions": build_tablet_suggestions(result.get("tablets", ""), result.get("predicted_disease", "")),
                "advice": result["advice"],
                "response": response_text,
                "speech_text": speech_text,

                "response_lang": lang,
                "speech_lang": lang,
                "pending_severity": True,
                "severity_options": ["mild", "moderate", "severe"],
            },
            status=status.HTTP_200_OK,
        )




class SeverityResponseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SeveritySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat_id = serializer.validated_data["chat_id"]
        severity = serializer.validated_data["severity"]



        lang = _resolve_lang(serializer.validated_data.get("lang"))
        try:
            chat = ChatHistory.objects.get(id=chat_id, user=request.user)
        except ChatHistory.DoesNotExist:
            return Response({"detail": "Chat not found."}, status=status.HTTP_404_NOT_FOUND)

        analysis_message = _prepare_message_for_analysis(chat.message)
        result = analyze_symptoms_with_gemini(analysis_message)
        response_text_en = build_severity_response_text(result, severity)
        response_text, speech_text = _localize_response_text(response_text_en, lang)

        care_locations = build_severe_care_locations(result.get("message", ""), result.get("predicted_disease", "")) if severity == "severe" else []

        chat.response = response_text
        chat.predicted_disease = result["predicted_disease"]
        chat.advice = result["advice"]
        chat.save(update_fields=["response", "predicted_disease", "advice"])

        return Response(
            {
                "chat_id": chat.id,
                "severity": severity,
                "predicted_disease": result["predicted_disease"],
                "tablets": result["tablets"],
                "tablet_suggestions": build_tablet_suggestions(result.get("tablets", ""), result.get("predicted_disease", "")),
                "advice": result["advice"],
                "response": response_text,
                "speech_text": speech_text,


                "care_locations": care_locations,
                "response_lang": lang,
                "speech_lang": lang,
            },
            status=status.HTTP_200_OK,
        )





class AutoImageMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AutoImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lang = _resolve_lang(serializer.validated_data.get("lang"))
        message = (serializer.validated_data.get("message") or "").strip() or "Image uploaded."
        image = serializer.validated_data["image"]

        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(image, "size", 0) and image.size > 5 * 1024 * 1024:
            return Response({"detail": "Image must be 5MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        result = analyze_auto_image_message(image, message=message)
        image.seek(0)

        ok = bool(result.get("ok"))
        needs_reupload = bool(result.get("needs_reupload"))
        kind = str(result.get("kind") or "other")

        response_text = str(result.get("response_text") or "").strip()
        if not response_text:
            response_text = str(result.get("detail") or "Couldn't analyze the image. Please type a short description (symptoms/tablet name).").strip() or "Couldn't analyze the image. Please type a short description (symptoms/tablet name)."

        speech_text = str(result.get("speech_text") or "").strip() or None

        if lang == "kn":
            response_text = speech_text or translate_to_kannada(response_text)
            speech_text = response_text
        else:
            speech_text = response_text
        # Store successful analyses only.
        chat_id = None
        image_url = None
        if ok:
            chat = ChatHistory.objects.create(
                user=request.user,
                message=message,
                image=image,
                response=response_text,
                predicted_disease=f"Image: {kind}",
                advice="",
            )
            chat_id = chat.id
            if getattr(chat, "image", None):
                try:
                    image_url = request.build_absolute_uri(chat.image.url)
                except ValueError:
                    image_url = None

        return Response(
            {
                "ok": ok,
                "needs_reupload": needs_reupload,
                "kind": kind,
                "chat_id": chat_id,
                "message": message,
                "image_url": image_url,
                "response": response_text,
                "speech_text": speech_text,

                "response_lang": lang,
                "speech_lang": lang,
            },
            status=status.HTTP_200_OK,
        )

class MedicineChatMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = MedicineImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lang = _resolve_lang(serializer.validated_data.get("lang"))
        message = (serializer.validated_data.get("message") or "").strip() or "Medicine image uploaded."
        image = serializer.validated_data["image"]

        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(image, "size", 0) and image.size > 5 * 1024 * 1024:
            return Response({"detail": "Image must be 5MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        result = analyze_medicine_image(image, hint_text=message)
        image.seek(0)

        # If unclear, do not store it as chat history to avoid polluting history.
        if not result.get("ok") and result.get("needs_reupload"):
            return Response({"detail": str(result.get("detail") or "Please upload a clearer cover/label photo.")}, status=status.HTTP_400_BAD_REQUEST)

        response_text_en = build_medicine_response_text(result)
        response_text, speech_text = _localize_response_text(response_text_en, lang)

        chat = ChatHistory.objects.create(
            user=request.user,
            message=message,
            image=image,
            response=response_text,
            predicted_disease="Medicine Identification",
            advice=str(result.get("uses") or ""),
        )

        image_url = None
        if getattr(chat, "image", None):
            try:
                image_url = request.build_absolute_uri(chat.image.url)
            except ValueError:
                image_url = None

        return Response(
            {
                "chat_id": chat.id,
                "message": message,
                "image_url": image_url,
                "response": response_text,
                "speech_text": speech_text,

                "response_lang": lang,
                "speech_lang": lang,
                "medicine_name": result.get("medicine_name"),
                "uses": result.get("uses"),
                "food_timing": result.get("food_timing"),
                "confidence": result.get("confidence"),
            },
            status=status.HTTP_200_OK,
        )

class PrescriptionChatMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PrescriptionChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lang = _resolve_lang(serializer.validated_data.get("lang"))
        message = (serializer.validated_data.get("message") or "").strip() or "Prescription image uploaded."
        image = serializer.validated_data["image"]

        content_type = getattr(image, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            return Response({"detail": "Please upload a valid image file."}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(image, "size", 0) and image.size > 5 * 1024 * 1024:
            return Response({"detail": "Image must be 5MB or smaller."}, status=status.HTTP_400_BAD_REQUEST)

        result = analyze_prescription_image(image, user_context=message)
        response_text_en = build_prescription_response_text(result)
        response_text, speech_text = _localize_response_text(response_text_en, lang)

        chat = ChatHistory.objects.create(
            user=request.user,
            message=message,
            image=image,
            response=response_text,
            predicted_disease="Prescription Review",
            advice=(result.get("summary") or ""),
        )

        image_url = None
        if getattr(chat, "image", None):
            try:
                image_url = request.build_absolute_uri(chat.image.url)
            except ValueError:
                image_url = None

        return Response(
            {
                "chat_id": chat.id,
                "message": message,
                "image_url": image_url,
                "response": response_text,
                "speech_text": speech_text,

                "response_lang": lang,
                "speech_lang": lang,
            },
            status=status.HTTP_200_OK,
        )
class ChatRatingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChatRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat = serializer.validated_data["chat"]

        if chat.user_id != request.user.id:
            return Response({"detail": "You can rate only your own chats."}, status=status.HTTP_403_FORBIDDEN)

        rating, created = ChatRating.objects.update_or_create(
            user=request.user,
            chat=chat,
            defaults={
                "rating": serializer.validated_data["rating"],
                "feedback": serializer.validated_data.get("feedback", ""),
            },
        )

        return Response(
            {"created": created, "rating": ChatRatingSerializer(rating).data},
            status=status.HTTP_200_OK,
        )


class EmergencyCallConfigView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        phone_number = getattr(settings, "EMERGENCY_CALL_NUMBER", "").strip()
        return Response(
            {
                "phone_number": phone_number,
                "call_enabled": bool(phone_number),
                "callback_enabled": is_twilio_calling_enabled(),
                "provider": "twilio" if is_twilio_calling_enabled() else "",
            },
            status=status.HTTP_200_OK,
        )


class InitiateHelpCallView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not is_twilio_calling_enabled():
            return Response({"detail": "Calling provider is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = CallRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_number = serializer.validated_data["phone_number"]

        allowlist = getattr(settings, "CALLBACK_ALLOWLIST", []) or []
        if allowlist and to_number not in allowlist:
            return Response({"detail": "This number is not allowed for callback in this environment."}, status=status.HTTP_403_FORBIDDEN)

        cooldown = int(getattr(settings, "CALLBACK_RATE_LIMIT_SECONDS", 120) or 120)
        key = f"callback:{request.user.id}"
        if cache.get(key):
            return Response({"detail": "Please wait before requesting another call."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.set(key, True, timeout=cooldown)

        bridge_to = getattr(settings, "TWILIO_BRIDGE_TO_NUMBER", "").strip() or None
        result = initiate_twilio_callback(to_number, bridge_to=bridge_to)
        if not result.get("ok"):
            return Response({"detail": result.get("detail", "Call failed.")}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result, status=status.HTTP_200_OK)





