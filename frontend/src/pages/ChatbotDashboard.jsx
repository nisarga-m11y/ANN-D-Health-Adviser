import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { createPortal } from "react-dom";

import {
  fetchCallConfig,
  fetchChatHistory,
  requestHelpCall,
  sendAutoImageMessage,
  sendChatMessage,
  sendPrescriptionMessage,
  sendSeverity,
  sendVoiceMessage,
  translateToEnglish,
  fetchTtsAudio,
} from "../api/chat";
import { useAuth } from "../context/AuthContext";


const DEV_ASSET_BUST = import.meta.env.DEV ? String(Date.now()) : "";

function getAvatarUrl(kind) {
  const baseUrl = import.meta.env.BASE_URL || "/";
  const base = baseUrl.endsWith("/") ? baseUrl : baseUrl + "/";
  const file = kind === "bot" ? "avatars/bot.png" : "avatars/user.png";
  const url = base + file;
  return DEV_ASSET_BUST ? `${url}?v=${DEV_ASSET_BUST}` : url;
}

function MessageAvatar({ role }) {
  const kind = role === "bot" ? "bot" : "user";
  const alt = role === "bot" ? "Bot" : "User";
  return <img className="chat-avatar" src={getAvatarUrl(kind)} alt={alt} />;
}

