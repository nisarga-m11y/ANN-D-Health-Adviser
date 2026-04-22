import base64
import json
import mimetypes
import pickle
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import requests
from django.conf import settings

from .nlp_utils import preprocess_text

from .medicine_image_match import match_uploaded_medicine_image
from .medicine_guide import build_medicine_safety_note, get_food_timing_for_image_key

DISCLAIMER_EN = (
    "This is not a medical diagnosis. If symptoms are severe, sudden, or worsening, seek urgent medical care."
)

_DOUBLE_QUOTED_ITEMS_RE = re.compile(r'"([^"\\]{1,120})"')
_SINGLE_QUOTED_ITEMS_RE = re.compile(r"'([^'\\]{1,120})'")



def normalize_symptom_message(message: str) -> str:
    """Normalize symptom text that sometimes arrives as a quoted list (often from speech/LLM output),
    e.g. `"headache", "nausea", "vomiting"` or `["headache", "nausea"]`.
    Keeps normal sentences unchanged as much as possible.
    """

    text = str(message or "").strip()
    if not text:
        return ""

    stripped = text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            items = [str(item).strip() for item in parsed if str(item).strip()]
            if items:
                return ", ".join(items)

    double_items = _DOUBLE_QUOTED_ITEMS_RE.findall(text)
    if len(double_items) >= 2:
        return ", ".join(item.strip() for item in double_items if item.strip())

    single_items = _SINGLE_QUOTED_ITEMS_RE.findall(text)
    if len(single_items) >= 2:
        return ", ".join(item.strip() for item in single_items if item.strip())

    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    return re.sub(r"\s+", " ", text).strip()




def guess_image_kind_from_message(message: str) -> str:
    """Best-effort routing based on the user's text when image-only classification fails."""

    raw = preprocess_text(message or "")
    tokens = set(t for t in raw.split() if t)
    joined = f" {raw} "

    # Skin/external
    skin_terms = {
        "rash",
        "rashes",
        "itch",
        "itching",
        "redness",
        "red",
        "spots",
        "patch",
        "pimple",
        "pimples",
        "acne",
        "eczema",
        "allergy",
        "hives",
        "skin",
        "face",
        "cheek",
    }
    if tokens.intersection(skin_terms):
        return "skin_rash"

    # Eye
    eye_terms = {"eye", "eyes", "conjunctivitis", "watery", "itchy"}
    if tokens.intersection(eye_terms) and ("eye" in joined or "eyes" in joined):
        return "eye_redness"

    # Prescription
    if any(t in tokens for t in {"prescription", "rx", "doctor"}) or "prescription" in joined:
        return "prescription"

    # Medicine/tablet
    med_terms = {"tablet", "tablets", "pill", "medicine", "med", "capsule", "strip"}
    if tokens.intersection(med_terms):
        return "medicine"

    return "other"
LOCAL_MODEL_DIR = Path(__file__).resolve().parents[3] / "ml"
LOCAL_MODEL_PATH = LOCAL_MODEL_DIR / "model.pkl"
LOCAL_VECTORIZER_PATH = LOCAL_MODEL_DIR / "vectorizer.pkl"
LOCAL_LABEL_ENCODER_PATH = LOCAL_MODEL_DIR / "label_encoder.pkl"


@lru_cache(maxsize=1)
def _load_local_symptom_model():
    if not (LOCAL_MODEL_PATH.exists() and LOCAL_VECTORIZER_PATH.exists() and LOCAL_LABEL_ENCODER_PATH.exists()):
        return None

    try:
        with open(LOCAL_MODEL_PATH, "rb") as handle:
            model = pickle.load(handle)
        with open(LOCAL_VECTORIZER_PATH, "rb") as handle:
            vectorizer = pickle.load(handle)
        with open(LOCAL_LABEL_ENCODER_PATH, "rb") as handle:
            encoder = pickle.load(handle)
    except OSError:
        return None
    except pickle.UnpicklingError:
        return None

    return model, vectorizer, encoder


def _predict_with_local_model(message: str) -> Dict[str, Any] | None:
    bundle = _load_local_symptom_model()
    if bundle is None:
        return None

    model, vectorizer, encoder = bundle
    clean = preprocess_text(message or "")
    if not clean.strip():
        return None

    try:
        x = vectorizer.transform([clean])
        y = model.predict(x)[0]
        label = encoder.inverse_transform([y])[0]
        confidence = 0.55
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x)[0]
            confidence = float(max(proba))
    except Exception:
        return None

    return {
        "predicted_disease": str(label).strip() or "General Symptom Review",
        "confidence": confidence,
    }


FALLBACK_PROFILES = [
    {
        "keywords": ["knee pain", "knee ache", "joint pain"],
        "predicted_disease": "Knee Joint Inflammation Pattern",
        "confidence": 0.67,
        "tablets": "Topical diclofenac gel or acetaminophen may help mild knee pain if medically suitable. Anti-inflammatory tablets (like ibuprofen/naproxen) only if suitable for you and per label directions.",
        "natural_medicine": "Warm compress, light knee stretches, and avoid stairs/heavy load.",
        "advice": "Seek care if swelling, redness, locking, or inability to bear weight develops.",
    },
    {
        "keywords": ["back pain", "neck pain", "muscle pain", "body pain", "body ache"],
        "predicted_disease": "Musculoskeletal Strain Pattern",
        "confidence": 0.64,
        "tablets": "Ibuprofen, Diclofenac or naproxen may help inflammatory muscle pain only if medically suitable.",
        "natural_medicine": "Posture correction, warm compress, gentle stretching, and hydration.",
        "advice": "Consult a doctor for persistent pain, numbness, weakness, or radiating pain.",
    },
    {
        "keywords": ["migraine", "headache", "head ache", "head pain", "headpain"],
        "predicted_disease": "Migraine or Tension Headache Pattern",
        "confidence": 0.69,
        "min_score": 2,
        "tablets": "Acetaminophen or ibuprofen may help headache if medically suitable. Prescription migraine medicines (e.g., triptans/gepants) should be used only if already prescribed.",
        "natural_medicine": "Rest in a dark room, hydration, and reduced screen exposure.",
        "advice": "Urgent care is needed for worst headache of life, confusion, or neurological symptoms.",
    },
    {
        "keywords": ["throat infection", "sore throat", "throat pain", "tonsil", "swallowing pain"],
        "predicted_disease": "Upper Throat Infection Pattern",
        "confidence": 0.63,
        "tablets": "Lozenges & sprays may help throat pain if medically suitable. Antibiotics like amoxicillin/penicillin only if prescribed by a doctor.",
        "natural_medicine": "Warm saline gargles, warm fluids, and voice rest.",
        "advice": "Consult a doctor if swallowing becomes difficult or fever persists.",
    },
    {
        "keywords": ["fever"],
        "predicted_disease": "Flu-like Illness Pattern",
        "confidence": 0.62,
        "tablets": "Tylenol,Crocin,Dolo-650,Paracetamol for fever may help if medically suitable.",
        "natural_medicine": "Coriander seed water: boil 1 teaspoon coriander seeds in 1 cup water, strain and drink warm. Rest and regular hydration.",
        "advice": "Consult a doctor if fever lasts over 48 hours or breathing worsens.",
    },
    {
        "keywords": ["cough"],
        "predicted_disease": "Common cough",
        "confidence": 0.62,
        "tablets": "Paracetamol, cetirizine for runny nose may help if medically suitable.",
        "natural_medicine": "Tulsi (Holy Basil) leaves, ginger tea, turmeric milk.",
        "advice": "Consult a doctor if cough lasts over 10-14 days, breathing worsens, or chest pain occurs.",
    },
    {
        "keywords": ["cold"],
        "predicted_disease": "Common cold",
        "confidence": 0.62,
        "tablets": "Cetirizine,Cipla,Cold Act for runny nose may help if medically suitable.",
        "natural_medicine": "Warm Salt Water Gargle,Mix a pinch of black pepper powder with 1 teaspoon honey,Take 2 times a day to reduce cold.",
        "advice": "Consult a doctor if fever lasts over 48 hours or breathing worsens.",
    },
    {
        "keywords": ["acidity", "gas", "bloating", "stomach pain", "indigestion", "burning"],
        "predicted_disease": "Gastric Irritation Pattern",
        "confidence": 0.58,
        "tablets": "Antacids (calcium carbonate or alginate-based) may help temporarily if suitable.",
        "natural_medicine": "Small bland meals, avoid spicy food, and avoid late-night meals.",
        "advice": "Consult a doctor for persistent pain, vomiting, blood in stool, or severe burning.",
    },
    {
        "keywords": ["i am felling tired", "i am feeling tired", "feeling tired", "tired", "fatigue"],
        "predicted_disease": "Vitamin Deficiency",
        "confidence": 0.60,
        "tablets": "If diet is poor, a basic multivitamin may help, but long-lasting tiredness needs a checkup and possible blood tests.",
        "natural_medicine": "Get enough sleep, drink water, eat nutritious food.",
        "advice": "Consult a doctor if tiredness persists more than 1-2 weeks or is severe.",
    },
    {
        "keywords": ["stomach burning"],
        "predicted_disease": "Gastric Irritation Pattern",
        "confidence": 0.58,
        "tablets": "Antacids (calcium carbonate or alginate-based) may help temporarily if suitable.",
        "natural_medicine": "Small bland meals, avoid spicy food, and avoid late-night meals.",
        "advice": "Consult a doctor for persistent pain, vomiting, blood in stool, or severe burning.",
    },
    {
        "keywords": ["diarrhea", "loose motion", "vomiting", "stomach upset"],
        "predicted_disease": "Acute Gastroenteritis Pattern",
        "confidence": 0.66,
        "tablets": "ORS (oral rehydration solution) is most important. Probiotics may help some people if medically suitable. Avoid anti-diarrheal tablets if you have fever, blood in stool, or severe abdominal pain.",
        "natural_medicine": "Drink plenty of fluids (ORS/coconut water), and eat light foods like rice/banana/toast.",
        "advice": "Consult a doctor if dehydration, persistent vomiting, blood in stool, or high fever occurs.",
    },
    {
        "keywords": [
            "stomach pain",
            "stomach cramps",
            "vomiting",
            "food poisoning",
            "ate outside",
            "bad food",
            "spoiled food",
            "diarrhea",
        ],
        "predicted_disease": "Food Poisoning Pattern",
        "confidence": 0.66,
        "min_score": 4,
        "tablets": "ORS solution is most important. Probiotics may help if medically suitable.",
        "natural_medicine": "Drink plenty of fluids (ORS/coconut water), and eat light foods like rice and banana.",
        "advice": "Consult a doctor if dehydration, persistent vomiting, blood in stool, or high fever occurs.",
    },
    {
        "keywords": ["itching", "skin rash", "redness", "allergy", "sneezing"],
        "predicted_disease": "Allergic Reaction Pattern",
        "confidence": 0.65,
        "tablets": "Cetirizine or loratadine may help relieve allergy symptoms if medically suitable.",
        "natural_medicine": "Avoid suspected allergens, keep skin cool/clean, and use a cold compress for itching.",
        "advice": "Seek urgent care if swelling of face/lips, wheezing, or breathing difficulty occurs.",
    },
    {
        "keywords": ["blocked nose", "nose blocked", "nose block", "stuffy nose", "nasal congestion", "sinus pain", "sinus", "headache with cold", "cold headache", "head ache with cold", "head ache and cold"],
        "predicted_disease": "Sinus Infection Pattern",
        "confidence": 0.64,
        "tablets": "Decongestants or steam inhalation may help if medically suitable.",
        "natural_medicine": "Steam inhalation, warm fluids, saline nasal rinse/spray, and rest.",
        "advice": "Consult a doctor if symptoms last more than 7-10 days, fever is high, or symptoms worsen.",
    },
    {
        "keywords": ["pain burning urination", "burning urination", "frequent urination", "lower abdominal pain", "urine pain"],
        "predicted_disease": "Urinary Tract Infection Pattern",
        "confidence": 0.67,
        "tablets": "Avoid antibiotics without a doctor's prescription. A urine test may be needed to choose the right treatment.",
        "natural_medicine": "Drink plenty of water, avoid holding urine, and maintain hygiene.",
        "advice": "Consult a doctor if fever, back/flank pain, vomiting, pregnancy, or blood in urine occurs.",
    },
    {
        "keywords": ["dizziness", "weakness", "pale skin", "low hemoglobin", "fatigue dizziness"],
        "predicted_disease": "Possible Iron Deficiency Pattern",
        "confidence": 0.68,
        "tablets": "Iron supplements should be taken only after a blood test and a doctor's advice.",
        "natural_medicine": "Eat iron-rich foods (spinach/beans/meat if applicable), plus vitamin-C rich foods to improve absorption.",
        "advice": "Consult a doctor for confirmation and treatment plan, especially if symptoms are significant.",
    },
    {
        "keywords": ["chest pain", "tightness", "left arm pain", "sweating", "pressure in chest"],
        "predicted_disease": "Possible Cardiac Event",
        "confidence": 0.85,
        "tablets": "Do not self-medicate.",
        "natural_medicine": "None",
        "advice": "Emergency: seek immediate medical attention now (call your local emergency number or go to the nearest hospital).",
    },
    {
        "keywords": ["stress", "anxiety", "overthinking", "cannot sleep", "can't sleep", "panic"],
        "predicted_disease": "Stress / Anxiety Pattern",
        "confidence": 0.62,
        "tablets": "If symptoms are frequent or severe, talk to a doctor/therapist. Avoid starting sedatives on your own.",
        "natural_medicine": "Breathing exercises, short walks, reduced caffeine at night, and a consistent sleep routine.",
        "advice": "Seek help urgently if you have thoughts of self-harm or feel unsafe.",
    },
    {
        "keywords": ["eye redness", "itchy eyes", "watery eyes", "red eye"],
        "predicted_disease": "Eye Irritation / Conjunctivitis Pattern",
        "confidence": 0.63,
        "tablets": "Artificial tears may help irritation. Use medicated eye drops only if prescribed or advised by a clinician.",
        "natural_medicine": "Avoid touching eyes, wash hands, and rinse with clean water if irritant exposure is suspected.",
        "advice": "Consult a doctor if pain, vision changes, thick discharge, or contact lens use is involved.",
    },
    {
        "keywords": ["tooth pain", "gum swelling", "tooth sensitivity", "toothache"],
        "predicted_disease": "Dental Pain / Possible Infection Pattern",
        "confidence": 0.66,
        "tablets": "Acetaminophen or ibuprofen may help pain temporarily if medically suitable.",
        "natural_medicine": "Warm salt-water rinse and maintain oral hygiene. Avoid chewing on the painful side.",
        "advice": "See a dentist soon, especially if swelling, fever, or worsening pain occurs.",
    },
    {
        "keywords": ["period pain", "menstrual cramps", "irregular periods", "period cramps"],
        "predicted_disease": "Menstrual Pain Pattern",
        "confidence": 0.65,
        "tablets": "Ibuprofen or naproxen may help cramps if medically suitable and taken with food; avoid if you have ulcers/kidney disease or are advised against NSAIDs.",
        "natural_medicine": "Warm compress/heating pad, gentle stretching, and light activity.",
        "advice": "Consult a doctor if pain is severe, bleeding is very heavy, cycles are very irregular, or symptoms are new/worsening.",
    },
    {
        "keywords": [
            "leg pain",
            "shooting leg pain",
            "radiating leg pain",
            "pain radiates to leg",
            "numbness in leg",
            "tingling in leg",
            "sciatica",
            "back pain with leg pain"
        ],
        "predicted_disease": "Nerve Compression / Sciatica Pattern",
        "confidence": 0.68,
        "tablets": "Avoid self-medicating strong painkillers. If medically suitable, OTC acetaminophen (paracetamol) or ibuprofen may help short-term; stop and seek care if symptoms worsen.",
        "natural_medicine": "Rest from heavy lifting, gentle stretching, heat/ice as tolerated, and avoid prolonged sitting.",
        "advice": "Seek urgent care if weakness, foot drop, bowel/bladder changes, severe numbness, or pain after injury occurs.",
    },
]


