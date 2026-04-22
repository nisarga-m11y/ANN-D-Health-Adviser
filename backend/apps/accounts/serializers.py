from django.contrib.auth import authenticate
from rest_framework import serializers

from .otp import consume_verified, normalize_email
from .models import LogoutFeedback, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "name", "email", "password"]

    def create(self, validated_data):
        email = normalize_email(validated_data["email"])
        name = validated_data.get("name", "")
        raw_password = validated_data["password"]
        verified = consume_verified("email", email)

        existing = User.objects.filter(email=email).first()
        if existing:
            # Allow OTP-verified users to complete registration or reset to a password.
            if existing.has_usable_password() and not verified:
                raise serializers.ValidationError({"email": "An account with this email already exists."})

            existing.name = name or existing.name
            existing.set_password(raw_password)
            existing.save(update_fields=["name", "password"])
            return existing

        return User.objects.create_user(email=email, name=name, password=raw_password)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(request=self.context.get("request"), username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phone_number"]


class LogoutFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogoutFeedback
        fields = ["rating", "feedback"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_feedback(self, value):
        return (value or "").strip()
