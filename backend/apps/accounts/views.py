from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LogoutFeedback, User
from .otp import (
    can_send,
    clear_otp,
    clear_verified,
    generate_otp,
    mark_verified,
    normalize_email,
    normalize_phone,
    send_email_otp,
    simulate_sms_otp,
    store_otp,
    verify_otp,
)
from .serializers import LogoutFeedbackSerializer, LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutFeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LogoutFeedback.objects.create(
            user=request.user,
            rating=serializer.validated_data["rating"],
            feedback=serializer.validated_data.get("feedback", ""),
        )
        return Response({"detail": "Thank you for your feedback."}, status=status.HTTP_201_CREATED)


class SendEmailOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        expires_in = int(getattr(settings, "OTP_EXPIRY_SECONDS", 60))
        allowed, remaining = can_send("email", email)
        if not allowed:
            return Response(
                {"detail": "OTP already sent. Please wait.", "retry_after": remaining},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = generate_otp()
        store_otp("email", email, otp, expires_in_seconds=expires_in)
        clear_verified("email", email)
        sent, error = send_email_otp(email, otp, expires_in_seconds=expires_in)
        if not sent:
            if getattr(settings, "OTP_DEBUG_RETURN_CODE", settings.DEBUG):
                return Response(
                    {
                        "detail": "SMTP is not configured. Using debug OTP for local development.",
                        "expires_in": expires_in,
                        "debug_otp": otp,
                    }
                )
            clear_otp("email", email)
            return Response(
                {"detail": f"Unable to send OTP email. {error}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = {"detail": "OTP sent.", "expires_in": expires_in}
        if getattr(settings, "OTP_DEBUG_RETURN_CODE", settings.DEBUG):
            response["debug_otp"] = otp
        return Response(response)


class VerifyEmailOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = normalize_email(request.data.get("email"))
        otp = str(request.data.get("otp") or "").strip()
        if not email or not otp:
            return Response(
                {"detail": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ok, error = verify_otp("email", email, otp)
        if not ok:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        mark_verified("email", email, expires_in_seconds=int(getattr(settings, "OTP_EXPIRY_SECONDS", 60)) * 10)

        user = User.objects.filter(email=email).first()
        if not user:
            name_guess = email.split("@", 1)[0].replace(".", " ").strip() or "User"
            try:
                with transaction.atomic():
                    user = User.objects.create_user(email=email, name=name_guess, password=None)
            except IntegrityError:
                user = User.objects.get(email=email)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class SendMobileOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = normalize_phone(request.data.get("phone"))
        if not phone:
            return Response({"detail": "Mobile number is required."}, status=status.HTTP_400_BAD_REQUEST)

        expires_in = int(getattr(settings, "OTP_EXPIRY_SECONDS", 60))
        allowed, remaining = can_send("mobile", phone)
        if not allowed:
            return Response(
                {"detail": "OTP already sent. Please wait.", "retry_after": remaining},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = generate_otp()
        store_otp("mobile", phone, otp, expires_in_seconds=expires_in)
        simulate_sms_otp(phone, otp, expires_in_seconds=expires_in)

        return Response({"detail": "OTP sent.", "expires_in": expires_in})


class VerifyMobileOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = normalize_phone(request.data.get("phone"))
        otp = str(request.data.get("otp") or "").strip()
        if not phone or not otp:
            return Response(
                {"detail": "Mobile number and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ok, error = verify_otp("mobile", phone, otp)
        if not ok:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(phone_number=phone).first()
        if not user:
            base_digits = phone[1:] if phone.startswith("+") else phone
            base_email = f"mobile_{base_digits}@ann-d.local"
            name_guess = f"User {base_digits[-4:]}" if len(base_digits) >= 4 else "User"

            email_candidate = base_email
            for _attempt in range(6):
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            email=email_candidate,
                            name=name_guess,
                            password=None,
                            phone_number=phone,
                        )
                    break
                except IntegrityError:
                    suffix = generate_otp()
                    email_candidate = f"mobile_{base_digits}_{suffix}@ann-d.local"

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})