def _extract_json_block(raw_text: str) -> Dict[str, Any]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {}

    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        filtered = [line for line in lines if not line.strip().startswith("```")]
        raw_text = "".join(filtered).strip()

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _safe_float(value: Any, fallback: float = 0.35) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback



SYMPTOM_COMBINATION_RULES = [
    {
        "predicted_disease": "Flu-like Illness Pattern",
        "all": ["fever", "cough"],
        "any": ["cold", "runny nose", "sore throat", "body ache"],
    },
    {
        "predicted_disease": "Acute Gastroenteritis Pattern",
        "all": ["diarrhea", "vomiting"],
        "any": ["stomach pain", "stomach upset"],
    },
    {
        "predicted_disease": "Food Poisoning Pattern",
        "all": ["stomach pain", "vomiting"],
        "any": ["diarrhea", "loose motion", "bad food", "spoiled food", "after eating"],
    },
    {
        "predicted_disease": "Sinus Infection Pattern",
        "all": ["blocked nose"],
        "any": ["sinus pain", "headache with cold", "facial pain", "nasal congestion"],
    },
    {
        "predicted_disease": "Upper Throat Infection Pattern",
        "all": ["sore throat"],
        "any": ["fever", "swallowing pain", "tonsil"],
    },
    {
        "predicted_disease": "Urinary Tract Infection Pattern",
        "all": ["burning urination", "frequent urination"],
        "any": ["lower abdominal pain", "urine pain"],
    },
    {
        "predicted_disease": "Possible Cardiac Event",
        "all": ["chest pain"],
        "any": ["left arm pain", "sweating", "tightness", "pressure in chest"],
    },
    {
        "predicted_disease": "Gastric Irritation Pattern",
        "all": ["acidity"],
        "any": ["burning", "bloating", "gas", "indigestion"],
    },
    {
        "predicted_disease": "Nerve Compression / Sciatica Pattern",
        "all": ["back pain"],
        "any": ["leg pain", "sciatica", "radiating leg pain", "numbness in leg", "tingling in leg"],
    },
]


def _term_matches_message(term: str, raw_text: str, clean_tokens: set[str]) -> bool:
    key_raw = (term or "").lower().strip()
    if not key_raw:
        return False
    if key_raw in raw_text:
        return True

    key_clean = preprocess_text(key_raw)
    if not key_clean:
        return False

    key_tokens = {tok for tok in key_clean.split() if tok}
    return bool(key_tokens) and key_tokens.issubset(clean_tokens)


def _match_combination_rule(raw_text: str, clean_tokens: set[str]) -> str | None:
    best_label = None
    best_specificity = -1

    for rule in SYMPTOM_COMBINATION_RULES:
        required = rule.get("all", [])
        optional = rule.get("any", [])

        if required and not all(_term_matches_message(t, raw_text, clean_tokens) for t in required):
            continue
        if optional and not any(_term_matches_message(t, raw_text, clean_tokens) for t in optional):
            continue

        optional_matches = sum(1 for t in optional if _term_matches_message(t, raw_text, clean_tokens))

        specificity = len(required) * 10 + optional_matches
        if specificity > best_specificity:
            best_specificity = specificity
            best_label = str(rule.get("predicted_disease") or "").strip() or None

    return best_label

def _select_fallback_profile(message: str) -> Dict[str, Any] | None:
    message = normalize_symptom_message(message)
    raw_text = (message or "").lower()
    clean_text = preprocess_text(message or "")
    clean_tokens = {tok for tok in clean_text.split() if tok}

    combo_label = _match_combination_rule(raw_text, clean_tokens)
    if combo_label:
        for profile in FALLBACK_PROFILES:
            if str(profile.get("predicted_disease", "")).strip().lower() == combo_label.lower():
                return profile

    best_profile = None
    best_score = 0

    for profile in FALLBACK_PROFILES:
        score = 0
        for keyword in profile.get("keywords", []):
            key_raw = str(keyword).lower().strip()
            if not key_raw:
                continue

            key_clean = preprocess_text(key_raw)
            if not key_clean:
                continue

            key_tokens = {tok for tok in key_clean.split() if tok}
            weight = 2 + max(0, min(2, len(key_tokens) - 1))

            if key_raw in raw_text:
                score += weight
                continue

            if key_tokens and key_tokens.issubset(clean_tokens):
                score += weight
        if score >= profile.get("min_score", 1) and score > best_score:
            best_score = score
            best_profile = profile

    return best_profile if best_score > 0 else None

def _fallback_result(message: str) -> Dict[str, Any]:
    message = normalize_symptom_message(message)
    profile = _select_fallback_profile(message)

    if not profile:
        local_pred = _predict_with_local_model(message)
        if local_pred:
            predicted_label = str(local_pred.get("predicted_disease", "")).strip()
            if predicted_label:
                for candidate in FALLBACK_PROFILES:
                    if str(candidate.get("predicted_disease", "")).strip().lower() == predicted_label.lower():
                        profile = candidate
                        break

                if profile:
                    return {
                        "message": message,
                        "predicted_disease": profile["predicted_disease"],
                        "confidence": float(local_pred.get("confidence", profile.get("confidence", 0.55))),
                        "tablets": profile["tablets"],
                        "natural_medicine": profile["natural_medicine"],
                        "advice": f"{profile['advice']} {DISCLAIMER_EN}",
                    }

                return {
                    "message": message,
                    "predicted_disease": predicted_label,
                    "confidence": float(local_pred.get("confidence", 0.55)),
                    "tablets": "Avoid self-medication. Use only a previously doctor-approved tablet if needed.",
                    "natural_medicine": "Hydration, rest, light meals, and symptom monitoring for 24-48 hours.",
                    "advice": "Consult a doctor for persistent symptoms. " + DISCLAIMER_EN,
                }

    if profile:
        return {
            "message": message,
            "predicted_disease": profile["predicted_disease"],
            "confidence": profile["confidence"],
            "tablets": profile["tablets"],
            "natural_medicine": profile["natural_medicine"],
            "advice": f"{profile['advice']} {DISCLAIMER_EN}",
        }

    return {
        "message": message,
        "predicted_disease": "General Symptom Review",
        "confidence": 0.35,
        "tablets": "Avoid self-medication. Use only a previously doctor-approved tablet if needed.",
        "natural_medicine": "Hydration, rest, light meals, and symptom monitoring for 24-48 hours.",
        "advice": "Consult a doctor for persistent symptoms. " + DISCLAIMER_EN,
    }

def _fallback_with_reason(message: str) -> Dict[str, Any]:
    result = _fallback_result(message)
    result["advice"] = f"{result['advice']} AI service is temporarily unavailable, so this is safe basic guidance."
    return result


def _build_prompt(message: str) -> str:
    return (
        "You are a cautious health assistant for educational guidance only. "
        "Given user symptoms, provide:"
        "1) one likely condition label (not diagnosis)2) confidence between 0 and 13) tablets suggestions specific to the exact symptom pattern (not same for every pain)4) natural/home remedies5) when to consult a doctor."
        "Output only valid JSON with keys exactly:"
        "predicted_disease, confidence, tablets, natural_medicine, advice"
        "Rules:"
        "- Include a medical disclaimer in advice."
        "- Never claim certainty."
        "- Keep each field concise."
        f"User symptoms: {message}"
    )


