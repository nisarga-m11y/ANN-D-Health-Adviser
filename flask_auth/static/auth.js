const state = {
  tab: "email",
  otpSent: false,
  ttlSeconds: 60,
  resendSeconds: 60,
  ttlTimer: null,
  resendTimer: null,
  busy: false,
};

const els = {
  msg: document.getElementById("msg"),
  form: document.getElementById("form"),
  tabs: Array.from(document.querySelectorAll(".tab")),
  emailFields: document.getElementById("emailFields"),
  mobileFields: document.getElementById("mobileFields"),
  otpFields: document.getElementById("otpFields"),
  email: document.getElementById("email"),
  mobile: document.getElementById("mobile"),
  otp: document.getElementById("otp"),
  sendBtn: document.getElementById("sendBtn"),
  sendText: document.getElementById("sendText"),
  verifyBtn: document.getElementById("verifyBtn"),
  resendBtn: document.getElementById("resendBtn"),
  ttl: document.getElementById("ttl"),
};

function setMsg(text, kind = "info") {
  els.msg.textContent = text || "";
  els.msg.className = "msg " + kind;
}

function setBusy(isBusy, sendingText = "Sending OTP...") {
  state.busy = isBusy;
  els.sendBtn.disabled = isBusy;
  els.verifyBtn.disabled = isBusy || !state.otpSent;
  els.resendBtn.disabled = isBusy || (state.otpSent && state.resendSeconds > 0);
  els.sendText.textContent = isBusy ? sendingText : "Send OTP";
}

function stopTimers() {
  if (state.ttlTimer) clearInterval(state.ttlTimer);
  if (state.resendTimer) clearInterval(state.resendTimer);
  state.ttlTimer = null;
  state.resendTimer = null;
}

function resetOtpUI() {
  stopTimers();
  state.otpSent = false;
  state.ttlSeconds = 60;
  state.resendSeconds = 60;
  els.otpFields.classList.add("hidden");
  els.verifyBtn.disabled = true;
  els.resendBtn.disabled = true;
  els.ttl.textContent = "60";
  els.otp.value = "";
}

function startTimers() {
  stopTimers();

  els.otpFields.classList.remove("hidden");
  state.otpSent = true;
  els.verifyBtn.disabled = false;
  els.resendBtn.disabled = true;

  els.ttl.textContent = String(state.ttlSeconds);

  state.ttlTimer = setInterval(() => {
    state.ttlSeconds -= 1;
    els.ttl.textContent = String(Math.max(0, state.ttlSeconds));
    if (state.ttlSeconds <= 0) {
      clearInterval(state.ttlTimer);
      state.ttlTimer = null;
      setMsg("OTP expired. Please resend OTP.", "err");
      els.verifyBtn.disabled = true;
    }
  }, 1000);

  state.resendTimer = setInterval(() => {
    state.resendSeconds -= 1;
    if (state.resendSeconds <= 0) {
      clearInterval(state.resendTimer);
      state.resendTimer = null;
      els.resendBtn.disabled = false;
    }
  }, 1000);
}

function switchTab(tab) {
  if (tab !== "email" && tab !== "mobile") return;
  state.tab = tab;
  els.tabs.forEach((btn) => {
    const active = btn.dataset.tab === tab;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });

  els.emailFields.classList.toggle("hidden", tab !== "email");
  els.mobileFields.classList.toggle("hidden", tab !== "mobile");
  resetOtpUI();
  setMsg("");
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || "Request failed.");
  }
  return data;
}

function getTarget() {
  if (state.tab === "email") {
    return { channel: "email", value: (els.email.value || "").trim() };
  }
  return { channel: "mobile", value: (els.mobile.value || "").trim() };
}

async function sendOtp() {
  const t = getTarget();
  if (!t.value) {
    setMsg(state.tab === "email" ? "Please enter your email." : "Please enter your mobile number.", "err");
    return;
  }

  resetOtpUI();
  setBusy(true, "Sending OTP...");
  setMsg("Sending OTP...", "info");

  try {
    const data =
      t.channel === "email"
        ? await apiPost("/api/otp/email/send", { email: t.value })
        : await apiPost("/api/otp/mobile/send", { mobile: t.value });

    state.ttlSeconds = Number(data.expires_in || 60);
    state.resendSeconds = Number(data.resend_in || 60);
    startTimers();
    setMsg(data.message || "OTP sent.", "ok");
    els.otp.focus();
  } catch (e) {
    setMsg(e.message || "Failed to send OTP.", "err");
  } finally {
    setBusy(false);
  }
}

async function verifyOtp() {
  if (!state.otpSent) return;
  const otp = (els.otp.value || "").trim();
  if (!/^\d{6}$/.test(otp)) {
    setMsg("Enter the 6-digit OTP.", "err");
    return;
  }

  setBusy(true, "Verifying...");
  setMsg("Verifying OTP...", "info");
  try {
    const data = await apiPost("/api/otp/verify", { channel: state.tab, otp });
    setMsg(data.message || "Login successful.", "ok");
    stopTimers();
    setTimeout(() => {
      window.location.href = data.redirect_url || "/chatbot/";
    }, 450);
  } catch (e) {
    setMsg(e.message || "Invalid OTP.", "err");
  } finally {
    setBusy(false, "Sending OTP...");
  }
}

els.tabs.forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));
els.sendBtn.addEventListener("click", sendOtp);
els.verifyBtn.addEventListener("click", verifyOtp);
els.resendBtn.addEventListener("click", sendOtp);

els.otp.addEventListener("input", () => {
  const value = (els.otp.value || "").replace(/\D/g, "").slice(0, 6);
  els.otp.value = value;
});

els.form.addEventListener("submit", (e) => e.preventDefault());
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    if (!state.otpSent) sendOtp();
    else verifyOtp();
  }
});

switchTab("email");

