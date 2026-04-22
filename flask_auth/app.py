from __future__ import annotations

import hashlib
import os
import re
import secrets
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Final

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)


OTP_TTL_SECONDS: Final[int] = 60
RESEND_COOLDOWN_SECONDS: Final[int] = 60
SEND_MIN_INTERVAL_SECONDS: Final[int] = 5
MAX_VERIFY_ATTEMPTS: Final[int] = 5


EMAIL_RE: Final[re.Pattern[str]] = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def create_app() -> Flask:
    repo_root = Path(__file__).resolve().parents[1]
    app_root = Path(__file__).resolve().parent
    chatbot_dir = Path(os.environ.get("CHATBOT_STATIC_DIR", repo_root / "ann-d-web"))
    chatbot_dir = chatbot_dir if chatbot_dir.is_absolute() else (repo_root / chatbot_dir)

    app = Flask(
        __name__,
        root_path=str(app_root),
        template_folder="templates",
        static_folder="static",
    )
    app.config["CHATBOT_DIR"] = str(chatbot_dir)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.get("/")
    def root():
        if session.get("logged_in"):
            return redirect(url_for("chatbot_index"))
        return redirect(url_for("auth_page"))

    @app.get("/auth")
    def auth_page():
        return render_template("auth.html")

    @app.post("/api/otp/email/send")
    def send_email_otp():
        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()

        if not EMAIL_RE.match(email):
            return jsonify(ok=False, message="Please enter a valid email."), 400

        send_guard_error = _send_guard()
        if send_guard_error:
            return jsonify(ok=False, message=send_guard_error), 429

        otp = _generate_otp()
        _store_otp(channel="email", target=email, otp=otp, secret_key=app.config["SECRET_KEY"])

        sent_via_email, email_error = _send_otp_via_gmail_smtp(
            to_email=email,
            otp=otp,
            ttl_seconds=OTP_TTL_SECONDS,
        )

        if not sent_via_email:
            _clear_otp()
            app.logger.warning("Email OTP send failed for %s: %s", email, email_error)
            return (
                jsonify(
                    ok=False,
                    message=f"Unable to send OTP email. {email_error}",
                ),
                503,
            )

        return jsonify(
            ok=True,
            message="OTP sent to email.",
            expires_in=OTP_TTL_SECONDS,
            resend_in=RESEND_COOLDOWN_SECONDS,
        )

    @app.post("/api/otp/mobile/send")
    def send_mobile_otp():
        payload = request.get_json(silent=True) or {}
        raw_mobile = (payload.get("mobile") or "").strip()
        mobile = _normalize_mobile(raw_mobile)
        if not mobile:
            return jsonify(ok=False, message="Please enter a valid mobile number."), 400

        send_guard_error = _send_guard()
        if send_guard_error:
            return jsonify(ok=False, message=send_guard_error), 429

        otp = _generate_otp()
        _store_otp(channel="mobile", target=mobile, otp=otp, secret_key=app.config["SECRET_KEY"])

        sms_sent = _send_otp_via_twilio_or_mock(mobile=mobile, otp=otp, ttl_seconds=OTP_TTL_SECONDS)
        if not sms_sent:
            app.logger.info("Mock SMS OTP for %s is %s (dev-only)", mobile, otp)

        return jsonify(
            ok=True,
            message="OTP sent to mobile." if sms_sent else "OTP generated (SMS mocked). Check server logs.",
            expires_in=OTP_TTL_SECONDS,
            resend_in=RESEND_COOLDOWN_SECONDS,
        )

    @app.post("/api/otp/verify")
    def verify_otp():
        payload = request.get_json(silent=True) or {}
        channel = (payload.get("channel") or "").strip().lower()
        otp = (payload.get("otp") or "").strip()

        if channel not in {"email", "mobile"}:
            return jsonify(ok=False, message="Invalid login method."), 400

        if not re.fullmatch(r"\d{6}", otp):
            return jsonify(ok=False, message="Enter the 6-digit OTP."), 400

        if session.get("otp_attempts", 0) >= MAX_VERIFY_ATTEMPTS:
            _clear_otp()
            return jsonify(ok=False, message="Too many attempts. Please request a new OTP."), 429

        stored_channel = session.get("otp_channel")
        stored_target = session.get("otp_target")
        stored_hash = session.get("otp_hash")
        expires_at = float(session.get("otp_expires_at", 0))

        if not stored_channel or not stored_target or not stored_hash:
            return jsonify(ok=False, message="No OTP request found. Please send OTP first."), 400

        if stored_channel != channel:
            return jsonify(ok=False, message="OTP method mismatch. Please request OTP again."), 400

        if time.time() > expires_at:
            _clear_otp()
            return jsonify(ok=False, message="OTP expired. Please resend OTP."), 400

        expected_hash = _hash_otp(
            otp=otp,
            channel=stored_channel,
            target=stored_target,
            secret_key=app.config["SECRET_KEY"],
        )

        if not secrets.compare_digest(expected_hash, stored_hash):
            session["otp_attempts"] = int(session.get("otp_attempts", 0)) + 1
            return jsonify(ok=False, message="Invalid OTP. Please try again."), 400

        session["logged_in"] = True
        session["user_channel"] = stored_channel
        session["user_target"] = stored_target
        _clear_otp()

        return jsonify(ok=True, message="Login successful.", redirect_url=url_for("chatbot_index"))

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("auth_page"))

    def _require_login():
        if not session.get("logged_in"):
            return redirect(url_for("auth_page"))
        return None

    @app.get("/chatbot/")
    def chatbot_index():
        gate = _require_login()
        if gate:
            return gate

        chatbot_dir = Path(app.config["CHATBOT_DIR"])
        return send_from_directory(chatbot_dir, "index.html")

    @app.get("/chatbot")
    def chatbot_index_no_slash():
        return redirect(url_for("chatbot_index"))

    @app.get("/chatbot/<path:filename>")
    def chatbot_assets(filename: str):
        gate = _require_login()
        if gate:
            return gate

        chatbot_dir = Path(app.config["CHATBOT_DIR"])
        return send_from_directory(chatbot_dir, filename)


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalize_mobile(raw: str) -> str | None:
    cleaned = re.sub(r"[^\d+]", "", raw)
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.startswith("+"):
        digits = re.sub(r"\D", "", cleaned)
        if 10 <= len(digits) <= 15:
            return "+" + digits
        return None

    digits = re.sub(r"\D", "", cleaned)
    if 10 <= len(digits) <= 15:
        return digits
    return None