def analyze_symptoms_with_gemini(message: str) -> Dict[str, Any]:
    message = normalize_symptom_message(message)
    api_key = settings.GEMINI_API_KEY
    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"

    if not api_key:
        return _fallback_result(message)

    payload = {
        "contents": [{"parts": [{"text": _build_prompt(message)}]}],
        "generationConfig": {"temperature": 0.2},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError:
        return _fallback_with_reason(message)
    except requests.RequestException:
        return _fallback_with_reason(message)

    candidates = data.get("candidates", [])
    if not candidates:
        return _fallback_result(message)

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)
    if not parsed:
        return _fallback_result(message)

    predicted_disease = str(parsed.get("predicted_disease", "General Symptom Review")).strip()
    confidence = _safe_float(parsed.get("confidence"), fallback=0.35)
    tablets = str(parsed.get("tablets", "")).strip()
    natural_medicine = str(parsed.get("natural_medicine", "")).strip()
    advice = str(parsed.get("advice", "")).strip()

    if not advice:
        advice = _fallback_result(message)["advice"]
    if "not a medical diagnosis" not in advice.lower() and "not a diagnosis" not in advice.lower():
        advice += " This is not a medical diagnosis."

    if not tablets:
        tablets = _fallback_result(message)["tablets"]

    return {
        "message": message,
        "predicted_disease": predicted_disease or "General Symptom Review",
        "confidence": confidence,
        "tablets": tablets,
        "natural_medicine": natural_medicine or "Hydration, rest, and light food intake.",
        "advice": advice,
    }


KANNADA_FALLBACK_STATIC = {
    "Immediate Simple Advice (At Home)": "?????? ??? ???? (????????)",
    "Based on your symptoms:": "????? ??????? ????? ????:",
    "Since you have fever:": "????? ???? ??????????:",
    "When You Should See a Doctor Immediately": "????? ????? ?????????? ???? ???????",
    "Possible Causes (Based on Symptoms)": "???????? ??????? (??????? ????? ????)",
    "Fever can happen due to:": "???? ???? ???????? ???????:",
    "Your symptoms can happen due to:": "????? ?????????? ???????? ???????:",
    "Do you need any extra suggestions or precautions?": "???????? ??????? ???? ??????????? ?????",
}


KANNADA_FALLBACK_BULLETS = {
    "Drink plenty of water": "?????? ???? ????????",
    "Take proper rest and avoid stress": "??????? ????????? ???????????? ????? ????? ???????",
    "Eat light food (rice, soup, fruits)": "??? ???? (????, ????, ????????) ??????",
    "Use a wet cloth on forehead if temperature is high": "?????? ?????? ?????? ???????? ?????? ????? ???",
    "Drink warm fluids and keep yourself hydrated": "???? ?????????? ???????? ????? ???????? ???????",
    "Use warm compress on painful area": "???? ???? ??? ???? ????? (warm compress) ????",
    "Take rest and avoid heavy lifting": "????????? ???????????? ????? ???? ???? ???????",
    "Do gentle stretching if pain is mild": "???? ????? ?????? ??????? ??????????? ????",
    "Stay hydrated and avoid prolonged poor posture": "???????? ??????? ????? ?????? ?????/???? ????????? ???????",
    "Rest in a dark and quiet room": "?????? ????? ???? ????????? ????????? ????????????",
    "Drink water regularly": "?????????? ???? ????????",
    "Avoid loud sound and bright light": "????? ???? ????? ????? ????? ???????",
    "Eat light meals and avoid skipping meals": "??? ?? ???? ????? ?? ???????? ???????",
    "Drink lukewarm water in small sips": "?????? ?????????? ???-???????? ???? ????????",
    "Eat soft light food and avoid oily/spicy meals": "??????? ??? ???? ?????? ????? ?????/??? ???? ???????",
    "Do not lie down immediately after eating": "??? ????? ???????",
    "Take proper rest and reduce stress": "??????? ????????? ???????????? ????? ????? ????? ????",
    "Drink enough water": "??????? ???? ????????",
    "Eat light nutritious food": "??????? ???? ??? ???? ??????",
    "Avoid stress and monitor symptoms": "????? ??????? ????? ??????????? ??????",
    "Fever above 102F": "102F ?????? ?????? ????",
    "Fever more than 2-3 days": "2-3 ?????????? ?????? ????",
    "Severe headache or vomiting": "????? ??????? ???? ?????",
    "Difficulty breathing": "?????????? ??????",
    "Extreme weakness": "?????? ????????",
    "Viral infection": "????? ?????",
    "Cold & flu": "???/????",
    "Weather change or low immunity": "?????? ??????? ???? ????? ????????? ?????",
}


def _kannada_tts_fallback(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    out_lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        if "Mild" in stripped and "Moderate" in stripped and "Severe" in stripped:
            out_lines.append("Mild   Moderate   Severe")
            continue

        if stripped in KANNADA_FALLBACK_STATIC:
            out_lines.append(KANNADA_FALLBACK_STATIC[stripped])
            continue

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            translated_item = KANNADA_FALLBACK_BULLETS.get(item)
            if translated_item:
                out_lines.append(f"- {translated_item}")
                continue

        for prefix_en, prefix_kn in [
            ("Condition:", "???????? ??????:"),
            ("Tablets:", "?????????:"),
            ("Natural medicine:", "????????? ????????:"),
            ("Home remedies:", "????????/?????-?????:"),
            ("Advice:", "????:"),
            ("Doctor immediately:", "????? ?????????? ?????????:"),
            ("Select severity:", "????? ???????????? ??????? ?????????:"),
            ("Do you need any extra suggestions or precautions?"),
        ]:
            if stripped.startswith(prefix_en):
                rest = stripped[len(prefix_en) :].strip()
                out_lines.append(f"{prefix_kn} {rest}".rstrip())
                break
        else:
            out_lines.append(line)

    joined = "".join(out_lines).strip()
    return joined or raw

_KANNADA_LABEL_MAP = {
    'Condition:': '\u0cb8\u0ccd\u0ca5\u0cbf\u0ca4\u0cbf:',
    'Tablets:': '\u0c94\u0cb7\u0ca7\u0cbf\u0c97\u0cb3\u0cc1:',
    'Natural medicine:': '\u0cb8\u0ccd\u0cb5\u0cbe\u0cad\u0cbe\u0cb5\u0cbf\u0c95 \u0c9a\u0cbf\u0c95\u0cbf\u0ca4\u0ccd\u0cb8\u0cc6:',
    'Home remedies:': '\u0cae\u0ca8\u0cc6\u0cae\u0ca6\u0ccd\u0ca6\u0cc1\u0c97\u0cb3\u0cc1:',
    'Advice:': '\u0cb8\u0cb2\u0cb9\u0cc6:',
    'Doctor immediately:': '\u0ca4\u0c95\u0ccd\u0cb7\u0ca3 \u0cb5\u0cc8\u0ca6\u0ccd\u0caf\u0cb0\u0ca8\u0ccd\u0ca8\u0cc1 \u0cb8\u0c82\u0caa\u0cb0\u0ccd\u0c95\u0cbf\u0cb8\u0cbf:',
    'Select severity:': '\u0ca4\u0cc0\u0cb5\u0ccd\u0cb0\u0ca4\u0cc6 \u0c86\u0caf\u0ccd\u0c95\u0cc6\u0cae\u0cbe\u0ca1\u0cbf:',
}


def _kannada_label_fallback(text: str) -> str:
    raw = (text or '').strip()
    if not raw:
        return ''

    out_lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        replaced = False
        for en_prefix, kn_prefix in _KANNADA_LABEL_MAP.items():
            if stripped.lower().startswith(en_prefix.lower()):
                rest = stripped[len(en_prefix):].strip()
                out_lines.append((kn_prefix + ' ' + rest).rstrip())
                replaced = True
                break
        if not replaced:
            out_lines.append(line)

    joined = '\n'.join(out_lines).strip()
    return joined or raw



def translate_to_kannada(text: str) -> str:
    """Translate English text to Kannada.

    Primary: Gemini (if `GEMINI_API_KEY` is configured).
    Fallback: `deep-translator` GoogleTranslate (no API key, internet required).
    Final fallback: label-only Kannada mapping (offline).
    """

    raw = str(text or "").strip()
    if not raw:
        return ""

    def _deep_translate(value: str) -> str:
        try:
            from deep_translator import GoogleTranslator

            translated = GoogleTranslator(source="auto", target="kn").translate(value)
            return str(translated or "").strip()
        except Exception:
            return ""

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        deep = _deep_translate(raw)
        return deep or _kannada_label_fallback(raw)

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "Translate the following text into Kannada (kn). "
        "Keep medicine names/doses as-is. Do not add any extra medical advice. "
        "Return only the translated plain text. "
        f"TEXT:{raw}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        deep = _deep_translate(raw)
        return deep or _kannada_label_fallback(raw)

    candidates = data.get("candidates", [])
    if not candidates:
        deep = _deep_translate(raw)
        return deep or _kannada_label_fallback(raw)

    parts = candidates[0].get("content", {}).get("parts", [])
    translated = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    if translated:
        return translated

    deep = _deep_translate(raw)
    return deep or _kannada_label_fallback(raw)


def analyze_prescription_image(image_file, user_context: str = "") -> Dict[str, Any]:

    def _contextual_home_remedies_for_prescription(context: str) -> list[str]:
        clean = preprocess_text(context or "")
        tokens = set(clean.split())

        remedies: list[str] = []

        def add(item: str) -> None:
            item = str(item or "").strip()
            if not item:
                return
            if item.lower() in {r.lower() for r in remedies}:
                return
            remedies.append(item)

        # Gastro / acidity
        if tokens.intersection({"acidity", "heartburn", "burning", "gastric", "stomach", "vomit", "vomiting", "diarrhea", "loose", "motion", "nausea"}):
            add("Take small, bland meals (rice, curd, banana) and avoid spicy/oily food.")
            add("Sip water/ORS regularly to prevent dehydration.")
            add("Avoid lying down immediately after eating.")

        # Cold/cough
        if tokens.intersection({"cough", "cold", "sneeze", "sneezing", "throat", "sore"}):
            add("Drink warm fluids and rest your voice.")
            add("Warm salt-water gargles can soothe throat irritation.")

        # Fever/body ache
        if tokens.intersection({"fever", "temperature", "chills", "body", "ache"}):
            add("Rest and drink plenty of fluids.")
            add("Light meals and adequate sleep help recovery.")

        # Headache/migraine
        if tokens.intersection({"headache", "migraine", "head", "photophobia", "light", "sensitivity"}):
            add("Rest in a dark, quiet room and reduce screen exposure.")
            add("Stay hydrated and avoid skipping meals.")

        # Default
        if not remedies:
            add("Rest and stay hydrated.")
            add("Eat light nutritious food.")

        return remedies[:5]
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        summary = (
            "Prescription understanding needs GEMINI_API_KEY. "
            "Please verify the prescription with your doctor/pharmacist. "
            + DISCLAIMER_EN
        )
        return {
            "extracted_text": "",
            "medicines": [],
            "tests": [],
            "warnings": [
                "Could not read the prescription without AI key.",
                "Please verify with a doctor/pharmacist.",
            ],
            "summary": summary,
            "home_remedies": _contextual_home_remedies_for_prescription(user_context),
            "tablets_note": "Follow exactly what is written on the prescription.",
            "questions_for_doctor": [
                "How many days should I take each medicine?",
                "Should I take it before/after food?",
                "What are common side effects to watch for?",
            ],
            "speech_text": summary,
        }

    mime_type = mimetypes.guess_type(getattr(image_file, "name", ""))[0] or "image/jpeg"
    image_bytes = image_file.read()
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are helping a user understand a doctor prescription photo."
        "First, extract what is written (best-effort) as plain text."
        "Then explain it in simple English."
        "Return only JSON with keys exactly:"
        "extracted_text, medicines, tests, warnings, summary, home_remedies, tablets_note, questions_for_doctor"
        "Rules:"
        "- extracted_text: best-effort transcription."
        "- medicines: list of objects with keys: name, strength, dosage, frequency, duration, instructions (unknown => empty string)."
        "- warnings: include that handwriting/OCR may be wrong and user must verify with doctor/pharmacist."
        "- tablets_note: only explain what is written; do NOT recommend new medicines/doses."
        "- home_remedies: general safe self-care only."
        "- No diagnosis or certainty."
        "User context (symptoms/complaint): " + str(user_context or "")

    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        summary = "Could not reach the AI service. Please verify with your pharmacist/doctor. " + DISCLAIMER_EN
        return {
            "extracted_text": "",
            "medicines": [],
            "tests": [],
            "warnings": ["AI service unavailable. Please retry with a clearer image."],
            "summary": summary,
            "home_remedies": _contextual_home_remedies_for_prescription(user_context),
            "tablets_note": "Follow the prescription as written.",
            "questions_for_doctor": ["Please confirm the medicines/dose written on this prescription."],
            "speech_text": translate_to_kannada(summary),
        }

    candidates = data.get("candidates", [])
    if not candidates:
        summary = "No output from AI model. Please retry with a clearer image. " + DISCLAIMER_EN
        return {
            "extracted_text": "",
            "medicines": [],
            "tests": [],
            "warnings": ["No output from model. Please retry."],
            "summary": summary,
            "home_remedies": ["Stay hydrated", "Rest"],
            "tablets_note": "Follow the prescription as written.",
            "questions_for_doctor": ["Please confirm the prescription content."],
            "speech_text": translate_to_kannada(summary),
        }

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)
    if not parsed:
        summary = "Could not parse the prescription result. Please retry with a clearer image. " + DISCLAIMER_EN
        return {
            "extracted_text": model_text[:4000],
            "medicines": [],
            "tests": [],
            "warnings": ["Could not parse response. Please retry."],
            "summary": summary,
            "home_remedies": ["Stay hydrated", "Rest"],
            "tablets_note": "Follow the prescription as written.",
            "questions_for_doctor": ["Please confirm the prescription content."],
            "speech_text": translate_to_kannada(summary),
        }

    warnings = parsed.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    warnings = [str(w).strip() for w in warnings if str(w).strip()]
    if not warnings:
        warnings = ["Handwriting/OCR may be incorrect. Please verify with your doctor/pharmacist."]

    summary = str(parsed.get("summary", "")).strip() or DISCLAIMER_EN

    home_remedies = parsed.get("home_remedies") or []
    if not isinstance(home_remedies, list) or not [str(x).strip() for x in home_remedies if str(x).strip()]:
        home_remedies = _contextual_home_remedies_for_prescription(user_context)

    return {
        "extracted_text": str(parsed.get("extracted_text", "")).strip(),
        "medicines": parsed.get("medicines") or [],
        "tests": parsed.get("tests") or [],
        "warnings": warnings,
        "summary": summary,
        "home_remedies": home_remedies,
        "tablets_note": str(parsed.get("tablets_note", "")).strip(),
        "questions_for_doctor": parsed.get("questions_for_doctor") or [],
        "speech_text": translate_to_kannada(summary),
    }


