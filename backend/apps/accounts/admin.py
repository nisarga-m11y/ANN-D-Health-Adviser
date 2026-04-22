from django.contrib import admin

from .models import LogoutFeedback, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "is_active", "is_staff", "date_joined")
    search_fields = ("name", "email")


@admin.register(LogoutFeedback)
class LogoutFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "feedback")
