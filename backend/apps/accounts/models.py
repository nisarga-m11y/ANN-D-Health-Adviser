from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


class LogoutFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="logout_feedbacks")
    rating = models.PositiveSmallIntegerField()
    feedback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "logout_feedback"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} ({self.rating}/5)"