def analyze_symptom_image(image_file, category: str) -> Dict[str, Any]:
    """Analyze skin/eye images. For skin, classify into common skin problems and return cause/symptoms/care."""

    SKIN_LIBRARY = {
        "acne": {
            "title": "Acne (Pimples)",
            "cause": "Oil, bacteria, hormones",
            "symptoms": "Pimples, blackheads, whiteheads",
            "care": "Keep face clean, avoid oily products/food, don?t squeeze pimples.",
        },
        "rashes": {
            "title": "Rashes",
            "cause": "Allergy, heat, irritation",
            "symptoms": "Redness, itching, small bumps",
            "care": "Avoid irritant/trigger, use soothing moisturizer, keep area cool/dry.",
        },
        "eczema": {
            "title": "Eczema",
            "cause": "Skin sensitivity",
            "symptoms": "Dry, itchy, cracked skin",
            "care": "Moisturize regularly, avoid harsh soaps/hot showers, use gentle cleanser.",
        },
        "fungal": {
            "title": "Fungal Infection",
            "cause": "Sweat, moisture",
            "symptoms": "Itching, red circular patches",
            "care": "Keep area dry, change sweaty clothes, consider an OTC antifungal cream if suitable.",
        },
        "psoriasis": {
            "title": "Psoriasis",
            "cause": "Immune system issue",
            "symptoms": "Thick, scaly patches",
            "care": "Often needs medical treatment; moisturize and avoid harsh irritants.",
        },
        "sunburn": {
            "title": "Sunburn",
            "cause": "Too much sun exposure",
            "symptoms": "Red, painful skin",
            "care": "Cool compress, aloe vera, stay hydrated, avoid further sun; use sunscreen later.",
        },
        "allergy": {
            "title": "Allergic Reaction",
            "cause": "Food, chemicals, cosmetics",
            "symptoms": "Swelling, redness, itching",
            "care": "Avoid trigger, cold compress, consider an OTC antihistamine if medically suitable.",
        },
        "pigmentation": {
            "title": "Dark Spots / Pigmentation",
            "cause": "Sun, acne scars",
            "symptoms": "Dark patches on skin",
            "care": "Daily sunscreen, gentle skincare; see a dermatologist for treatment options.",
        },
    }

    def _skin_response(label_key: str, confidence: float, extra_advice: str = "") -> Dict[str, Any]:
        info = SKIN_LIBRARY.get(label_key) or SKIN_LIBRARY["rashes"]
        advice = (
            "Seek a doctor urgently if you have fever, pus, severe pain, rapid spreading rednessswelling of lips/face, or breathing trouble. "
            + DISCLAIMER_EN
        )
        if extra_advice:
            advice = (extra_advice.strip() + " " + advice).strip()

        guidance = "\n".join(
            [
                f"Condition: {info['title']}",
                f"Cause: {info['cause']}",
                f"Symptoms: {info['symptoms']}",
                f"Care: {info['care']}",
                f"Advice: {advice}",
            ]
        )

        return {
            "assessment": info["title"],
            "confidence": confidence,
            "guidance": guidance,
            "skin_label": label_key,
        }

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        # Basic (no-AI) fallback. We still respond in the same structured format.
        if category == "skin_rash":
            return _skin_response("rashes", 0.35, extra_advice="Basic guidance only (image AI not configured).")

        guidance = "\n".join([
            "Condition: Eye irritation / conjunctivitis (possible)",
            "Care: Avoid touching eyes, wash hands, rinse with clean water, use artificial tears.",
            "Advice: Seek care urgently if severe pain, vision change, thick discharge, or contact lens use. " + DISCLAIMER_EN,
        ])
        return {
            "assessment": "Eye Irritation / Conjunctivitis Pattern",
            "confidence": 0.35,
            "guidance": guidance,
        }

    mime_type = mimetypes.guess_type(getattr(image_file, "name", ""))[0] or "image/jpeg"
    image_bytes = image_file.read()
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"

    if category == "skin_rash":
        prompt = (
            "Analyze this skin image cautiously. "
            "First decide if the image is usable (not blurry/dark/cropped). "
            "If unusable, ask for a clearer close-up photo of the affected skin area. "
            "If usable, classify the skin problem into exactly ONE of: "
            "acne, rashes, eczema, fungal, psoriasis, sunburn, allergy, pigmentation. "
            "Return ONLY JSON with keys exactly: needs_reupload (boolean), reupload_reason (string), label (string), confidence (0..1)."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1},
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=25)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return _skin_response("rashes", 0.45, extra_advice="Could not reach image AI, so this is a basic best-effort suggestion.")

        candidates = data.get("candidates", [])
        if not candidates:
            return {
                "assessment": "Unclear skin image",
                "confidence": 0.3,
                "guidance": "Couldn't analyze the image. Please describe the skin/eye issue in text. " + DISCLAIMER_EN,
                "needs_reupload": True,
                "reupload_reason": "Couldn't analyze the image. Please describe the skin/eye issue in text.",
            }

        parts = candidates[0].get("content", {}).get("parts", [])
        model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        parsed = _extract_json_block(model_text)

        needs_reupload = bool(parsed.get("needs_reupload"))
        reupload_reason = str(parsed.get("reupload_reason") or "").strip()
        label = str(parsed.get("label") or "rashes").strip().lower()
        confidence = _safe_float(parsed.get("confidence"), fallback=0.55)

        if needs_reupload:
            reason = reupload_reason or "Couldn't analyze the image. Please describe the skin/eye issue in text."
            return {
                "assessment": "Unclear skin image",
                "confidence": 0.3,
                "guidance": reason + " " + DISCLAIMER_EN,
                "needs_reupload": True,
                "reupload_reason": reason,
            }

        if label not in SKIN_LIBRARY:
            label = "rashes"

        out = _skin_response(label, confidence)
        out["needs_reupload"] = False
        out["reupload_reason"] = ""
        return out

    # Eye path (keep previous style)
    prompt = (
        "Analyze this eye redness/irritation image with caution. "
        "Return only JSON with keys: assessment, confidence, guidance. "
        "Rules: confidence must be 0..1; keep concise; include that this is not a diagnosis in guidance."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return {
            "assessment": "Possible eye irritation pattern",
            "confidence": 0.45,
            "guidance": "Could not reach advanced image model, so this is basic guidance. " + DISCLAIMER_EN,
        }

    candidates = data.get("candidates", [])
    if not candidates:
        return {
            "assessment": "Possible eye irritation pattern",
            "confidence": 0.45,
            "guidance": "Model returned no output. Please retry with clearer image. " + DISCLAIMER_EN,
        }

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)

    assessment = str(parsed.get("assessment", "Possible eye irritation pattern")).strip()
    confidence = _safe_float(parsed.get("confidence"), fallback=0.55)
    guidance = str(parsed.get("guidance", "Please consult a specialist if symptoms persist or worsen. " + DISCLAIMER_EN)).strip()
    if "not a medical diagnosis" not in guidance.lower() and "not a diagnosis" not in guidance.lower():
        guidance += " " + DISCLAIMER_EN

    return {
        "assessment": assessment,
        "confidence": confidence,
        "guidance": guidance,
    }

def _strip_disclaimer(advice: str) -> str:
    value = (advice or "").strip()
    if not value:
        return value

    lowered = value.lower()
    for marker in [
        "this is not a medical diagnosis",
        "not a medical diagnosis",
        "not a diagnosis",
        "ai service is temporarily unavailable",
    ]:
        idx = lowered.find(marker)
        if idx > 0:
            return value[:idx].rstrip(" .") + "."

    return value



