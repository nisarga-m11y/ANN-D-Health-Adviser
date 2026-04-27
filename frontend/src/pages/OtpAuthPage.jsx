import { useEffect, useMemo, useState } from "react";

import {
  sendEmailOtp,
  verifyEmailOtp,
} from "../api/otpAuth";
import "../styles/otp-auth.css";

function IconEmail() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 6.75C4 5.784 4.784 5 5.75 5h12.5C19.216 5 20 5.784 20 6.75v10.5c0 .966-.784 1.75-1.75 1.75H5.75C4.784 19 4 18.216 4 17.25V6.75Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M5.5 7.25 12 12l6.5-4.75"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconLock() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7.5 10.5V8.25A4.5 4.5 0 0 1 12 3.75a4.5 4.5 0 0 1 4.5 4.5v2.25"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M6.75 10.5h10.5c.966 0 1.75.784 1.75 1.75v5c0 .966-.784 1.75-1.75 1.75H6.75A1.75 1.75 0 0 1 5 17.25v-5c0-.966.784-1.75 1.75-1.75Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M12 14.25v2"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function formatCountdown(seconds) {
  const clamped = Math.max(0, Number(seconds) || 0);
  const mm = String(Math.floor(clamped / 60)).padStart(2, "0");
  const ss = String(clamped % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function OtpAuthPage() {
  const [identifier, setIdentifier] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [message, setMessage] = useState(null); // { type, text }

  const canResend = otpSent && secondsLeft === 0 && !sending;

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const id = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [secondsLeft]);

  const title = useMemo(() => "Email OTP Login / Register", []);

  async function handleSendOtp() {
    setMessage(null);
    setSending(true);
    try {
      const data = await sendEmailOtp(identifier);
      const expires = Number(data?.expires_in) || 60;
      setOtpSent(true);
      setOtp("");
      setSecondsLeft(expires);
      const debugOtp = String(data?.debug_otp || "").trim();
      setMessage({
        type: "success",
        text: debugOtp
          ? `OTP sent successfully. Debug OTP: ${debugOtp}`
          : "OTP sent successfully.",
      });
    } catch (err) {
      const retryAfter = err?.response?.data?.retry_after;
      const detail = err?.response?.data?.detail || "Failed to send OTP.";
      if (typeof retryAfter === "number") {
        setSecondsLeft(Math.max(0, Math.floor(retryAfter)));
        setOtpSent(true);
      }
      setMessage({ type: "error", text: detail });
    } finally {
      setSending(false);
    }
  }

  async function handleVerifyOtp() {
    setMessage(null);
    setLoading(true);
    try {
      const data = await verifyEmailOtp(identifier, otp);
      localStorage.setItem("auth_token", data.token);
      if (data?.user?.name) {
        localStorage.setItem("auth_user_name", String(data.user.name));
      }
      if (data?.user?.email) {
        localStorage.setItem("auth_user_email", String(data.user.email));
      }
      localStorage.setItem("auth_login_email", String(identifier || "").trim().toLowerCase());
      setMessage({ type: "success", text: "Login successful. Redirecting..." });
      window.location.href = "/dashboard";
    } catch (err) {
      const detail = err?.response?.data?.detail || "OTP verification failed.";
      setMessage({ type: "error", text: detail });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container auth-page">
      <div className="auth-card otp-auth-card">
        <h2 className="otp-auth-title">ANN-D Health Advisor</h2>
        <p className="otp-auth-subtitle">{title}</p>

        <label htmlFor="identifier">Email</label>
        <div className="otp-auth-field">
          <div className="otp-auth-icon">
            <IconEmail />
          </div>
          <input
            id="identifier"
            name="identifier"
            type="email"
            placeholder="name@example.com"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            disabled={sending || loading}
            required
          />
        </div>

        {otpSent ? (
          <>
            <label htmlFor="otp">OTP</label>
            <div className="otp-auth-field">
              <div className="otp-auth-icon">
                <IconLock />
              </div>
              <input
                id="otp"
                name="otp"
                inputMode="numeric"
                placeholder="6-digit OTP"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                disabled={loading || sending}
              />
            </div>

            <div className="otp-auth-meta">
              <span>{secondsLeft > 0 ? `Expires in ${formatCountdown(secondsLeft)}` : "OTP expired"}</span>
              <button type="button" className="btn-outline" onClick={handleSendOtp} disabled={!canResend}>
                Resend OTP
              </button>
            </div>
          </>
        ) : null}

        {message ? (
          <div className="otp-auth-message" data-type={message.type}>
            {message.text}
          </div>
        ) : null}

        <div className="otp-auth-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleSendOtp}
            disabled={sending || loading || !identifier.trim()}
          >
            {sending ? "Sending OTP..." : "Send OTP"}
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={handleVerifyOtp}
            disabled={!otpSent || loading || sending || otp.trim().length !== 6}
          >
            {loading ? "Verifying..." : "Verify OTP"}
          </button>
        </div>
      </div>
    </main>
  );
}

export default OtpAuthPage;
