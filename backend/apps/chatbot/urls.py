from django.urls import path

from .views import (
    AutoImageMessageView,
    ChatHistoryView,
    ChatRatingView,
    ChatbotMessageView,
    EmergencyCallConfigView,
    InitiateHelpCallView,
    MedicineChatMessageView,
    PrescriptionChatMessageView,
    PrescriptionHelperView,
    SeverityResponseView,
    SymptomImageAnalysisView,
    SymptomPredictionView,
    TranslateToEnglishView,
    VoiceChatMessageView,
    TextToSpeechView,
)

urlpatterns = [
    path("predict/", SymptomPredictionView.as_view(), name="chat-predict"),
    path("message/", ChatbotMessageView.as_view(), name="chat-message"),
    path("image-auto/", AutoImageMessageView.as_view(), name="chat-image-auto"),
    path("severity/", SeverityResponseView.as_view(), name="chat-severity"),
    path("history/", ChatHistoryView.as_view(), name="chat-history"),
    path("image-analysis/", SymptomImageAnalysisView.as_view(), name="chat-image-analysis"),
    path("ratings/", ChatRatingView.as_view(), name="chat-ratings"),
    path("call-config/", EmergencyCallConfigView.as_view(), name="chat-call-config"),
    path("call/", InitiateHelpCallView.as_view(), name="chat-call"),
    path("prescription/", PrescriptionHelperView.as_view(), name="chat-prescription"),
    path("prescription-message/", PrescriptionChatMessageView.as_view(), name="chat-prescription-message"),
    path("medicine-message/", MedicineChatMessageView.as_view(), name="chat-medicine-message"),
    path("voice/", VoiceChatMessageView.as_view(), name="chat-voice"),
    path("voice/", VoiceChatMessageView.as_view(), name="chat-voice"),
    path("tts/", TextToSpeechView.as_view(), name="chat-tts"),
    path("translate/", TranslateToEnglishView.as_view(), name="chat-translate"),
]