FOLLOWUP_QUESTIONS_BY_PATTERN = {
    "Flu-like Illness Pattern": [
        "Do you also have cough?",
        "Since how many days?",
        "Is the fever very high (above 102F/39C) or with breathing trouble?",
    ],
    "Common cold": [
        "Do you have sore throat or cough?",
        "Since how many days?",
        "Any fever?",
    ],
    "Common cough": [
        "Since how many days?",
        "Do you also have fever?",
        "Any breathing difficulty or chest pain?",
    ],
    "Upper Throat Infection Pattern": [
        "Do you have fever?",
        "Is swallowing very painful or difficult?",
        "Since how many days?",
    ],
    "Sinus Infection Pattern": [
        "Is your nose blocked/runny with facial pressure?",
        "Since how many days?",
        "Do you also have fever or tooth pain?",
    ],
    "Migraine or Tension Headache Pattern": [
        "Is it one-sided/throbbing with nausea or light sensitivity?",
        "Since how many hours/days?",
        "Any weakness, confusion, or worst headache of life?",
    ],
    "Gastric Irritation Pattern": [
        "Is there vomiting or blood in stool?",
        "Since how many days?",
        "Is the burning worse after spicy/oily food?",
    ],
    "Acute Gastroenteritis Pattern": [
        "How many times did you have loose motions/vomiting today?",
        "Any blood in stool or high fever?",
        "Since how many days?",
    ],
    "Urinary Tract Infection Pattern": [
        "Do you have fever or back/flank pain?",
        "Since how many days?",
        "Is there blood in urine or pregnancy?",
    ],
    "Allergic Reaction Pattern": [
        "Any swelling of lips/face or breathing difficulty?",
        "What triggered it (food/dust/medicine)?",
        "Since when did it start?",
    ],
    "Menstrual Pain Pattern": [
        "Is bleeding very heavy or cycles very irregular?",
        "Since how many days (this cycle)?",
        "Any severe dizziness or fainting?",
    ],
    "Stress / Anxiety Pattern": [
        "Are you able to sleep?",
        "Since how many days/weeks?",
        "Any panic symptoms (fast heartbeat, breathlessness) or thoughts of self-harm?",
    ],
    "Dental Pain / Possible Infection Pattern": [
        "Is there gum swelling or fever?",
        "Since how many days?",
        "Is chewing painful?",
    ],
    "Eye Irritation / Conjunctivitis Pattern": [
        "Is there eye pain or vision change?",
        "Any discharge (sticky/pus) or contact lens use?",
        "Since how many days?",
    ],
    "Possible Iron Deficiency Pattern": [
        "Do you feel shortness of breath on exertion?",
        "Since how many weeks?",
        "Any very heavy periods or recent blood loss?",
    ],
}

DEFAULT_FOLLOWUP_QUESTIONS = [
    "Since how many days?",
    "Do you have fever?",
    "Is the symptom getting worse quickly?",
]


def generate_followup_questions(message: str) -> List[str]:
    profile = _select_fallback_profile(message)
    label = None
    if profile:
        label = str(profile.get("predicted_disease") or "").strip()

    if not label:
        local = _predict_with_local_model(message)
        if local:
            label = str(local.get("predicted_disease") or "").strip()

    if label == "Possible Cardiac Event":
        return []

    if label and label in FOLLOWUP_QUESTIONS_BY_PATTERN:
        return FOLLOWUP_QUESTIONS_BY_PATTERN[label]

    return DEFAULT_FOLLOWUP_QUESTIONS

TABLET_SUGGESTION_CATALOG = [
    {
        "name": "Paracetamol",
        "image_key": "paracetamol",
        "use": "Used for fever relief and mild pain.",
        "triggers": ["paracetamol", "tylenol", "dolo", "crocin"],
    },
    {
        "name": "Acetaminophen",
        "image_key": "acetaminophen",
        "use": "Used for fever relief and mild pain (same medicine as paracetamol).",
        "triggers": ["acetaminophen"],
    },
    {
        "name": "Cetirizine",
        "image_key": "cetirizine",
        "use": "Used for allergy/runny nose symptoms.",
        "triggers": ["cetirizine"],
    },
    {
        "name": "Ibuprofen",
        "image_key": "ibuprofen",
        "use": "Used for pain and inflammation (NSAID).",
        "triggers": ["ibuprofen"],
    },
    {
        "name": "Naproxen",
        "image_key": "naproxen",
        "use": "Used for pain and inflammation (NSAID).",
        "triggers": ["naproxen"],
    },
    {
        "name": "Diclofenac Gel",
        "image_key": "diclofenac_gel",
        "use": "Topical gel used for localized joint/muscle pain.",
        "triggers": ["diclofenac", "diclofenac gel"],
    },
    {
        "name": "ORS",
        "image_key": "ors",
        "use": "Used to prevent dehydration (diarrhea/vomiting).",
        "triggers": ["ors", "oral rehydration"],
    },
    {
        "name": "Antacid",
        "image_key": "antacid",
        "use": "Used for acidity/heartburn relief.",
        "triggers": ["antacid", "calcium carbonate", "alginate"],
    },
    {
        "name": "Probiotics",
        "image_key": "probiotic",
        "use": "May help restore gut bacteria in diarrhea (some cases).",
        "triggers": ["probiotic", "probiotics"],
    },
    {
        "name": "Loratadine",
        "image_key": "loratadine",
        "use": "Used for allergy/runny nose symptoms (non-drowsy antihistamine).",
        "triggers": ["loratadine"],
    },
    {
        "name": "Amoxicillin",
        "image_key": "amoxicillin",
        "use": "Antibiotic (use only if prescribed).",
        "triggers": ["amoxicillin"],
    },
    {
        "name": "Penicillin",
        "image_key": "penicillin",
        "use": "Antibiotic (use only if prescribed).",
        "triggers": ["penicillin"],
    },
    {
        "name": "Meloxicam",
        "image_key": "meloxicam",
        "use": "NSAID used for pain and inflammation (only if medically suitable).",
        "triggers": ["meloxicam"],
    },
    {
        "name": "Tramadol",
        "image_key": "tramadol",
        "use": "Prescription pain medicine (use only if prescribed).",
        "triggers": ["tramadol"],
    },
    {
        "name": "Triptan",
        "image_key": "triptan",
        "use": "Prescription migraine medicine (use only if prescribed).",
        "triggers": ["triptan", "sumatriptan"],
    },
    {
        "name": "Gepant",
        "image_key": "gepant",
        "use": "Prescription migraine medicine (CGRP antagonist; use only if prescribed).",
        "triggers": ["gepant", "ubrogepant", "rimegepant"],
    },
    {
        "name": "Zincovid",
        "image_key": "zincovid",
        "use": "Supplement used for immunity support (for reference only).",
        "triggers": ["zincovid"],
    },
    {
        "name": "Decongestants",
        "image_key": "deconestand",
        "use": "Used for nasal congestion/runny nose relief (for reference).",
        "triggers": ["decongestant", "decongestants", "deconestand"],
    },
    {
        "name": "Revital H",
        "image_key": "revital_h",
        "use": "Multivitamin supplement (for reference only).",
        "triggers": ["revital", "revital h", "multivitamin", "vitamin", "vitamins"],
    },
    {
        "name": "Sprays",
        "image_key": "sprays",
        "use": "Throat/nasal sprays (for reference only).",
        "triggers": ["spray", "sprays"],
    },
    {
        "name": "Celeheal",
        "image_key": "celeheal",
        "use": "Pain relief medicine (use only if medically suitable).",
        "triggers": ["celeheal"],
    },
    {
        "name": "Dolokind-Plus (Aceclofenac + Paracetamol)",
        "image_key": "dolokind_plus",
        "use": "Used for pain and inflammation (for reference only; use only if medically suitable).",
        "triggers": ["dolokind", "dolokind plus", "dolokind-plus", "aceclofenac", "aceclofenac paracetamol", "aceclofenac and paracetamol"],
    },
]


def _normalize_match_text(text: str) -> str:
    """Lowercase and normalize punctuation to spaces for trigger matching."""

    lower = str(text or "").lower()
    lower = re.sub(r"[^a-z0-9]+", " ", lower)
    return re.sub(r"\s+", " ", lower).strip()


def _text_contains_trigger(text: str, trigger: str) -> bool:
    """True if trigger appears in text with basic word-boundary safety for short tokens."""

    norm_text = _normalize_match_text(text)
    trig = _normalize_match_text(trigger)
    if not norm_text or not trig:
        return False

    # Multi-token or digit-containing triggers can be substring matched on normalized text.
    if " " in trig or any(ch.isdigit() for ch in trig):
        return f" {trig} " in f" {norm_text} "

    # Single token: use word boundary to avoid matching 'dolo' in 'dolokind'.
    return re.search(rf"\b{re.escape(trig)}\b", norm_text) is not None


def find_best_tablet_catalog_match(text: str) -> Dict[str, Any] | None:
    """Return the best matching catalog item for the given text (brand/generic), else None."""

    if not str(text or "").strip():
        return None

    best_item = None
    best_score = -1

    for item in TABLET_SUGGESTION_CATALOG:
        for trig in item.get("triggers", []) or []:
            trigger = str(trig or "").strip()
            if not trigger:
                continue
            if not _text_contains_trigger(text, trigger):
                continue

            # Prefer more specific (longer) triggers.
            score = len(_normalize_match_text(trigger))
            if score > best_score:
                best_item = item
                best_score = score

    return best_item



def build_tablet_suggestions(tablets_text: str, predicted_disease: str = "") -> List[Dict[str, str]]:
    text = (tablets_text or "").lower()
    results: List[Dict[str, str]] = []
    seen = set()

    for item in TABLET_SUGGESTION_CATALOG:
        triggers = [str(t).strip() for t in item.get("triggers", [])]
        if triggers and not any(t and _text_contains_trigger(text, t) for t in triggers):
            continue

        key = str(item.get("image_key") or "generic")
        name = str(item.get("name") or "Medicine").strip() or "Medicine"
        if name.lower() in seen:
            continue
        seen.add(name.lower())

        results.append(
            {
                "name": name,
                "use": str(item.get("use") or "").strip(),
                "image_key": key,
                "food_timing": get_food_timing_for_image_key(key),
                "disclaimer": "For reference only. Consult doctor before use.",
            }
        )

    # If disease is emergency, avoid suggesting tablets.
    disease_lower = str(predicted_disease or "").strip().lower()

    def _push_image_key(image_key: str) -> None:
        key = (image_key or "").strip()
        if not key:
            return

        for catalog_item in TABLET_SUGGESTION_CATALOG:
            if str(catalog_item.get("image_key") or "").strip().lower() != key.lower():
                continue

            name = str(catalog_item.get("name") or "Medicine").strip() or "Medicine"
            if name.lower() in seen:
                return

            seen.add(name.lower())
            results.append(
                {
                    "name": name,
                    "use": str(catalog_item.get("use") or "").strip(),
                    "image_key": str(catalog_item.get("image_key") or "generic"),
                    "food_timing": get_food_timing_for_image_key(str(catalog_item.get("image_key") or "")),
                    "disclaimer": "For reference only. Consult doctor before use.",
                }
            )
            return

    # Helpful defaults when the response text doesn't explicitly name medicines.
    if "vitamin deficiency" in disease_lower:
        _push_image_key("revital_h")
        _push_image_key("zincovid")

    if ("migraine" in disease_lower or "headache" in disease_lower) and not results:
        _push_image_key("acetaminophen")
        _push_image_key("ibuprofen")
    if str(predicted_disease or "").strip().lower() == "possible cardiac event":
        return []

    if results:
        return results

    raw = (tablets_text or "").strip()
    if not raw or "avoid self-medication" in raw.lower():
        return []

    candidates = [
        p.strip()
        for p in raw.replace(" or ", ",").replace(" & ", ",").split(",")
        if p and p.strip()
    ]

    for candidate in candidates:
        name = candidate
        lowered = name.lower()
        for sep in [" may ", " only ", " if ", " for "]:
            idx = lowered.find(sep)
            if idx != -1:
                name = name[:idx]
                lowered = name.lower()
                break

        name = name.strip(" .")
        lowered = name.lower()

        if not name or len(name) > 40:
            continue
        if lowered.startswith(("if ", "a ", "an ", "avoid ")):
            continue
        if any(
            k in lowered
            for k in (
                "steam",
                "inhalation",
                "warm ",
                "saline",
                "hydration",
                "rest",
                "drink",
                "water",
                "diet",
                "sleep",
                "monitoring",
            )
        ):
            continue
        if len(lowered.split()) > 2:
            continue
        if name.lower() in seen:
            continue
        seen.add(name.lower())

        results.append(
            {
                "name": name,
                "use": "Used for symptom relief (for reference).",
                "image_key": "generic",
                "disclaimer": "For reference only. Consult doctor before use.",
            }
        )
        if len(results) >= 2:
            break

    return results