def _hash_otp(*, otp: str, channel: str, target: str, secret_key: str) -> str:
    material = f"{otp}|{channel}|{target}|{secret_key}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _store_otp(*, channel: str, target: str, otp: str, secret_key: str) -> None:
    now = time.time()
    session["otp_channel"] = channel
    session["otp_target"] = target
    session["otp_hash"] = _hash_otp(otp=otp, channel=channel, target=target, secret_key=secret_key)
    session["otp_expires_at"] = now + OTP_TTL_SECONDS
    session["otp_resend_at"] = now + RESEND_COOLDOWN_SECONDS
    session["otp_last_sent_at"] = now
    session["otp_attempts"] = 0


def _clear_otp() -> None:
    for key in (
        "otp_channel",
        "otp_target",
        "otp_hash",
        "otp_expires_at",
        "otp_resend_at",
        "otp_last_sent_at",
        "otp_attempts",
    ):
        session.pop(key, None)


def _send_guard() -> str | None:
    last_sent_at = float(session.get("otp_last_sent_at", 0))
    now = time.time()
    if now - last_sent_at < SEND_MIN_INTERVAL_SECONDS:
        return "Please wait a few seconds before requesting another OTP."
    return None


def _send_otp_via_gmail_smtp(*, to_email: str, otp: str, ttl_seconds: int) -> tuple[bool, str]:
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    from_email = os.environ.get("SMTP_FROM", gmail_user or "")

    missing = []
    if not gmail_user:
        missing.append("GMAIL_USER")
    if not gmail_app_password:
        missing.append("GMAIL_APP_PASSWORD")
    if not from_email:
        missing.append("SMTP_FROM")
    if missing:
        return False, f"Missing email configuration: {', '.join(missing)}."

    msg = EmailMessage()
    msg["Subject"] = "Your ANN-D Health Advisor OTP"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(
        "\n".join(
            [
                "ANN-D Health Advisor",
                "",
                f"Your OTP is: {otp}",
                f"This OTP expires in {ttl_seconds} seconds.",
                "",
                "If you did not request this, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.send_message(msg)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check Gmail app password and account security settings."
    except smtplib.SMTPException as exc:
        return False, f"SMTP error: {exc}"
    except TimeoutError:
        return False, "SMTP connection timed out. Check internet/firewall and try again."
    except Exception as exc:
        return False, f"Email send failed: {exc}"


def _send_otp_via_twilio_or_mock(*, mobile: str, otp: str, ttl_seconds: int) -> bool:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")

    if not (account_sid and auth_token and from_number):
        return False

    try:
        from twilio.rest import Client  # type: ignore

        client = Client(account_sid, auth_token)
        client.messages.create(
            body=f"ANN-D Health Advisor OTP: {otp} (expires in {ttl_seconds}s)",
            from_=from_number,
            to=mobile,
        )
        return True
    except Exception:
        return False


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
