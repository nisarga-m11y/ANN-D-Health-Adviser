import { useEffect, useMemo, useState } from "react";

import { registerUser } from "../api/auth";
import { sendEmailOtp, verifyEmailOtp } from "../api/otpAuth";
import "../styles/register.css";

function formatCountdown(seconds) {
  const clamped = Math.max(0, Number(seconds) || 0);
  const mm = String(Math.floor(clamped / 60)).padStart(2, "0");
  const ss = String(clamped % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function EyeIcon({ open }) {
  if (open) {
    return (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" stroke="currentColor" strokeWidth="1.7" />
        <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.7" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m3 3 18 18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M10.7 6.2A9.5 9.5 0 0 1 12 6c5.5 0 9 6 9 6a17.5 17.5 0 0 1-3.2 3.8" stroke="currentColor" strokeWidth="1.7" />
      <path d="M6.2 10.7A17.6 17.6 0 0 0 3 12s3.5 6 9 6c.4 0 .9 0 1.3-.1" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

function RuleItem({ ok, text }) {
  return (
    <li className="reg-rule" data-ok={ok ? "true" : "false"}>
      <span className="reg-rule-dot" aria-hidden="true" />
      <span>{text}</span>
    </li>
  );
}

function RegisterPage() {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [verifyingOtp, setVerifyingOtp] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const id = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [secondsLeft]);

  const rules = useMemo(
    () => ({
      minLength: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      number: /\d/.test(password),
      special: /[^A-Za-z0-9]/.test(password),
    }),
    [password],
  );

  const passwordScore = useMemo(() => {
    let score = 0;
    if (rules.minLength) score += 1;
    if (rules.uppercase) score += 1;
    if (rules.number) score += 1;
    if (rules.special) score += 1;
    return score;
  }, [rules]);

  const passwordStrength = useMemo(() => {
    if (passwordScore <= 1) return "Weak";
    if (passwordScore <= 3) return "Medium";
    return "Strong";
  }, [passwordScore]);

  const passwordValid = rules.minLength && rules.uppercase && rules.number && rules.special;
  const passwordsMatch = confirmPassword.length > 0 && password === confirmPassword;
  const showMismatch = submitted && confirmPassword.length > 0 && !passwordsMatch;
  const canResend = otpSent && secondsLeft === 0 && !sendingOtp && !verifyingOtp;
  const canCreate = otpVerified && passwordValid && passwordsMatch && !creating;
  const normalizedEmail = email.trim().toLowerCase();

  async function handleSendOtp() {
    setMessage(null);
    setSendingOtp(true);
    try {
      const data = await sendEmailOtp(normalizedEmail);
      setOtpSent(true);
      setOtp("");
      setSecondsLeft(Number(data?.expires_in) || 60);
      setMessage({ type: "success", text: "OTP sent successfully." });
    } catch (err) {
      const retryAfter = err?.response?.data?.retry_after;
      const detail = err?.response?.data?.detail || "Failed to send OTP.";
      if (typeof retryAfter === "number") {
        setOtpSent(true);
        setSecondsLeft(Math.max(0, Math.floor(retryAfter)));
      }
      setMessage({ type: "error", text: detail });
    } finally {
      setSendingOtp(false);
    }
  }

  async function handleVerifyOtp() {
    setMessage(null);
    setVerifyingOtp(true);
    try {
      await verifyEmailOtp(normalizedEmail, otp);
      setOtpVerified(true);
      setMessage({ type: "success", text: "Email verified successfully." });
    } catch (err) {
      const detail = err?.response?.data?.detail || "OTP verification failed.";
      setMessage({ type: "error", text: detail });
    } finally {
      setVerifyingOtp(false);
    }
  }

  async function handleCreateAccount(event) {
    event.preventDefault();
    setSubmitted(true);
    if (!canCreate) return;

    setMessage(null);
    setCreating(true);
    try {
      const nameGuess = normalizedEmail.split("@", 1)[0]?.replace(/[._-]+/g, " ").trim() || "User";
      await registerUser({
        name: nameGuess,
        email: normalizedEmail,
        password,
      });
      setMessage({ type: "success", text: "Registration complete. Redirecting to login..." });
      setTimeout(() => {
        window.location.href = "/login";
      }, 600);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const emailError = err?.response?.data?.email?.[0];
      const alreadyExists =
        (typeof detail === "string" && detail.toLowerCase().includes("already exists")) ||
        (typeof emailError === "string" && emailError.toLowerCase().includes("already exists"));

      if (alreadyExists) {
        setMessage({
          type: "error",
          text: "An account with this email already exists. Please log in instead.",
        });
      } else if (typeof detail === "string" && detail.trim()) {
        setMessage({ type: "error", text: detail });
      } else if (emailError) {
        setMessage({ type: "error", text: String(emailError) });
      } else {
        setMessage({ type: "error", text: "Could not create account. Please try again." });
      }
    } finally {
      setCreating(false);
    }
  }

  const step = otpVerified ? 2 : otpSent ? 1 : 1;
  const stepThreeComplete = Boolean(message?.type === "success" && message?.text?.includes("Registration complete"));

  return (
    <main className="container auth-page">
      <form className="auth-card reg-card" onSubmit={handleCreateAccount}>
        <h2 className="reg-title">Create Your Account</h2>
        <p className="reg-subtitle">Secure registration with email OTP verification</p>

        <div className="reg-steps" aria-label="Registration steps">
          <div className="reg-step" data-active={step >= 1 ? "true" : "false"}>
            <div className="reg-step-index">1</div>
            <div className="reg-step-text">Step 1: Verify Email</div>
          </div>
          <div className="reg-step" data-active={step >= 2 ? "true" : "false"}>
            <div className="reg-step-index">2</div>
            <div className="reg-step-text">Step 2: Create Password</div>
          </div>
          <div className="reg-step" data-active={stepThreeComplete ? "true" : "false"}>
            <div className="reg-step-index">3</div>
            <div className="reg-step-text">Step 3: Complete Registration</div>
          </div>
        </div>

        <label htmlFor="reg-email">Email</label>
        <input
          id="reg-email"
          type="email"
          placeholder="name@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={sendingOtp || verifyingOtp || otpVerified}
          required
        />

        <div className="reg-inline-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleSendOtp}
            disabled={!email.trim() || sendingOtp || verifyingOtp || otpVerified}
          >
            {sendingOtp ? "Sending OTP..." : "Send OTP"}
          </button>
          {otpSent && (
            <span className="reg-timer">
              {secondsLeft > 0 ? `OTP expires in ${formatCountdown(secondsLeft)}` : "OTP expired"}
            </span>
          )}
        </div>

        {otpSent && (
          <>
            <label htmlFor="reg-otp">OTP</label>
            <input
              id="reg-otp"
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D+/g, ""))}
              disabled={verifyingOtp || otpVerified}
            />

            <div className="reg-inline-actions">
              <button
                type="button"
                className="btn-primary"
                onClick={handleVerifyOtp}
                disabled={otp.length !== 6 || verifyingOtp || otpVerified}
              >
                {verifyingOtp ? "Verifying..." : "Verify OTP"}
              </button>
              <button type="button" className="btn-outline" onClick={handleSendOtp} disabled={!canResend || otpVerified}>
                Resend OTP
              </button>
            </div>
          </>
        )}

        <section className="reg-password-section" data-open={otpVerified ? "true" : "false"}>
          <label htmlFor="reg-password">Password</label>
          <div className="reg-password-wrap">
            <input
              id="reg-password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a strong password"
              disabled={!otpVerified || creating}
            />
            <button
              type="button"
              className="reg-eye-btn"
              aria-label={showPassword ? "Hide password" : "Show password"}
              onClick={() => setShowPassword((v) => !v)}
              disabled={!otpVerified}
            >
              <EyeIcon open={showPassword} />
            </button>
          </div>

          <ul className="reg-rules">
            <RuleItem ok={rules.minLength} text="Minimum 8 characters" />
            <RuleItem ok={rules.uppercase} text="At least 1 uppercase letter" />
            <RuleItem ok={rules.number} text="At least 1 number" />
            <RuleItem ok={rules.special} text="At least 1 special character" />
          </ul>

          <div className="reg-strength">
            <div className="reg-strength-track">
              <div className="reg-strength-fill" data-level={passwordStrength.toLowerCase()} style={{ width: `${(passwordScore / 4) * 100}%` }} />
            </div>
            <div className="reg-strength-label">Strength: {passwordStrength}</div>
          </div>

          <label htmlFor="reg-confirm-password">Confirm Password</label>
          <div className="reg-password-wrap">
            <input
              id="reg-confirm-password"
              type={showConfirmPassword ? "text" : "password"}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
              disabled={!otpVerified || creating}
            />
            <button
              type="button"
              className="reg-eye-btn"
              aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
              onClick={() => setShowConfirmPassword((v) => !v)}
              disabled={!otpVerified}
            >
              <EyeIcon open={showConfirmPassword} />
            </button>
          </div>
          {showMismatch && <p className="reg-inline-error">Passwords do not match.</p>}
        </section>

        {message && (
          <div className="otp-auth-message" data-type={message.type}>
            {message.text}
          </div>
        )}

        <button type="submit" className="btn-primary reg-submit" disabled={!canCreate}>
          {creating ? "Creating Account..." : "Create Account"}
        </button>
      </form>
    </main>
  );
}

export default RegisterPage;
