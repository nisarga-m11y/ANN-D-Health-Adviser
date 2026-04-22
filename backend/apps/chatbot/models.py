from django.conf import settings
from django.db import models


class SymptomsData(models.Model):
    symptom = models.TextField()
    disease = models.CharField(max_length=200)

    class Meta:
        db_table = "symptoms_data"

    def __str__(self):
        return f"{self.symptom[:40]} -> {self.disease}"


class ChatHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_history")
    message = models.TextField()
    image = models.FileField(upload_to="chat_images/", null=True, blank=True)
    response = models.TextField()
    predicted_disease = models.CharField(max_length=200, blank=True)
    advice = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_history"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.email} @ {self.timestamp}"



class SymptomImageAnalysis(models.Model):
    CATEGORY_CHOICES = [
        ("skin_rash", "Skin Rash"),
        ("eye_redness", "Eye Redness"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="image_analyses")
    image = models.FileField(upload_to="symptom_images/")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    assessment = models.CharField(max_length=200)
    confidence = models.FloatField(default=0.0)
    guidance = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "symptom_image_analysis"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} {self.category} @ {self.created_at}"


class ChatRating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_ratings")
    chat = models.ForeignKey(ChatHistory, on_delete=models.CASCADE, related_name="ratings")
    rating = models.PositiveSmallIntegerField()
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_rating"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "chat"], name="unique_chat_rating_per_user"),
        ]

    def __str__(self):
        return f"{self.user.email} rated {self.rating}/5 for chat {self.chat_id}"