_PROGRESSION_GUIDANCE = {
    "knee": "If pain/swelling persists or worsens, it could indicate a ligament/meniscus injury or worsening joint inflammation - seek an in-person exam.",
    "musculoskeletal": "If pain worsens or starts radiating with numbness/weakness, it may be nerve involvement (e.g., sciatica) - seek medical evaluation.",
    "headache": "If headaches become frequent, severe, or come with vision/weakness/confusion, it could be migraine or another condition - seek medical care.",
    "throat": "If throat pain worsens, lasts >3-5 days, or you have high fever/breathing trouble, it may need medical review.",
    "flu": "If fever persists >48 hours, breathing worsens, or you become dehydrated, seek medical care.",
    "gastro": "If vomiting/diarrhea worsens, you can become dehydrated quickly - seek care for dizziness, low urine, or blood in stool.",
    "allergy": "If rash/itching worsens or you develop facial swelling/wheezing, it can become a severe allergic reaction - seek urgent care.",
    "uti": "If burning urination worsens or you develop fever/back pain, it may spread to kidneys?seek medical care.",
    "cardiac": "If chest pain/tightness worsens or is with sweating/left-arm pain, treat as emergency and seek urgent care.",
    "eye": "If redness worsens or you have pain/vision changes, you may need urgent eye evaluation.",
    "dental": "If tooth pain worsens or swelling/fever develops, it may be a spreading dental infection - see a dentist/doctor.",
    "menstrual": "If cramps become severe, recurrent, or bleeding is heavy, consider medical evaluation for causes like fibroids/endometriosis.",
}


def _progression_guidance_for_condition(predicted_disease: str) -> str:
    predicted = str(predicted_disease or "").strip().lower()
    if not predicted:
        return "If symptoms persist or worsen, seek medical advice."

    if any(k in predicted for k in ["chest", "cardiac", "heart", "tightness", "left arm"]):
        return _PROGRESSION_GUIDANCE["cardiac"]
    if any(k in predicted for k in ["urinary", "uti", "urination", "kidney"]):
        return _PROGRESSION_GUIDANCE["uti"]
    if any(k in predicted for k in ["migraine", "headache", "head pain", "tension headache"]):
        return _PROGRESSION_GUIDANCE["headache"]
    if any(k in predicted for k in ["throat", "tonsil", "pharyng", "upper throat"]):
        return _PROGRESSION_GUIDANCE["throat"]
    if any(k in predicted for k in ["flu", "fever", "viral"]):
        return _PROGRESSION_GUIDANCE["flu"]
    if any(k in predicted for k in ["gastro", "food poisoning", "diarr", "vomit"]):
        return _PROGRESSION_GUIDANCE["gastro"]
    if any(k in predicted for k in ["allerg", "rash", "itch"]):
        return _PROGRESSION_GUIDANCE["allergy"]
    if any(k in predicted for k in ["eye", "conjunct"]):
        return _PROGRESSION_GUIDANCE["eye"]
    if any(k in predicted for k in ["dental", "tooth", "gum"]):
        return _PROGRESSION_GUIDANCE["dental"]
    if any(k in predicted for k in ["menstrual", "period", "dysmen"]):
        return _PROGRESSION_GUIDANCE["menstrual"]
    if any(k in predicted for k in ["sciatica", "nerve", "radiat", "compression", "leg pain"]):
        return _PROGRESSION_GUIDANCE["musculoskeletal"]
    if any(k in predicted for k in ["knee", "joint"]):
        return _PROGRESSION_GUIDANCE["knee"]
    if any(k in predicted for k in ["strain", "muscle", "back", "neck"]):
        return _PROGRESSION_GUIDANCE["musculoskeletal"]

    return "If symptoms persist or worsen, seek medical advice."



_SYMPTOM_PROGRESSION_RULES: list[dict[str, object]] = [
    {
        "label": "Headache",
        "terms": ["headache", "head pain"],
        "guidance": (
            "If headaches become more frequent or severe, they can become migraine-like or may signal another issue. "
            "Seek urgent care for sudden 'worst headache', confusion, weakness, fainting, or vision changes."
        ),
    },
    {
        "label": "Fever",
        "terms": ["fever", "high fever", "temperature"],
        "guidance": (
            "If fever persists or rises, dehydration and worsening infection risk increase. "
            "Seek care if fever lasts >48-72 hours, is very high, or there is breathing trouble, severe weakness, or confusion."
        ),
    },
    {
        "label": "Cough / Breathing",
        "terms": ["cough", "breath", "breathing", "shortness of breath", "wheezing"],
        "guidance": (
            "If cough/breathlessness worsens, it may progress to a chest infection or an asthma-like flare. "
            "Seek urgent care for severe breathlessness, blue lips, chest pain, or low oxygen symptoms."
        ),
    },
    {
        "label": "Sore throat",
        "terms": ["sore throat", "throat pain", "tonsil", "tonsillitis"],
        "guidance": (
            "If throat pain worsens, swallowing becomes difficult, or high fever develops, it may need medical review. "
            "Seek urgent care for breathing difficulty, drooling, or inability to swallow fluids."
        ),
    },
    {
        "label": "Nausea / Vomiting",
        "terms": ["nausea", "vomiting", "throwing up"],
        "guidance": (
            "If vomiting continues, dehydration can develop quickly. "
            "Seek care for dizziness, very low urine, blood in vomit, or inability to keep fluids down."
        ),
    },
    {
        "label": "Diarrhea / Stomach upset",
        "terms": ["diarrhea", "loose motion", "stomach", "abdominal pain", "stomach pain"],
        "guidance": (
            "If diarrhea/abdominal pain worsens, dehydration and electrolyte imbalance risk increases. "
            "Seek care for severe pain, blood in stool, persistent vomiting, or signs of dehydration."
        ),
    },
    {
        "label": "Rash / Allergy",
        "terms": ["rash", "itch", "itching", "hives", "allergy"],
        "guidance": (
            "If rash/itching spreads or swelling develops, it may become a more serious allergic reaction. "
            "Seek urgent care for facial/lip swelling, wheezing, or trouble breathing."
        ),
    },
    {
        "label": "Chest pain",
        "terms": ["chest pain", "chest tightness", "tightness", "pressure"],
        "guidance": (
            "Worsening chest pain can be serious. "
            "Seek emergency care if chest pain is severe, lasts >10 minutes, or occurs with sweating, nausea, fainting, or left-arm/jaw pain."
        ),
    },
    {
        "label": "Urinary burning",
        "terms": ["burning urination", "burning urine", "uti", "urination pain", "frequent urination"],
        "guidance": (
            "If urinary burning worsens or fever/back pain develops, it can spread to the kidneys. "
            "Seek medical care for fever, flank/back pain, vomiting, or blood in urine."
        ),
    },
    {
        "label": "Back / nerve pain",
        "terms": ["back pain", "sciatica", "radiating", "numbness", "tingling", "neck pain"],
        "guidance": (
            "If pain starts radiating with numbness/weakness, it may involve nerve irritation. "
            "Seek urgent care for new weakness, loss of bladder/bowel control, or severe worsening pain."
        ),
    },
    {
        "label": "Joint / knee pain",
        "terms": ["knee pain", "joint pain", "swelling", "sprain"],
        "guidance": (
            "If swelling and pain increase, it could be worsening inflammation or an injury needing examination. "
            "Seek care if you cannot bear weight, there is marked swelling/redness, or fever."
        ),
    },
    {
        "label": "Tooth pain",
        "terms": ["tooth pain", "toothache", "gum pain", "dental"],
        "guidance": (
            "If tooth pain worsens with swelling/fever, infection can spread. "
            "See a dentist/doctor urgently for facial swelling, fever, or difficulty opening the mouth."
        ),
    },
]


