from django.contrib import admin

from .models import ChatHistory, ChatRating, SymptomImageAnalysis, SymptomsData


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "predicted_disease", "timestamp")
    search_fields = ("user__email", "message", "predicted_disease")
    list_filter = ("predicted_disease", "timestamp")


@admin.register(SymptomsData)
class SymptomsDataAdmin(admin.ModelAdmin):
    list_display = ("id", "symptom", "disease")
    search_fields = ("symptom", "disease")


@admin.register(SymptomImageAnalysis)
class SymptomImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "assessment", "confidence", "created_at")
    search_fields = ("user__email", "assessment", "guidance")
    list_filter = ("category", "created_at")


@admin.register(ChatRating)
class ChatRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "chat", "rating", "created_at")
    search_fields = ("user__email", "feedback")
    list_filter = ("rating", "created_at")
