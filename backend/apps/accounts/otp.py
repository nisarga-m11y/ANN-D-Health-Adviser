import logging
import re
import secrets
import time
from dataclasses import dataclass
from smtplib import SMTPAuthenticationError, SMTPException

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OtpSendResult:
    expires_in_seconds: int


def _now_ts() -> int:
    return int(time.time())


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


_PHONE_ALLOWED = re.compile(r"[^0-9+]")


def normalize_phone(phone: str) -> str:
    value = (phone or "").strip()
    value = _PHONE_ALLOWED.sub("", value)
    if value.startswith("+"):
        digits = "+" + re.sub(r"[^0-9]", "", value[1:])
        return digits if digits != "+" else ""
    return re.sub(r"[^0-9]", "", value)


def _cache_key(kind: str, identifier: str) -> str:
    return f"otp:{kind}:{identifier}"


def _verified_key(kind: str, identifier: str) -> str:
    return f"otp_verified:{kind}:{identifier}"


def can_send(kind: str, identifier: str) -> tuple[bool, int]:
    payload = cache.get(_cache_key(kind, identifier))
    if not payload:
        return True, 0
    expires_at = int(payload.get("expires_at", 0) or 0)
    remaining = max(0, expires_at - _now_ts())
    return remaining <= 0, remaining


def store_otp(kind: str, identifier: str, otp: str, expires_in_seconds: int) -> None:
    now = _now_ts()
    payload = {
        "otp_hash": make_password(otp),
        "sent_at": now,
        "expires_at": now + expires_in_seconds,
        "attempts": 0,
    }
    cache.set(_cache_key(kind, identifier), payload, timeout=expires_in_seconds)


def clear_otp(kind: str, identifier: str) -> None:
    cache.delete(_cache_key(kind, identifier))


def mark_verified(kind: str, identifier: str, *, expires_in_seconds: int) -> None:
    cache.set(_verified_key(kind, identifier), True, timeout=max(60, expires_in_seconds))


def consume_verified(kind: str, identifier: str) -> bool:
    key = _verified_key(kind, identifier)
    verified = bool(cache.get(key))
    if verified:
        cache.delete(key)
    return verified


def clear_verified(kind: str, identifier: str) -> None:
    cache.delete(_verified_key(kind, identifier))


def verify_otp(kind: str, identifier: str, otp: str, *, max_attempts: int = 5) -> tuple[bool, str]:
    key = _cache_key(kind, identifier)
    payload = cache.get(key)
    if not payload:
        return False, "OTP expired. Please resend."

    attempts = int(payload.get("attempts", 0) or 0) + 1
    payload["attempts"] = attempts
    cache.set(key, payload, timeout=max(1, int(payload.get("expires_at", 0)) - _now_ts()))

    if attempts > max_attempts:
        cache.delete(key)
        return False, "Too many attempts. Please resend OTP."

    otp_hash = payload.get("otp_hash") or ""
    if not check_password(str(otp).strip(), otp_hash):
        return False, "Invalid OTP."

    cache.delete(key)
    return True, ""


def send_email_otp(email: str, otp: str, *, expires_in_seconds: int) -> tuple[bool, str]:
    email_backend = str(getattr(settings, "EMAIL_BACKEND", "") or "")
    if "console.EmailBackend" in email_backend:
        return False, "Email backend is in console mode. Configure SMTP in backend/.env."

    missing = []
    if not str(getattr(settings, "EMAIL_HOST", "") or "").strip():
        missing.append("EMAIL_HOST")
    if not str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip():
        missing.append("EMAIL_HOST_USER")
    if not str(getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip():
        missing.append("EMAIL_HOST_PASSWORD")
    if missing:
        return False, f"Missing email configuration: {', '.join(missing)}."

    subject = "Your ANN-D Health Advisor OTP"
    message = (
        f"Your OTP is {otp}. It will expire in {expires_in_seconds} seconds.\n\n"
        "If you did not request this, you can ignore this email."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
        return True, ""
    except SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check email app password/credentials."
    except SMTPException as exc:
        return False, f"SMTP error: {exc}"
    except TimeoutError:
        return False, "SMTP connection timed out. Check internet/firewall and try again."
    except Exception as exc:
        return False, f"Email send failed: {exc}"


def simulate_sms_otp(phone: str, otp: str, *, expires_in_seconds: int) -> None:
    logger.info("Simulated SMS OTP to %s: %s (expires in %ss)", phone, otp, expires_in_seconds)