def _extract_symptom_phrases(message: str) -> list[str]:
    message = normalize_symptom_message(message)
    if not message:
        return []

    text = re.sub(r"[\n;|]+", ",", message)
    text = re.sub(r"\s+(and|&|\+)\s+", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"[.?!]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    raw_parts = [p.strip(" ,:-").strip() for p in text.split(",")]
    results: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        if not part:
            continue
        part = re.sub(r"^(i have|having|suffering from|i am having|my)\s+", "", part, flags=re.IGNORECASE).strip()
        part = re.sub(r"(since|for)\s+.+$", "", part, flags=re.IGNORECASE).strip()
        part = re.sub(r"(mild|moderate|severe|very)\s+", "", part, flags=re.IGNORECASE).strip()
        if not part:
            continue
        if len(part) > 60:
            continue
        if len(part.split()) > 6:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(part)
        if len(results) >= 6:
            break
    return results


def build_symptom_progression_lines(message: str) -> List[str]:
    message = normalize_symptom_message(message)
    raw_text = (message or "").lower()
    clean_tokens = {tok for tok in preprocess_text(message or "").split() if tok}

    phrases = _extract_symptom_phrases(message)

    def _rule_for_phrase(phrase: str):
        p_raw = (phrase or "").lower().strip()
        if not p_raw:
            return None
        phrase_tokens = {tok for tok in preprocess_text(phrase).split() if tok}
        for rule in _SYMPTOM_PROGRESSION_RULES:
            terms = [str(t) for t in rule.get("terms", [])]
            if any(_term_matches_message(t, p_raw, phrase_tokens) for t in terms):
                return rule
        return None

    lines: list[str] = []
    used_labels: set[str] = set()
    used_phrases: set[str] = set()

    for phrase in phrases:
        rule = _rule_for_phrase(phrase)
        if rule:
            label = str(rule.get("label") or "").strip()
            guidance = str(rule.get("guidance") or "").strip()
            if label and guidance and label.lower() not in used_labels:
                used_labels.add(label.lower())
                used_phrases.add(phrase.lower())
                lines.append(f"- {label}: {guidance}")
            continue

        phrase_clean = phrase.strip()
        if phrase_clean and phrase_clean.lower() not in used_phrases:
            used_phrases.add(phrase_clean.lower())
            lines.append(
                f"- {phrase_clean}: If this gets worse, lasts more than 48-72 hours, or new concerning symptoms appear, consult a doctor."
            )

    if not lines:
        for rule in _SYMPTOM_PROGRESSION_RULES:
            terms = [str(t) for t in rule.get("terms", [])]
            if any(_term_matches_message(t, raw_text, clean_tokens) for t in terms):
                label = str(rule.get("label") or "").strip()
                guidance = str(rule.get("guidance") or "").strip()
                if label and guidance and label.lower() not in used_labels:
                    used_labels.add(label.lower())
                    lines.append(f"- {label}: {guidance}")
                if len(lines) >= 4:
                    break

    return lines[:6]
def build_severity_prompt_text(predicted_disease: str) -> str:
    predicted = (predicted_disease or "General Symptom Review").strip() or "General Symptom Review"
    return "\n".join(
        [
            f"Condition: {predicted}",
            "",
            "Select severity:",
            "Mild   Moderate   Severe",
        ]
    )



def _maps_search_url(query: str) -> str:
    from urllib.parse import quote_plus

    q = quote_plus((query or '').strip())
    return f"https://www.google.com/maps/search/?api=1&query={q}" if q else "https://www.google.com/maps"


def build_severe_care_locations(message: str, predicted_disease: str) -> List[Dict[str, str]]:
    """Return a single place-type suggestion (not specific hospitals) for severe symptoms.

    We avoid naming "best hospitals" without verified, location-specific data.
    The returned link opens a Google Maps search that the user's device can localize ("near me").
    """

    msg = preprocess_text(normalize_symptom_message(message) or "")
    predicted = str(predicted_disease or "").strip().lower()
    text_blob = f"{predicted} {msg}".strip()

    def one(name: str, query: str) -> List[Dict[str, str]]:
        return [{"name": name, "maps_url": _maps_search_url(query)}]

    # Emergency-first patterns
    if any(k in text_blob for k in ["chest", "cardiac", "heart", "left arm", "pressure", "tightness"]):
        return one("Emergency hospital (24x7) near me", "emergency hospital near me")

    if any(k in text_blob for k in ["severe breath", "shortness", "breathing difficulty", "wheezing", "low oxygen"]):
        return one("Emergency hospital (24x7) near me", "emergency hospital near me")

    # Symptom-to-specialist mapping (pick ONE)
    if any(k in text_blob for k in ["vomit", "vomiting", "diarr", "abdominal", "stomach", "acidity", "burning", "gastr", "food poisoning"]):
        return one("Gastroenterologist near me", "gastroenterologist near me")

    if any(k in text_blob for k in ["headache", "migraine", "photophobia", "light sensitivity"]):
        return one("Neurologist near me", "neurologist near me")

    if any(k in text_blob for k in ["eye", "vision", "blur", "redness", "conjunct"]):
        return one("Eye hospital / ophthalmologist near me", "eye hospital near me")

    if any(k in text_blob for k in ["rash", "itch", "hives", "allergy"]):
        return one("Dermatologist near me", "dermatologist near me")

    if any(k in text_blob for k in ["burning urination", "uti", "urination", "kidney", "flank"]):
        return one("Urologist near me", "urologist near me")

    if any(k in text_blob for k in ["tooth", "gum", "dental"]):
        return one("Dentist near me", "dentist near me")

    if any(k in text_blob for k in ["knee", "joint", "sprain", "back pain", "neck pain", "sciatica"]):
        return one("Orthopedist near me", "orthopedic doctor near me")

    return one("General physician near me", "general physician near me")


def build_severity_response_text(result: Dict[str, Any], severity: str) -> str:
    predicted = str(result.get("predicted_disease", "General Symptom Review")).strip() or "General Symptom Review"
    tablets = str(result.get("tablets", "")).strip() or "-"
    remedies = str(result.get("natural_medicine", "")).strip() or "-"
    advice = _strip_disclaimer(str(result.get("advice", "")).strip()) or "-"
    progression = str(result.get("progression", "")).strip() or _progression_guidance_for_condition(predicted)


    symptom_progression_lines = build_symptom_progression_lines(str(result.get("message") or ""))
    severity = (severity or "").strip().lower()

    lines = [f"Condition: {predicted}"]

    if severity == "mild":
        lines.append(f"Natural medicine: {remedies}")
        lines.append(f"Advice: {advice}")
        lines.append(f"If symptoms worsen: {progression}")
    elif severity == "moderate":
        lines.append(f"Tablets: {tablets}")
        lines.append(f"Natural medicine: {remedies}")
        lines.append(f"Advice: {advice}")
        lines.append(f"If symptoms worsen: {progression}")
    elif severity == "severe":
        lines.append("Doctor immediately: Please seek urgent medical care or contact a doctor now.")
        lines.append(f"Advice: {advice}")

        care_locations = build_severe_care_locations(str(result.get("message") or ""), predicted)
        if care_locations:
            best_name = str(care_locations[0].get('name', '')).strip()
            if best_name:
                lines.append(f"Best place to go: {best_name}")
    else:
        lines.append(f"Tablets: {tablets}")
        lines.append(f"Natural medicine: {remedies}")
        lines.append(f"Advice: {advice}")
        lines.append(f"If symptoms worsen: {progression}")

    if severity != "severe" and symptom_progression_lines:
        lines.append("If each symptom worsens (possible progression):")
        lines.extend(symptom_progression_lines)

    return "\n".join(lines)


def build_chat_response_text(result: Dict[str, Any]) -> str:
    predicted = str(result.get("predicted_disease", "General Symptom Review")).strip() or "General Symptom Review"
    tablets = str(result.get("tablets", "")).strip() or "-"
    remedies = str(result.get("natural_medicine", "")).strip() or "-"
    advice = _strip_disclaimer(str(result.get("advice", "")).strip()) or "-"
    progression = str(result.get("progression", "")).strip() or _progression_guidance_for_condition(predicted)

    symptom_progression_lines = build_symptom_progression_lines(str(result.get("message") or ""))

    lines = [
        f"Condition: {predicted}",
        f"Tablets: {tablets}",
        f"Natural medicine: {remedies}",
        f"Advice: {advice}",
        f"If symptoms worsen: {progression}",
    ]

    if symptom_progression_lines:
        lines.append("If each symptom worsens (possible progression):")
        lines.extend(symptom_progression_lines)

    return "\n".join(lines)


def translate_to_english(text: str) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return text

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "Translate the following text into English. "
        "Keep medicine names/doses as-is. Do not add any extra medical advice. "
        "Return only the translated plain text."
        f"TEXT:{text}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return text

    candidates = data.get("candidates", [])
    if not candidates:
        return text

    parts = candidates[0].get("content", {}).get("parts", [])
    translated = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    return translated or text


def transcribe_kannada_audio_to_english(audio_file) -> str:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return ""

    mime_type = mimetypes.guess_type(getattr(audio_file, "name", ""))[0] or "audio/wav"
    audio_bytes = audio_file.read()
    encoded = base64.b64encode(audio_bytes).decode("utf-8")

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You will receive a Kannada (kn-IN) voice recording describing health symptoms. "
        "Transcribe it and translate it to English in one step. "
        "Return only JSON with keys exactly: transcript_en"
        "Rules:"
        "- transcript_en must be English text only."
        "- Do not add medical advice."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=35)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return ""

    candidates = data.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)
    transcript_en = str(parsed.get("transcript_en", "")).strip()
    return transcript_en


def build_prescription_response_text(result: Dict[str, Any]) -> str:
    summary = (result.get("summary") or "").strip()
    warnings = result.get("warnings") or []
    medicines = result.get("medicines") or []
    tests = result.get("tests") or []
    tablets_note = (result.get("tablets_note") or "").strip()
    home_remedies = result.get("home_remedies") or []
    questions = result.get("questions_for_doctor") or []

    lines = ["Prescription Summary", "", summary or DISCLAIMER_EN]

    if tablets_note:
        lines.extend(["", "Notes from prescription", "", f"- {tablets_note}"])

    if isinstance(medicines, list) and medicines:
        lines.extend(["", "Medicines (best-effort from image)", ""])
        for med in medicines:
            if not isinstance(med, dict):
                continue
            parts = [
                str(med.get("name") or "").strip(),
                str(med.get("strength") or "").strip(),
                str(med.get("dosage") or "").strip(),
                str(med.get("frequency") or "").strip(),
                str(med.get("duration") or "").strip(),
                str(med.get("instructions") or "").strip(),
            ]
            parts = [p for p in parts if p]
            if parts:
                lines.append(f"- {', '.join(parts)}")

    if isinstance(tests, list) and tests:
        lines.extend(["", "Tests mentioned", ""])
        for t in tests:
            t = str(t).strip()
            if t:
                lines.append(f"- {t}")

    if isinstance(home_remedies, list) and home_remedies:
        lines.extend(["", "Safe self-care", ""])
        for item in home_remedies:
            item = str(item).strip()
            if item:
                lines.append(f"- {item}")

    if isinstance(warnings, list) and warnings:
        lines.extend(["", "Safety notes", ""])
        for w in warnings:
            w = str(w).strip()
            if w:
                lines.append(f"- {w}")

    if isinstance(questions, list) and questions:
        lines.extend(["", "Questions to ask your doctor/pharmacist", ""])
        for q in questions:
            q = str(q).strip()
            if q:
                lines.append(f"- {q}")

    return "\n".join(lines)

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def is_twilio_calling_enabled() -> bool:
    return bool(
        getattr(settings, "TWILIO_ACCOUNT_SID", "").strip()
        and getattr(settings, "TWILIO_AUTH_TOKEN", "").strip()
        and getattr(settings, "TWILIO_FROM_NUMBER", "").strip()
    )


def initiate_twilio_callback(to_number: str, bridge_to: str | None = None) -> Dict[str, Any]:
    """Initiate an outbound call to `to_number` using Twilio.

    Note: This requires internet access from the server running Django.
    """

    to_number = str(to_number or "").strip()
    if not _E164_RE.match(to_number):
        return {"ok": False, "detail": "Phone number must be in E.164 format (example: +919999999999)."}

    if not is_twilio_calling_enabled():
        return {"ok": False, "detail": "Calling provider is not configured."}

    account_sid = settings.TWILIO_ACCOUNT_SID.strip()
    auth_token = settings.TWILIO_AUTH_TOKEN.strip()
    from_number = settings.TWILIO_FROM_NUMBER.strip()

    bridge_to = (bridge_to or "").strip() or None

    # Minimal TwiML without requiring a public webhook.
    twiml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Response>',
        '<Say voice="alice">This is Health AI Chatbot. Connecting you for help.</Say>',
    ]
    if bridge_to and _E164_RE.match(bridge_to):
        twiml_parts.append(f"<Dial>{bridge_to}</Dial>")
    else:
        twiml_parts.append('<Pause length="2"/>')
        twiml_parts.append('<Say voice="alice">If this is an emergency, please contact your local emergency number.</Say>')

    twiml_parts.append("</Response>")
    twiml = "".join(twiml_parts)

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    payload = {
        "To": to_number,
        "From": from_number,
        "Twiml": twiml,
    }

    try:
        resp = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=25)
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
    except requests.RequestException:
        return {"ok": False, "detail": "Failed to initiate call (provider request error)."}

    return {
        "ok": True,
        "call_sid": str(data.get("sid") or ""),
        "status": str(data.get("status") or ""),
        "to": to_number,
    }


def _find_catalog_item_by_image_key(image_key: str) -> Dict[str, Any] | None:
    key = str(image_key or "").strip().lower()
    if not key:
        return None
    for item in TABLET_SUGGESTION_CATALOG:
        if str(item.get("image_key") or "").strip().lower() == key:
            return item
    return None