function QuickPromptIcon({ kind }) {
  if (kind === "remedy") {
    return (
      <svg className="quick-prompt-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M19 5c-7 0-12 5-12 12 7 0 12-5 12-12Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M8 15c2.5-2.8 5.2-4.8 8-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    );
  }

  if (kind === "doctor") {
    return (
      <svg className="quick-prompt-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="9" cy="9" r="3" stroke="currentColor" strokeWidth="1.7" />
        <path d="M4.5 17c.7-2.2 2.5-3.4 4.5-3.4 2 0 3.8 1.2 4.5 3.4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        <circle cx="17" cy="10" r="2.2" stroke="currentColor" strokeWidth="1.6" />
        <path d="M14.5 17c.5-1.6 1.8-2.5 3.3-2.5s2.8.9 3.2 2.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg className="quick-prompt-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 11.5h16" stroke="currentColor" strokeWidth="1.7" />
      <path d="M7 11.5v6.5M12 11.5v6.5M17 11.5v6.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M5.5 11.5V8.8a1.8 1.8 0 0 1 1.8-1.8h9.4a1.8 1.8 0 0 1 1.8 1.8v2.7" stroke="currentColor" strokeWidth="1.7" />
      <path d="M9.5 7V5.7a2.5 2.5 0 0 1 5 0V7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function getTabletImageCandidates(imageKey) {
  const key = String(imageKey || "generic").trim() || "generic";
  const baseUrl = import.meta.env.BASE_URL || "/";
  const base = baseUrl.endsWith("/") ? baseUrl : baseUrl + "/";

  const urls = [
    `${base}meds/${key}.jpeg`,
    `${base}meds/${key}.jpg`,
    `${base}meds/${key}.png`,
    `${base}meds/${key}.svg`,
    `${base}meds/generic.svg`,
  ];

  if (!DEV_ASSET_BUST) return urls;
  return urls.map((url) => `${url}?v=${DEV_ASSET_BUST}`);
}

function getTabletImageUrl(imageKey) {
  return getTabletImageCandidates(imageKey)[0];
}

function handleTabletImageError(event, imageKey) {
  const urls = getTabletImageCandidates(imageKey);
  const img = event.currentTarget;
  const currentIndex = Number(img.dataset.fallbackIndex || "0");
  const nextIndex = currentIndex + 1;

  if (nextIndex >= urls.length) {
    img.onerror = null;
    return;
  }

  img.dataset.fallbackIndex = String(nextIndex);
  img.src = urls[nextIndex];
}


function TabletSuggestions({ suggestions, onSelect }) {
  if (!Array.isArray(suggestions) || suggestions.length === 0) return null;

  return (
    <div className="tablet-suggestions">
      {suggestions.map((item, idx) => (
        <div key={String(item?.name || idx) + "-" + String(idx)} className="tablet-card">
          <img key={String(item?.image_key || item?.name || idx) + ":" + DEV_ASSET_BUST} className="tablet-image" data-fallback-index="0" src={getTabletImageUrl(item?.image_key)} alt={item?.name || "Tablet"} onClick={() => onSelect && onSelect(item)} style={{ cursor: "pointer" }} onLoad={(event) => { event.currentTarget.dataset.fallbackIndex = "0"; }} onError={(event) => handleTabletImageError(event, item?.image_key)} />
          <div className="tablet-meta">
            <div className="tablet-name">{item?.name || "Medicine"}</div>
            <div className="tablet-use">{item?.use || ""}</div>
            <div className="tablet-disclaimer">{item?.disclaimer || "For reference only. Consult doctor before use."}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
function hasKannadaChars(text) {
  return /[\u0C80-\u0CFF]/.test(text || "");
}

function renderMessageContent(message) {
  const content = String(message?.content || "").replaceAll("***", "");

  if (message?.role !== "bot") {
    return <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>;
  }

  const normalized = content.replaceAll("\\\\n", "\n");
  const lines = normalized.split("\n");

  return (
    <div style={{ whiteSpace: "pre-wrap" }}>
      {lines.map((line, idx) => {
        const trimmed = line.trimStart();
        if (trimmed.trim().toLowerCase() === "medicine image result") {
          return (
            <div key={idx}>
              <span className="highlight-title">{trimmed.trim()}</span>
            </div>
          );
        }
        const match = trimmed.match(/^([^:]{1,120})\s*:\s*(.*)$/);

        if (match) {
          const labelRaw = (match[1] || "").trim();
          const value = (match[2] || "").trim();
          const labelLower = labelRaw.toLowerCase();
          const kannadaLikeHeading = hasKannadaChars(labelRaw) && labelRaw.length <= 48;
          const shouldHighlight =
  kannadaLikeHeading ||
  labelLower === "condition" ||
  labelLower === "tablets" ||
  labelLower === "tablet" ||
  labelLower === "name" ||
  labelLower === "uses" ||
  labelLower === "food timing" ||
  labelLower === "safety" ||
  labelLower === "natural medicine" ||
  labelLower === "home remedies" ||
  labelLower === "advice" ||
  labelLower === "if symptoms worsen" ||
  labelLower === "if each symptom worsens (possible progression)" ||
  labelLower === "best places to go" ||
  labelLower === "best place to go";

          if (shouldHighlight) {
            const isHeaderOnly =
              labelLower === "if each symptom worsens (possible progression)" ||
              labelLower === "best places to go" ||
              labelLower === "???????? ?????????" ||
              labelLower === "????? ????? ????????? (??????? ??????)" ||
              labelLower === "????? ????????? ???????";
            const displayValue = isHeaderOnly ? "" : (value || "-");

            return (
              <div key={idx}>
                <span className="highlight-label">{labelRaw}</span>{displayValue ? `: ${displayValue}` : ":"}
              </div>
            );
          }
        }

        return <div key={idx}>{line}</div>;
      })}
    </div>
  );
}

function getApiErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }

  const message = error?.message;
  if (typeof message === "string" && message.trim()) {
    return message.trim();
  }

  return fallback;
}
function ChatbotDashboard() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lang, setLang] = useState("en");
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [ttsSupported, setTtsSupported] = useState(false);
  const [ttsVoicesLoaded, setTtsVoicesLoaded] = useState(false);
  const [hasKannadaVoice, setHasKannadaVoice] = useState(false);
  const [hasEnglishVoice, setHasEnglishVoice] = useState(true);
  const [listening, setListening] = useState(false);
  const [attachedImage, setAttachedImage] = useState(null);
  const [attachedPreviewUrl, setAttachedPreviewUrl] = useState("");
  const [attachedPrescription, setAttachedPrescription] = useState(null);
  const [prescriptionPreviewUrl, setPrescriptionPreviewUrl] = useState("");
  const [attachedAudio, setAttachedAudio] = useState(null);
  const [callConfig, setCallConfig] = useState({ call_enabled: false, phone_number: "", callback_enabled: false, provider: "" });
const [showEmergencyModal, setShowEmergencyModal] = useState(false);
  const [callRequestLoading, setCallRequestLoading] = useState(false);
  const [severityLoadingChatId, setSeverityLoadingChatId] = useState(null);
  const [selectedTablet, setSelectedTablet] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [readNotificationIds, setReadNotificationIds] = useState([]);
  const [notifyPanelStyle, setNotifyPanelStyle] = useState({});
  const recognitionRef = useRef(null);
  const audioRef = useRef(null);
  const audioUrlRef = useRef("");
  const audioContextRef = useRef(null);
  const audioSourceRef = useRef(null);
  const audioUnlockedRef = useRef(false);
  const kannadaVoiceNoticeLoggedRef = useRef(false);
  const imageInputRef = useRef(null);
  const prescriptionInputRef = useRef(null);
  const audioInputRef = useRef(null);
  const textInputRef = useRef(null);
  const messagesRef = useRef(null);
  const notificationsRef = useRef(null);
  const notifyButtonRef = useRef(null);
  const notifyPanelRef = useRef(null);

  const quickPrompts = useMemo(
    () => [
      { label: "Home Remedies", prompt: "Suggest home remedies for my symptoms.", icon: "remedy" },
      { label: "When to see a doctor?", prompt: "When should I see a doctor for these symptoms?", icon: "doctor" },
      { label: "Nearby hospitals", prompt: "Show nearby hospitals or clinics for this condition.", icon: "hospital" },
    ],
    [],
  );

  const latestBotMessageWithSpeech = useMemo(
    () => [...messages].reverse().find((message) => message.role === "bot" && message.speechText),
    [messages],
  );
  const hasAttachment = Boolean(attachedImage || attachedPrescription || attachedAudio);
  const canSubmit = Boolean(input.trim()) || hasAttachment;
  const activeAttachment = useMemo(() => {
    if (attachedAudio) {
      return { type: "Voice note", name: attachedAudio.name || "Audio file" };
    }
    if (attachedPrescription) {
      return { type: "Prescription image", name: attachedPrescription.name || "Prescription" };
    }
    if (attachedImage) {
      return { type: "Image", name: attachedImage.name || "Attached image" };
    }
    return null;
  }, [attachedAudio, attachedImage, attachedPrescription]);
  const notifications = useMemo(() => {
    const list = [];
    if (callConfig?.call_enabled) {
      list.push({
        id: "emergency-call",
        title: "Emergency call is enabled",
        detail: "Quick dial is ready from the Emergency Call button.",
      });
    }
    if (callConfig?.callback_enabled) {
      list.push({
        id: "callback-enabled",
        title: "Call back is available",
        detail: "You can request a call from support/helpline.",
      });
    }
    if (latestBotMessageWithSpeech) {
      list.push({
        id: "latest-reply",
        title: "New assistant reply",
        detail: "Tap Speak Reply to hear the latest message.",
      });
    }
    list.push({
      id: "lang-mode",
      title: "Language mode: " + (lang === "kn" ? "Kannada" : "English"),
      detail: "Switch anytime from the top toolbar.",
    });
    return list;
  }, [callConfig, latestBotMessageWithSpeech, lang]);
  const unreadCount = useMemo(
    () => notifications.filter((item) => !readNotificationIds.includes(item.id)).length,
    [notifications, readNotificationIds],
  );

  const displayName = useMemo(() => {
    const fromName = String(user?.name || "").trim();
    const fromEmail = String(user?.email || "").trim();
    const storedName = String(localStorage.getItem("auth_user_name") || "").trim();
    const storedEmail = String(localStorage.getItem("auth_user_email") || localStorage.getItem("auth_login_email") || "").trim();
    const emailPrefix = fromEmail && fromEmail.includes("@") ? fromEmail.split("@", 1)[0] : "";
    const storedEmailPrefix = storedEmail && storedEmail.includes("@") ? storedEmail.split("@", 1)[0] : "";
    const genericNames = new Set(["user", "guest", "unknown"]);

    if (fromName && !genericNames.has(fromName.toLowerCase())) return fromName;
    if (storedName && !genericNames.has(storedName.toLowerCase())) return storedName;

    const fromUsername = String(user?.username || "").trim();
    if (fromUsername) return fromUsername;

    if (emailPrefix) return emailPrefix;
    if (storedEmailPrefix) return storedEmailPrefix;

    if (fromName) return fromName;
    if (storedName) return storedName;

    if (fromEmail && fromEmail.includes("@")) {
      return fromEmail.split("@", 1)[0];
    }
    if (storedEmail && storedEmail.includes("@")) {
      return storedEmail.split("@", 1)[0];
    }

    return "User";
  }, [user]);

  const userInitial = useMemo(() => {
    const first = String(displayName || "").trim().charAt(0);
    return first ? first.toUpperCase() : "U";
  }, [displayName]);
useEffect(() => {
    async function loadHistory() {
      try {
        const [history, callInfo] = await Promise.all([fetchChatHistory(), fetchCallConfig()]);
        const normalized = history
          .slice()
          .reverse()
          .flatMap((item) => [
            {
              role: "user",
              content: item.message,
              timestamp: item.timestamp,
              chatId: item.id,
              imageUrl: item.image_url,
            },
            { role: "bot", content: item.response, timestamp: item.timestamp, chatId: item.id },
          ]);
        setMessages(normalized);
        setCallConfig(callInfo);
      } catch {
        setError("Could not load dashboard data.");
      }
    }

    loadHistory();
  }, []);

  useEffect(() => {
    return () => {
      if (attachedPreviewUrl) {
        URL.revokeObjectURL(attachedPreviewUrl);
      }
      if (prescriptionPreviewUrl) {
        URL.revokeObjectURL(prescriptionPreviewUrl);
      }
    };
  }, [attachedPreviewUrl, prescriptionPreviewUrl]);

  useEffect(() => {
    const box = messagesRef.current;
    if (!box) return;
    box.scrollTop = box.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (!showNotifications) return;

    function handleOutsideClick(event) {
      const insideBellWrap = notificationsRef.current && notificationsRef.current.contains(event.target);
      const insidePanel = notifyPanelRef.current && notifyPanelRef.current.contains(event.target);
      if (!insideBellWrap && !insidePanel) {
        setShowNotifications(false);
      }
    }

    function handleEsc(event) {
      if (event.key === "Escape") {
        setShowNotifications(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [showNotifications]);

  useEffect(() => {
    if (!showNotifications) return;

    function updateNotifyPosition() {
      const btn = notifyButtonRef.current;
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const panelWidth = Math.min(360, Math.max(280, window.innerWidth - 24));
      const left = Math.max(12, Math.min(window.innerWidth - panelWidth - 12, rect.right - panelWidth));
      const top = Math.max(12, rect.bottom + 8);
      setNotifyPanelStyle({ position: "fixed", left, top, width: panelWidth });
    }

    updateNotifyPosition();
    window.addEventListener("resize", updateNotifyPosition);
    window.addEventListener("scroll", updateNotifyPosition, true);
    return () => {
      window.removeEventListener("resize", updateNotifyPosition);
      window.removeEventListener("scroll", updateNotifyPosition, true);
    };
  }, [showNotifications]);

  useEffect(() => {
    const synth = window.speechSynthesis;
    if (!synth) {
      setTtsSupported(false);
      setTtsVoicesLoaded(false);
      setHasKannadaVoice(false);
      return;
    }

    setTtsSupported(true);

    function refreshVoices() {
      const voices = synth.getVoices() || [];
      setTtsVoicesLoaded(true);
      setHasKannadaVoice(voices.some((voice) => (voice.lang || "").toLowerCase().startsWith("kn")));
    }

    refreshVoices();
    synth.onvoiceschanged = refreshVoices;

    return () => {
      if (synth.onvoiceschanged === refreshVoices) {
        synth.onvoiceschanged = null;
      }
    };
  }, []);

  useEffect(() => {
    if (kannadaVoiceNoticeLoggedRef.current) {
      return;
    }

    if (lang === "kn" && ttsSupported && ttsVoicesLoaded && !hasKannadaVoice) {
      console.info(
        "Browser Kannada voice not installed. Kannada will play using server voice (backend running + internet). If audio is blocked, click Speak (Kannada) once.",
      );
      kannadaVoiceNoticeLoggedRef.current = true;
    }
  }, [lang, ttsSupported, ttsVoicesLoaded, hasKannadaVoice]);
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "kn-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      setError("Voice input failed. Please try again.");
    };
    recognition.onresult = (event) => {
      const transcript = event?.results?.[0]?.[0]?.transcript || "";
      const trimmed = transcript.trim();
      if (!trimmed) {
        return;
      }

      setError("");
      setInput((prev) => (prev + " " + trimmed).trim());
    };

    recognitionRef.current = recognition;
    setSpeechSupported(true);

    return () => {
      recognition.stop();
    };
  }, []);
  function getAudioContext() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;

    if (!audioContextRef.current) {
      audioContextRef.current = new AudioCtx();
    }

    return audioContextRef.current;
  }

  async function unlockAudio() {
    const ctx = getAudioContext();
    if (!ctx) return false;

    // Mark as unlocked when called from a user gesture.
    audioUnlockedRef.current = true;

    try {
      if (ctx.state === "suspended") {
        void ctx.resume();
      }
    } catch {
      // ignore
    }

    return true;
  }

  async function playMp3WithWebAudio(blob) {
    const ctx = getAudioContext();
    if (!ctx) return false;

    try {
      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      const arrayBuffer = await blob.arrayBuffer();
      const decoded = await new Promise((resolve, reject) => {
        ctx.decodeAudioData(arrayBuffer.slice(0), resolve, reject);
      });

      if (audioSourceRef.current) {
        try {
          audioSourceRef.current.stop();
        } catch {
          // ignore
        }
        audioSourceRef.current = null;
      }

      const source = ctx.createBufferSource();
      source.buffer = decoded;
      source.connect(ctx.destination);
      audioSourceRef.current = source;
      source.onended = () => {
        if (audioSourceRef.current === source) {
          audioSourceRef.current = null;
        }
      };
      source.start(0);
      return true;
    } catch {
      return false;
    }
  }

  async function speakServerTts(text, speechLang) {
    const value = (text || "").trim();
    if (!value) {
      setError("No text available to speak yet.");
      return;
    }

    try {
      setError("");

      // Stop any HTMLAudio playback.
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = "";
      }

      // Stop any WebAudio playback.
      if (audioSourceRef.current) {
        try {
          audioSourceRef.current.stop();
        } catch {
          // ignore
        }
        audioSourceRef.current = null;
      }

      const { blob } = await fetchTtsAudio({ text: value, lang: speechLang });

      // If audio was unlocked by a user gesture, prefer WebAudio.
      if (audioUnlockedRef.current) {
        const played = await playMp3WithWebAudio(blob);
        if (played) return;
      }

      // Fallback to HTMLAudio.
      const url = URL.createObjectURL(blob);
      audioUrlRef.current = url;

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = "";
        }
        audioRef.current = null;
      };

      try {
        await audio.play();
      } catch (playErr) {
        if (String(playErr?.name || "") === "NotAllowedError") {
          setError(
            "Audio playback was blocked by the browser. Click Speak (Kannada) once to allow audio, then try again.",
          );
        } else {
          setError("Could not play audio. Please try again.");
        }
      }
    } catch (err) {
      const message = String(err?.message || "").trim();
      setError(
        message ||
          "Kannada voice is not available in your browser. Start the backend and ensure internet is on for server TTS, or install Kannada language + speech pack in Windows and restart the browser.",
      );
    }
  }

function speakText(text, speechLang = lang) {
    const value = (text || "").trim();
    if (!value) {
      setError("No text available to speak yet.");
      return;
    }

    const synth = window.speechSynthesis;
    const wantsKannada = speechLang === "kn";

    if (wantsKannada && (!synth || !hasKannadaVoice)) {
      void speakServerTts(value, speechLang);
      return;
    }

    if (!synth) {
      setError("Text-to-speech is not supported in this browser.");
      return;
    }

    const desiredLang = wantsKannada ? "kn-IN" : "en-IN";

    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(value);
    utterance.lang = desiredLang;

    const voices = synth.getVoices() || [];
    const prefix = wantsKannada ? "kn" : "en";
    const preferredVoice =
      voices.find((voice) => (voice.lang || "").toLowerCase().startsWith(prefix + "-in")) ||
      voices.find((voice) => (voice.lang || "").toLowerCase().startsWith(prefix));
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.rate = wantsKannada ? 0.92 : 0.98;
    utterance.pitch = 1;
    synth.speak(utterance);
  }

  function handleCallEmergency() {
    const number = String(callConfig?.phone_number || "108").trim() || "108";

    setError("");
    setShowEmergencyModal(true);

    // Best-effort attempt to open a dialer. On many laptops this only works
    // if a calling app is configured as the OS handler for 	el: links.
    try {
      window.location.href = "tel:" + number;
    } catch {
      // ignore
    }
  }
  async function handleRequestHelpCall() {
    if (!callConfig?.callback_enabled) {
      setError("Callback calling is not enabled.");
      return;
    }

    const saved = window.localStorage.getItem("callback_phone") || "";
    const toNumber = window.prompt("Enter your phone number in E.164 format (example: +919999999999)", saved) || "";
    const trimmed = toNumber.trim();
    if (!trimmed) return;

    window.localStorage.setItem("callback_phone", trimmed);

    setError("");
    setCallRequestLoading(true);
    try {
      const data = await requestHelpCall(trimmed);
      if (data?.ok) {
        setError("Calling you now... Please answer your phone.");
      } else {
        setError(data?.detail || "Could not start the call.");
      }
    } catch (err) {
      setError("Could not start the call. Please try again.");
    } finally {
      setCallRequestLoading(false);
    }
  }

  function startVoiceInput() {
    void unlockAudio();
    if (!recognitionRef.current) {
      setError("Speech-to-text is not supported in this browser.");
      return;
    }
    setError("");
    recognitionRef.current.lang = lang === "kn" ? "kn-IN" : "en-IN";
    recognitionRef.current.start();
  }

  function handleImagePick(event) {
    const file = event.target.files?.[0] || null;

    if (attachedPreviewUrl) {
      URL.revokeObjectURL(attachedPreviewUrl);
    }

    if (!file) {
      setAttachedImage(null);
      setAttachedPreviewUrl("");
      return;
    }

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      setAttachedImage(null);
      setAttachedPreviewUrl("");
      return;
    }

    setError("");
    setError("");
    setAttachedAudio(null);

    if (prescriptionPreviewUrl) {
      URL.revokeObjectURL(prescriptionPreviewUrl);
    }
    setAttachedPrescription(null);
    setPrescriptionPreviewUrl("");

    setAttachedImage(file);
    setAttachedPreviewUrl(URL.createObjectURL(file));
  }


  function handlePrescriptionPick(event) {
    const file = event.target.files?.[0] || null;

    if (prescriptionPreviewUrl) {
      URL.revokeObjectURL(prescriptionPreviewUrl);
    }

    if (!file) {
      setAttachedPrescription(null);
      setPrescriptionPreviewUrl("");
      return;
    }

    if (!file.type.startsWith("image/")) {
      setError("Please select a valid image file.");
      setAttachedPrescription(null);
      setPrescriptionPreviewUrl("");
      return;
    }

    // Clear other attachments
    if (attachedPreviewUrl) {
      URL.revokeObjectURL(attachedPreviewUrl);
    }
    setAttachedImage(null);
    setAttachedPreviewUrl("");
    setAttachedAudio(null);

    setError("");
    setAttachedPrescription(file);
    setPrescriptionPreviewUrl(URL.createObjectURL(file));
  }

  function handleAudioPick(event) {
    const file = event.target.files?.[0] || null;

    if (!file) {
      setAttachedAudio(null);
      return;
    }

    if (file.type && !file.type.startsWith("audio/")) {
      setError("Please select a valid audio file.");
      setAttachedAudio(null);
      return;
    }

    setError("");
    setAttachedAudio(file);
    setAttachedImage(null);
    setAttachedPrescription(null);
    if (attachedPreviewUrl) {
      URL.revokeObjectURL(attachedPreviewUrl);
      setAttachedPreviewUrl("");
    }
    if (prescriptionPreviewUrl) {
      URL.revokeObjectURL(prescriptionPreviewUrl);
      setPrescriptionPreviewUrl("");
    }
  }

  function clearSelectedAttachment() {
    setAttachedAudio(null);
    setAttachedImage(null);
    setAttachedPrescription(null);
    if (attachedPreviewUrl) {
      URL.revokeObjectURL(attachedPreviewUrl);
    }
    if (prescriptionPreviewUrl) {
      URL.revokeObjectURL(prescriptionPreviewUrl);
    }
    setAttachedPreviewUrl("");
    setPrescriptionPreviewUrl("");

    if (imageInputRef.current) imageInputRef.current.value = "";
    if (prescriptionInputRef.current) prescriptionInputRef.current.value = "";
    if (audioInputRef.current) audioInputRef.current.value = "";
  }

  function markAllNotificationsRead() {
    setReadNotificationIds(notifications.map((item) => item.id));
  }

  async function handleSend(event) {
    event.preventDefault();

    const trimmed = input.trim();
    const hasVoice = Boolean(attachedAudio);
    const hasPrescription = Boolean(attachedPrescription);
    const hasImage = Boolean(attachedImage);

    if (!hasVoice && !hasPrescription && !hasImage && !trimmed) {
      setError("Please enter symptoms or upload an image/voice note.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      if (hasVoice) {
        const data = await sendVoiceMessage(attachedAudio, lang);
        const userMessage = {
          role: "user",
          content: data.transcript_en,
          timestamp: new Date().toISOString(),
        };
        const botMessage = {
          role: "bot",
          content: data.response,
          speechText: data.speech_text || null,
          speechLang: data.speech_lang || lang,
          timestamp: new Date().toISOString(),
          chatId: data.chat_id,
          pendingSeverity: Boolean(data.pending_severity),
          severityOptions: data.severity_options || null,
          tabletSuggestions: data.tablet_suggestions || null,
          careLocations: data.care_locations || null,
        };

        setMessages((prev) => [...prev, userMessage, botMessage]);
        if (autoSpeak) {
          speakText(data.speech_text || data.response, data.speech_lang || lang);
        }
        setInput("");
      } else if (hasPrescription) {
        const userText = trimmed || "Prescription image uploaded.";
        const userMessage = {
          role: "user",
          content: userText,
          timestamp: new Date().toISOString(),
          imagePreviewUrl: prescriptionPreviewUrl || null,
        };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");

        const data = await sendPrescriptionMessage({ message: trimmed, image: attachedPrescription, lang });
        const botMessage = {
          role: "bot",
          content: data.response,
          speechText: data.speech_text || null,
          speechLang: data.speech_lang || lang,
          timestamp: new Date().toISOString(),
          chatId: data.chat_id,
          pendingSeverity: false,
          severityOptions: null,
          tabletSuggestions: null,
          careLocations: data.care_locations || null,
        };
        setMessages((prev) => [...prev, botMessage]);
        if (autoSpeak) {
          speakText(data.speech_text || data.response, data.speech_lang || lang);
        }
      } else if (hasImage) {
        const userText = trimmed || "Image uploaded.";
        const userMessage = {
          role: "user",
          content: userText,
          timestamp: new Date().toISOString(),
          imagePreviewUrl: attachedPreviewUrl || null,
        };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");

        const data = await sendAutoImageMessage({ message: trimmed, image: attachedImage, lang });
        const botMessage = {
          role: "bot",
          content: data.response,
          speechText: data.speech_text || null,
          speechLang: data.speech_lang || lang,
          timestamp: new Date().toISOString(),
          chatId: data.chat_id,
          pendingSeverity: false,
          severityOptions: null,
          tabletSuggestions: null,
          careLocations: data.care_locations || null,
        };
        setMessages((prev) => [...prev, botMessage]);
        if (autoSpeak) {
          speakText(data.speech_text || data.response, data.speech_lang || lang);
        }
      } else {

        const userMessage = {
          role: "user",
          content: trimmed,
          timestamp: new Date().toISOString(),
          imagePreviewUrl: attachedPreviewUrl || null,
        };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");

        const data = await sendChatMessage({ message: trimmed, image: attachedImage, lang });
        const botMessage = {
          role: "bot",
          content: data.response,
          speechText: data.speech_text || null,
          speechLang: data.speech_lang || lang,
          timestamp: new Date().toISOString(),
          chatId: data.chat_id,
          pendingSeverity: Boolean(data.pending_severity),
          severityOptions: data.severity_options || null,
          tabletSuggestions: data.tablet_suggestions || null,
          careLocations: data.care_locations || null,
        };
        setMessages((prev) => [...prev, botMessage]);
        if (autoSpeak) {
          speakText(data.speech_text || data.response, data.speech_lang || lang);
        }
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to get chatbot response. Please try again."));
    } finally {
      setLoading(false);
      setAttachedAudio(null);
      setAttachedImage(null);
      setAttachedPrescription(null);
      if (attachedPreviewUrl) {
        URL.revokeObjectURL(attachedPreviewUrl);
      }
      if (prescriptionPreviewUrl) {
        URL.revokeObjectURL(prescriptionPreviewUrl);
      }
      setAttachedPreviewUrl("");
      setPrescriptionPreviewUrl("");
      if (imageInputRef.current) imageInputRef.current.value = "";
      if (prescriptionInputRef.current) prescriptionInputRef.current.value = "";
      if (audioInputRef.current) audioInputRef.current.value = "";
    }
  }


  async function handleSeveritySelect(chatId, severity) {
    if (!chatId || severityLoadingChatId) {
      return;
    }

    setError("");
    void unlockAudio();
    setSeverityLoadingChatId(chatId);

    try {
      const data = await sendSeverity({ chat_id: chatId, severity, lang });
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.role === "bot" && msg.chatId === chatId && msg.pendingSeverity) {
            return {
              ...msg,
              content: data.response,
              speechText: data.speech_text || null,
          speechLang: data.speech_lang || lang,
              pendingSeverity: false,
              severityOptions: null,
              tabletSuggestions: data.tablet_suggestions || null,
              careLocations: data.care_locations || null,
            };
          }
          return msg;
        }),
      );
      if (autoSpeak) {
        speakText(data.speech_text || data.response, data.speech_lang || lang);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to get severity response. Please try again."));
    } finally {
      setSeverityLoadingChatId(null);
    }
  }

  return (
    <main className="container dashboard">
      <div className="dashboard-star-layer" aria-hidden="true" />
      <div className="dashboard-head dashboard-head--modern">
        <div>
          <h2>Hello, {displayName}!</h2>
          <p>How can I help with your health today? Choose English or Kannada for text and voice replies.</p>
        </div>
        <div className="head-actions">
          <Link to="/health-report" className="btn-outline top-report-btn">Health Report</Link>
          <div className="notify-wrap" ref={notificationsRef}>
            <button
              type="button"
              className="icon-pill icon-pill--notify"
              aria-label="Notifications"
              aria-expanded={showNotifications}
              onClick={() => setShowNotifications((prev) => !prev)}
              ref={notifyButtonRef}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M6 10a6 6 0 1 1 12 0v5l1.5 2h-15L6 15v-5Z" stroke="currentColor" strokeWidth="1.6" />
                <path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              {unreadCount > 0 && <span className="notify-dot" />}
            </button>
          </div>
          <button type="button" className="user-chip" aria-label="Account">
            <span className="user-chip__avatar">{userInitial}</span>
            <span className="user-chip__name">{displayName}</span>
            <span className="user-chip__caret">v</span>
          </button>
        </div>
      </div>
      <div className="dashboard-layout">
        <div className="dashboard-main">
      <section className="assist-toolbar">
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" className="btn-outline" onClick={() => setLang("en")} aria-pressed={lang === "en"}>English</button>
          <button type="button" className="btn-outline" onClick={() => setLang("kn")} aria-pressed={lang === "kn"}>Kannada</button>
        </div>
        <button type="button" className="action-btn action-btn--voice" onClick={startVoiceInput} disabled={!speechSupported || listening || loading}>
          {listening ? "Listening..." : "Voice Input"}
        </button>
        <button
          type="button"
          className="btn-outline"
          onClick={() => latestBotMessageWithSpeech && speakText(latestBotMessageWithSpeech.speechText || latestBotMessageWithSpeech.content, latestBotMessageWithSpeech.speechLang || lang)}
          disabled={!latestBotMessageWithSpeech}
          title={!latestBotMessageWithSpeech ? "Send a new message to get Kannada voice" : ""}
        >
          Speak Reply
        </button>
        <label className="toggle-label" htmlFor="autoSpeak">
          <input
            id="autoSpeak"
            type="checkbox"
            checked={autoSpeak}
            onChange={(event) => setAutoSpeak(event.target.checked)}
          />
          Auto-read
        </label>
        {callConfig.callback_enabled && (
          <button
            type="button"
            className="btn-primary call-button"
            onClick={handleRequestHelpCall}
            disabled={callRequestLoading}
            title={callRequestLoading ? "Calling..." : "Request an incoming call"}
          >
            {callRequestLoading ? "Calling..." : "Request Call Back"}
          </button>
        )}

        {callConfig.call_enabled && (
          <button type="button" className="action-btn action-btn--emergency" onClick={handleCallEmergency}>Emergency Call</button>
        )}
      </section>

      {!ttsSupported && <p className="error-text">Text-to-speech is not supported in this browser.</p>}
      {showEmergencyModal && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          onClick={() => setShowEmergencyModal(false)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Emergency Call</h3>
            <p style={{ marginTop: 0 }}>
              Dial <strong>{String(callConfig?.phone_number || "108")}</strong>.
              On a laptop this works only if a calling app is set as the handler for <code>tel:</code> links.
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn-primary"
                onClick={() => {
                  const number = String(callConfig?.phone_number || "108").trim() || "108";
                  navigator.clipboard?.writeText(number);
                  setError("Copied emergency number: " + number);
                }}
              >
                Copy Number
              </button>
              <button
                type="button"
                className="btn-outline"
                onClick={() => {
                  const number = String(callConfig?.phone_number || "108").trim() || "108";
                  window.location.href = "tel:" + number;
                }}
              >
                Open Dialer
              </button>
              <button type="button" className="btn-outline" onClick={() => setShowEmergencyModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <section className="chat-box">
        <div className="chat-stars" aria-hidden="true" />
        <div className="messages" ref={messagesRef} aria-live="polite">
          {messages.length === 0 && (
            <div className="placeholder-guide">
              <p className="placeholder" style={{ marginTop: 0 }}>Start by typing your symptoms in plain language.</p>
              <p className="info-text" style={{ margin: 0 }}>Example: "I have fever, sore throat, and body pain since yesterday."</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={String(message.timestamp) + "-" + String(index)} className={"message " + message.role}>
              {message.role === "bot" && <MessageAvatar role="bot" />}
              <div className="bubble">
                {renderMessageContent(message)}
                {message.role === "bot" && !message.pendingSeverity && message.tabletSuggestions && (
                  <TabletSuggestions suggestions={message.tabletSuggestions} onSelect={setSelectedTablet} />
                )}
                {message.role === "bot" && !message.pendingSeverity && message.careLocations && message.careLocations.length > 0 && (
                  <div className="care-locations">
                    <div className="care-title">Nearby hospitals/clinics (Maps)</div>
                    {message.careLocations.map((loc, idx) => (
                      <a
                        key={String(loc?.maps_url || loc?.name || idx)}
                        className="care-link"
                        href={loc.maps_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {loc.name || "Open in Maps"}
                      </a>
                    ))}
                  </div>
                )}
                {message.role === "bot" && message.pendingSeverity && (
                  <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="btn-secondary severity-btn"
                      onClick={() => handleSeveritySelect(message.chatId, "mild")}
                      disabled={loading || severityLoadingChatId === message.chatId}
                    >
                      <span className="severity-dot severity-dot--mild" aria-hidden="true" /> Mild
                    </button>
                    <button
                      type="button"
                      className="btn-secondary severity-btn"
                      onClick={() => handleSeveritySelect(message.chatId, "moderate")}
                      disabled={loading || severityLoadingChatId === message.chatId}
                    >
                      <span className="severity-dot severity-dot--moderate" aria-hidden="true" /> Moderate
                    </button>
                    <button
                      type="button"
                      className="btn-secondary severity-btn"
                      onClick={() => handleSeveritySelect(message.chatId, "severe")}
                      disabled={loading || severityLoadingChatId === message.chatId}
                    >
                      <span className="severity-dot severity-dot--severe" aria-hidden="true" /> Severe
                    </button>
                  </div>
                )}
                {(message.imageUrl || message.imagePreviewUrl) && (
                  <img
                    src={message.imageUrl || message.imagePreviewUrl}
                    alt="Attached"
                    style={{ maxWidth: 260, width: "100%", borderRadius: 10, marginTop: 10 }}
                  />
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message bot">
              <MessageAvatar role="bot" />
              <div className="bubble bubble--typing">Analyzing your message...</div>
            </div>
          )}
        </div>

        <div className="quick-prompts">
          {quickPrompts.map((item) => (
            <button
              key={item.label}
              type="button"
              className="quick-prompt-btn"
              onClick={() => {
                setInput(item.prompt);
                if (textInputRef.current) textInputRef.current.focus();
              }}
              disabled={loading}
            >
              <QuickPromptIcon kind={item.icon} />
              {item.label}
            </button>
          ))}
        </div>

        <form className="chat-input" onSubmit={handleSend}>
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            onChange={handleImagePick}
            disabled={loading}
            style={{ display: "none" }}
          />
          <input
            ref={prescriptionInputRef}
            type="file"
            accept="image/*"
            onChange={handlePrescriptionPick}
            disabled={loading}
            style={{ display: "none" }}
          />
          <input
            ref={audioInputRef}
            type="file"
            accept="audio/*"
            onChange={handleAudioPick}
            disabled={loading}
            style={{ display: "none" }}
          />

          {activeAttachment && (
            <div className="attachment-banner">
              <span className="attachment-badge">{activeAttachment.type}</span>
              <span className="attachment-name" title={activeAttachment.name}>{activeAttachment.name}</span>
              <button type="button" className="attachment-clear" onClick={clearSelectedAttachment} disabled={loading}>
                Remove
              </button>
            </div>
          )}

          <div className="composer composer--clean">
            <button
              type="button"
              className="composer-btn composer-btn--attach composer-btn--clean"
              onClick={() => imageInputRef.current && imageInputRef.current.click()}
              disabled={loading}
              title="Upload image"
            >
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M8 7l1.2-2h5.6L16 7h2.2A2.8 2.8 0 0 1 21 9.8v8.4A2.8 2.8 0 0 1 18.2 21H5.8A2.8 2.8 0 0 1 3 18.2V9.8A2.8 2.8 0 0 1 5.8 7H8Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
                <path d="M12 17a3.7 3.7 0 1 0 0-7.4 3.7 3.7 0 0 0 0 7.4Z" stroke="currentColor" strokeWidth="1.8" />
              </svg>
            </button>

            <div className="composer-field composer-field--clean">
              <input
                ref={textInputRef}
                className="composer-input composer-input--clean"
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Type your symptoms or health question..."
                maxLength={1000}
                disabled={loading}
              />
              <button
                type="button"
                className="composer-mic"
                onClick={startVoiceInput}
                disabled={loading || !speechSupported || listening}
                title={!speechSupported ? "Speech-to-text not supported" : listening ? "Listening..." : (lang === "kn" ? "Speak (Kannada)" : "Speak (English)")}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3Z" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M19 11a7 7 0 0 1-14 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <path d="M12 18v3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </button>
            </div>

            <button type="submit" className="composer-btn composer-btn--send composer-btn--clean" disabled={loading || !canSubmit} title="Send">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 12h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M13 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </form>
      </section>
        </div>

        <aside className="dashboard-side">
          <section className="side-card">
            <div className="side-card__head">
              <h3>Daily Health Tip</h3>
            </div>
            <p>Start your day with warm water and lemon. It helps in detoxification and boosts metabolism.</p>
          </section>

          <section className="side-card side-card--care">
            <div className="side-card__head">
              <h3>Personal Care</h3>
            </div>
            <div className="care-grid">
              <article className="care-item care-item--hydration">
                <div className="care-item__icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M12 3c2.4 3 5 6.1 5 9.2A5 5 0 1 1 7 12.2C7 9.1 9.6 6 12 3Z" stroke="currentColor" strokeWidth="1.8" />
                    <path d="M9.2 13.2a3 3 0 0 0 5.1 1.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                  </svg>
                </div>
                <div className="care-item__title">Hydration</div>
                <div className="care-item__line">Keep it up!</div>
                <div className="care-item__meta">6/8 glasses</div>
              </article>
              <article className="care-item care-item--meditation">
                <div className="care-item__icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M12 7c1.6 2.1 2.6 3.6 2.6 5.2A2.6 2.6 0 1 1 9.4 12.2C9.4 10.6 10.4 9.1 12 7Z" stroke="currentColor" strokeWidth="1.7" />
                    <path d="M4.5 15.3c1.7-.2 3.4.3 4.7 1.3M19.5 15.3c-1.7-.2-3.4.3-4.7 1.3M8.2 18.2h7.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                  </svg>
                </div>
                <div className="care-item__title">Meditation</div>
                <div className="care-item__line">10 min</div>
                <div className="care-item__meta">Daily</div>
              </article>
              <article className="care-item care-item--stretching">
                <div className="care-item__icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none">
                    <circle cx="13.5" cy="4.8" r="2.2" stroke="currentColor" strokeWidth="1.6" />
                    <path d="M12.5 8.5 9.8 11l-3.3.6M12.7 8.8l3.6 2 2.7-.1M11.8 11.8l-2.2 2.8m2.2-2.8 2.9 2.8m-5.1 0-2.4 2.8m5.8-2.8 2.8 2.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="care-item__title">Stretching</div>
                <div className="care-item__line">15 min</div>
                <div className="care-item__meta">Daily</div>
              </article>
              <article className="care-item care-item--sleep">
                <div className="care-item__icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M15.8 4.1a8.2 8.2 0 1 0 4.1 15.1A7.3 7.3 0 0 1 15.8 4Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </div>
                <div className="care-item__title">Sleep Goal</div>
                <div className="care-item__line">7-8 hrs</div>
                <div className="care-item__meta">Tonight</div>
              </article>
            </div>
          </section>

          <section className="side-card side-card--motivation">
            <h3>Small steps today, better health tomorrow.</h3>
            <p>You've got this! <span className="motivation-heart">&hearts;</span></p>
            <svg className="motivation-art" viewBox="0 0 420 170" aria-hidden="true">
              <defs>
                <linearGradient id="skyGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#1c3a78" stopOpacity="0.35" />
                  <stop offset="55%" stopColor="#7f2e84" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#f58e6a" stopOpacity="0.25" />
                </linearGradient>
              </defs>
              <rect x="0" y="0" width="420" height="170" fill="url(#skyGrad)" />
              <path d="M180 150L245 95L278 122L322 88L380 150Z" fill="rgba(24,36,86,0.68)" />
              <path d="M130 150L215 83L262 120L310 96L360 150Z" fill="rgba(32,48,102,0.72)" />
              <path d="M96 150L188 101L234 124L272 108L316 150Z" fill="rgba(18,30,76,0.78)" />
              <circle cx="334" cy="34" r="8" fill="rgba(255, 220, 255, 0.42)" />
              <circle cx="360" cy="22" r="3" fill="rgba(255, 220, 255, 0.52)" />
              <g fill="rgba(8, 16, 45, 0.92)">
                <circle cx="285" cy="56" r="8" />
                <path d="M272 72c6-10 20-10 26 0l5 16-14 8h-10l-13-8Z" />
                <path d="M252 122c9-18 20-28 33-28s24 10 33 28h-20l-13-17-13 17Z" />
                <path d="M250 132c16-11 55-11 70 0-13 8-56 8-70 0Z" />
              </g>
            </svg>
          </section>

          <section className="side-card side-card--contacts">
            <div className="side-card__head">
              <h3>Emergency Contacts</h3>
              <button type="button" className="btn-link-inline" onClick={handleCallEmergency}>View All</button>
            </div>
            <div className="contact-row">
              <span>Ambulance</span>
              <strong className="pill-num pill-num--danger">102</strong>
            </div>
            <div className="contact-row">
              <span>Health Helpline</span>
              <strong className="pill-num pill-num--info">104</strong>
            </div>
            <div className="contact-row">
              <span>Emergency Desk</span>
              <strong className="pill-num pill-num--ok">{String(callConfig?.phone_number || "08046110007")}</strong>
            </div>
          </section>
        </aside>
      </div>

      {selectedTablet && (
        <div className="tablet-modal" onClick={() => setSelectedTablet(null)}>
          <div className="tablet-modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="tablet-modal-head">
              <div className="tablet-modal-title">{selectedTablet?.name || "Medicine"}</div>
              <button type="button" className="tablet-modal-close" onClick={() => setSelectedTablet(null)}>
                Close
              </button>
            </div>
            <div className="tablet-modal-body">
              <img
                key={String(selectedTablet?.image_key || selectedTablet?.name || "tablet")}
                data-fallback-index="0"
                className="tablet-modal-image"
                src={getTabletImageUrl(selectedTablet?.image_key)}
                alt={selectedTablet?.name || "Tablet"}
                onLoad={(event) => { event.currentTarget.dataset.fallbackIndex = "0"; }}
                onError={(event) => handleTabletImageError(event, selectedTablet?.image_key)}
                            />
              <div>
                <div className="tablet-use" style={{ fontSize: "1rem" }}>{selectedTablet?.use || ""}</div>
                <div className="tablet-disclaimer">{selectedTablet?.disclaimer || "For reference only. Consult doctor before use."}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
      {showNotifications &&
        createPortal(
          <div ref={notifyPanelRef} className="notify-panel" style={notifyPanelStyle} role="dialog" aria-label="Notifications panel">
            <div className="notify-panel__head">
              <strong>Notifications</strong>
              <button type="button" className="btn-link-inline" onClick={markAllNotificationsRead}>
                Mark all as read
              </button>
            </div>
            <div className="notify-list">
              {notifications.map((item) => {
                const unread = !readNotificationIds.includes(item.id);
                return (
                  <div key={item.id} className={"notify-item" + (unread ? " is-unread" : "")}>
                    <div className="notify-item__title">{item.title}</div>
                    <div className="notify-item__detail">{item.detail}</div>
                  </div>
                );
              })}
            </div>
          </div>,
          document.body,
        )}
    </main>
  );
}

export default ChatbotDashboard;






































