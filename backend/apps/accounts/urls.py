from django.urls import path

from .views import (
    LoginView,
    LogoutFeedbackView,
    MeView,
    RegisterView,
    SendEmailOtpView,
    SendMobileOtpView,
    VerifyEmailOtpView,
    VerifyMobileOtpView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("otp/email/send/", SendEmailOtpView.as_view(), name="send_email_otp"),
    path("otp/email/verify/", VerifyEmailOtpView.as_view(), name="verify_email_otp"),
    path("otp/mobile/send/", SendMobileOtpView.as_view(), name="send_mobile_otp"),
    path("otp/mobile/verify/", VerifyMobileOtpView.as_view(), name="verify_mobile_otp"),
    path("logout-feedback/", LogoutFeedbackView.as_view(), name="logout_feedback"),
    path("me/", MeView.as_view(), name="me"),
]