def analyze_medicine_image(image_file, hint_text: str = "") -> Dict[str, Any]:
    """Identify a medicine/tablet from its packaging image and return safe, basic uses.

    This function is intentionally cautious:
    - Uses local image matching first (no internet required) for known reference images.
    - If configured, may attempt Gemini vision as a secondary option.
    - Adds a *general* food-timing note when we can map to a known catalog item.
    """

    try:
        image_file.seek(0)
    except Exception:
        pass

    image_bytes = image_file.read() if hasattr(image_file, "read") else b""

    try:
        image_file.seek(0)
    except Exception:
        pass

    # 1) Local perceptual-hash match against known images
    local_match = match_uploaded_medicine_image(image_bytes or b"")
    if local_match:
        image_key = str(local_match.get("image_key") or "").strip().lower()
        catalog_item = _find_catalog_item_by_image_key(image_key) or {}
        name = str(catalog_item.get("name") or "Medicine").strip() or "Medicine"
        uses = str(catalog_item.get("use") or "Used for symptom relief (for reference only).").strip()
        food_timing = get_food_timing_for_image_key(image_key)
        return {
            "ok": True,
            "needs_reupload": False,
            "medicine_name": name,
            "confidence": float(local_match.get("confidence") or 0.65),
            "uses": uses,
            "food_timing": food_timing,
            "safety_note": build_medicine_safety_note("Follow the label/prescription. Do not self-medicate if unsure."),
        }

    api_key = settings.GEMINI_API_KEY

    # 2) If no vision key, fall back to text-based catalog matching
    if not api_key:
        catalog_match = find_best_tablet_catalog_match(hint_text)
        if catalog_match and catalog_match.get("use"):
            key = str(catalog_match.get("image_key") or "").strip().lower()
            return {
                "ok": True,
                "needs_reupload": False,
                "medicine_name": str(catalog_match.get("name") or "Medicine"),
                "confidence": 0.35,
                "uses": str(catalog_match.get("use") or "").strip(),
                "food_timing": get_food_timing_for_image_key(key),
                "safety_note": build_medicine_safety_note("For reference only."),
            }

        return {
            "ok": False,
            "needs_reupload": False,
            "detail": (
                "I can't analyze medicine photos right now. "
                "Please type the tablet/medicine name printed on the cover (example: Dolokind-Plus)."
            ),
        }

    # 3) Gemini vision (internet required). Keep response cautious; we do NOT ask Gemini for dosing.
    mime_type = mimetypes.guess_type(getattr(image_file, "name", ""))[0] or "image/jpeg"
    encoded = base64.b64encode(image_bytes or b"").decode("utf-8")

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are a cautious medical assistant. The user uploaded a photo of a tablet/medicine. "
        "First decide if the image is usable: if it is blurry, too dark, cropped, or missing the cover/label text, mark it as needs_reupload. "
        "If usable, identify the medicine name (brand/generic if visible) and provide its typical use/purpose in 1-2 lines. "
        "Return ONLY JSON with keys exactly: needs_reupload (boolean), reupload_reason (string), medicine_name (string), confidence (0..1), uses (string), safety_note (string). "
        "Rules: "
        "- If not sure, set needs_reupload=true with a clear reason. "
        "- Do NOT give dosing. "
        "- safety_note must include 'For reference only. Consult a doctor/pharmacist.'"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        catalog_match = find_best_tablet_catalog_match(hint_text)
        if catalog_match and catalog_match.get("use"):
            key = str(catalog_match.get("image_key") or "").strip().lower()
            return {
                "ok": True,
                "needs_reupload": False,
                "medicine_name": str(catalog_match.get("name") or "Medicine"),
                "confidence": 0.35,
                "uses": str(catalog_match.get("use") or "").strip(),
                "food_timing": get_food_timing_for_image_key(key),
                "safety_note": build_medicine_safety_note("For reference only."),
            }

        return {
            "ok": False,
            "needs_reupload": False,
            "detail": "Failed to analyze image right now. Please type the medicine name.",
        }

    candidates = data.get("candidates", [])
    if not candidates:
        return {"ok": False, "needs_reupload": True, "detail": "Couldn't identify the tablet from the image. Type the tablet name printed on it."}

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)

    needs_reupload = bool(parsed.get("needs_reupload"))
    reupload_reason = str(parsed.get("reupload_reason") or "").strip()

    if needs_reupload:
        return {
            "ok": False,
            "needs_reupload": True,
            "detail": "Couldn't identify the tablet from the image. Type the tablet name printed on it.",
        }

    medicine_name = str(parsed.get("medicine_name") or "").strip()
    confidence = parsed.get("confidence")
    uses = str(parsed.get("uses") or "").strip()
    safety_note = str(parsed.get("safety_note") or "").strip()

    if not medicine_name:
        return {
            "ok": False,
            "needs_reupload": True,
            "detail": "Couldn't identify the tablet from the image. Type the tablet name printed on it.",
        }

    food_timing = ""
    catalog_match = find_best_tablet_catalog_match(medicine_name)
    if catalog_match and catalog_match.get("use"):
        uses = str(catalog_match.get("use")).strip()
        food_timing = get_food_timing_for_image_key(str(catalog_match.get("image_key") or ""))

    if not safety_note:
        safety_note = "For reference only. Consult a doctor/pharmacist."
    if "consult" not in safety_note.lower():
        safety_note = (safety_note + " For reference only. Consult a doctor/pharmacist.").strip()

    return {
        "ok": True,
        "needs_reupload": False,
        "medicine_name": medicine_name,
        "confidence": confidence,
        "uses": uses or "Used for symptom relief (for reference only).",
        "food_timing": food_timing,
        "safety_note": safety_note,
    }


def build_medicine_response_text(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        detail = str(result.get("detail") or "Couldn't identify the tablet from the image. Type the tablet name printed on it.").strip()
        return "Medicine Image Result\n\n" + detail

    name = str(result.get("medicine_name") or "Medicine").strip() or "Medicine"
    uses = str(result.get("uses") or "").strip() or "-"
    timing = str(result.get("food_timing") or "").strip()
    safety = str(result.get("safety_note") or "").strip() or "For reference only. Consult a doctor/pharmacist."

    lines = [
        "Medicine Image Result",
        f"Name: {name}",
        f"Uses: {uses}",
    ]
    if timing:
        lines.append(f"Food timing: {timing}")
    lines.append(f"Safety: {safety}")
    return "\n".join(lines)


def classify_uploaded_image(image_file) -> Dict[str, Any]:
    """Classify an uploaded image into a handling bucket.

    Returns JSON-like dict with keys: kind, needs_reupload, reupload_reason.
    """

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {
            "kind": "other",
            "needs_reupload": False,
            "reupload_reason": "",
        }

    mime_type = mimetypes.guess_type(getattr(image_file, "name", ""))[0] or "image/jpeg"
    image_bytes = image_file.read()
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    endpoint = f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are triaging a user-uploaded health-related image. "
        "Decide what the image most likely is: "
        "(medicine/tablet packaging), (doctor prescription), (skin rash / external skin issue), (eye redness), or (other). "
        "Also decide if the image is unusable (blurry, too dark, cropped, missing the relevant label/cover). "
        "Return ONLY JSON with keys exactly: kind, needs_reupload, reupload_reason. "
        "kind must be one of: medicine, prescription, skin_rash, eye_redness, other. "
        "If needs_reupload is true, reupload_reason must tell the user what to do (e.g., 'upload a clear cover/label photo')."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return {"kind": "other", "needs_reupload": False, "reupload_reason": ""}

    candidates = data.get("candidates", [])
    if not candidates:
        return {"kind": "other", "needs_reupload": True, "reupload_reason": "Couldn't analyze the image. Please type a short description (symptoms/tablet name)."}

    parts = candidates[0].get("content", {}).get("parts", [])
    model_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    parsed = _extract_json_block(model_text)

    kind = str(parsed.get("kind") or "other").strip().lower()
    if kind not in {"medicine", "prescription", "skin_rash", "eye_redness", "other"}:
        kind = "other"

    needs_reupload = bool(parsed.get("needs_reupload"))
    reupload_reason = str(parsed.get("reupload_reason") or "").strip()

    return {
        "kind": kind,
        "needs_reupload": needs_reupload,
        "reupload_reason": reupload_reason,
    }


def build_symptom_image_response_text(result: Dict[str, Any], title: str = "Image Analysis") -> str:
    guidance = str(result.get("guidance") or "").strip()
    if title.lower().startswith("skin") and guidance:
        return guidance

    assessment = str(result.get("assessment") or "-").strip() or "-"
    confidence = result.get("confidence")
    conf_text = str(confidence) if confidence is not None else "-"
    return "\n".join([
        title,
        f"Assessment: {assessment}",
        f"Confidence: {conf_text}",
        f"Guidance: {guidance or '-'}",
    ])

def analyze_auto_image_message(image_file, message: str = "") -> Dict[str, Any]:
    """Route any image upload to the right analysis path."""

    # We need to read the file multiple times, so keep resetting.
    image_file.seek(0)
    classification = classify_uploaded_image(image_file)
    image_file.seek(0)

    if classification.get("needs_reupload"):
        # Some clear medicine cover photos get misclassified as "other" or "needs_reupload".
        # Try medicine detection once before asking the user to re-upload.
        image_file.seek(0)
        med_try = analyze_medicine_image(image_file, hint_text=message)
        image_file.seek(0)
        if med_try.get("ok"):
            response_text = build_medicine_response_text(med_try)
            return {
                "ok": True,
                "needs_reupload": False,
                "kind": "medicine",
                "response_text": response_text,
                "speech_text": translate_to_kannada(response_text),
            }

        reason = str(classification.get("reupload_reason") or "").strip() or "Couldn't analyze the image. Please type a short description (symptoms/tablet name)."
        return {"ok": False, "needs_reupload": True, "detail": reason, "kind": classification.get("kind")}

    kind = str(classification.get("kind") or "other")
    if kind == "other":
        # If the classifier couldn't decide, try medicine recognition once.
        image_file.seek(0)
        med_try = analyze_medicine_image(image_file, hint_text=message)
        image_file.seek(0)
        if med_try.get("ok"):
            response_text = build_medicine_response_text(med_try)
            return {
                "ok": True,
                "needs_reupload": False,
                "kind": "medicine",
                "response_text": response_text,
                "speech_text": translate_to_kannada(response_text),
            }

        guess = guess_image_kind_from_message(message)
        if guess and guess != "other":
            kind = guess

    if kind == "prescription":
        result = analyze_prescription_image(image_file, user_context=message)
        response_text = build_prescription_response_text(result)
        return {
            "ok": True,
            "needs_reupload": False,
            "kind": kind,
            "response_text": response_text,
            "speech_text": translate_to_kannada(response_text),
        }

    if kind == "medicine":
        result = analyze_medicine_image(image_file, hint_text=message)
        response_text = build_medicine_response_text(result)

        if not result.get("ok"):
            if result.get("needs_reupload"):
                return {"ok": False, "needs_reupload": True, "detail": str(result.get("detail") or "Couldn't identify the tablet from the image. Type the tablet name printed on it."), "kind": kind}
            return {
                "ok": False,
                "needs_reupload": False,
                "kind": kind,
                "detail": str(result.get("detail") or "Please type the tablet/medicine name from the cover."),
                "response_text": response_text,
                "speech_text": translate_to_kannada(response_text),
            }

        return {
            "ok": True,
            "needs_reupload": False,
            "kind": kind,
            "response_text": response_text,
            "speech_text": translate_to_kannada(response_text),
        }

    if kind in {"skin_rash", "eye_redness"}:
        result = analyze_symptom_image(image_file, kind)
        if result.get("needs_reupload"):
            reason = str(result.get("reupload_reason") or "Couldn't analyze the image. Please describe the issue in text.").strip()
            return {"ok": False, "needs_reupload": True, "detail": reason, "kind": kind}

        title = "Skin Image Analysis" if kind == "skin_rash" else "Eye Image Analysis"
        response_text = build_symptom_image_response_text(result, title=title)
        return {
            "ok": True,
            "needs_reupload": False,
            "kind": kind,
            "response_text": response_text,
            "speech_text": translate_to_kannada(response_text),
        }

    # Unknown image: encourage user to describe symptoms.
    detail = "Upload a clear tablet/medicine cover (label) photo, or type the tablet name."
    return {"ok": False, "needs_reupload": True, "detail": detail, "kind": "other"}
