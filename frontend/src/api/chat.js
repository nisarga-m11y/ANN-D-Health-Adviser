import { apiClient } from "./client";

export async function sendChatMessage({ message, image, lang = "en" }) {
  if (image) {
    const formData = new FormData();
    formData.append("message", message);
    formData.append("lang", lang);
    formData.append("image", image);
    const { data } = await apiClient.post("/chat/message/", formData);
    return data;
  }

  const { data } = await apiClient.post("/chat/message/", { message, lang });
  return data;
}

export async function sendPrescriptionMessage({ message, image, lang = "en" }) {
  const formData = new FormData();
  if (message) {
    formData.append("message", message);
  }
  formData.append("lang", lang);
  formData.append("image", image);
  const { data } = await apiClient.post("/chat/prescription-message/", formData);
  return data;
}

export async function sendVoiceMessage(audio, lang = "en") {
  const formData = new FormData();
  formData.append("audio", audio);
  formData.append("lang", lang);
  const { data } = await apiClient.post("/chat/voice/", formData);
  return data;
}

export async function translateToEnglish(text) {
  const { data } = await apiClient.post("/chat/translate/", { text });
  return data;
}

export async function fetchChatHistory() {
  const { data } = await apiClient.get("/chat/history/");
  return data;
}

export async function uploadSymptomImage({ image, category, lang = "en" }) {
  const formData = new FormData();
  formData.append("image", image);
  formData.append("category", category);
  formData.append("lang", lang);
  const { data } = await apiClient.post("/chat/image-analysis/", formData);
  return data;
}

export async function fetchCallConfig() {
  const { data } = await apiClient.get("/chat/call-config/");
  return data;
}

export async function sendSeverity({ chat_id, severity, lang = "en" }) {
  const { data } = await apiClient.post("/chat/severity/", { chat_id, severity, lang });
  return data;
}

export async function sendFollowup({ chat_id, answer }) {
  const { data } = await apiClient.post("/chat/followup/", { chat_id, answer });
  return data;
}

export async function requestHelpCall(phone_number) {
  const { data } = await apiClient.post("/chat/call/", { phone_number });
  return data;
}

export async function sendMedicineMessage({ message, image, lang = "en" }) {
  const formData = new FormData();
  if (message) {
    formData.append("message", message);
  }
  formData.append("lang", lang);
  formData.append("image", image);
  const { data } = await apiClient.post("/chat/medicine-message/", formData);
  return data;
}

export async function sendAutoImageMessage({ message, image, lang = "en" }) {
  const formData = new FormData();
  if (message) {
    formData.append("message", message);
  }
  formData.append("lang", lang);
  formData.append("image", image);
  const { data } = await apiClient.post("/chat/image-auto/", formData);
  return data;
}
export async function fetchTtsAudio({ text, lang = "en" }) {
  try {
    const resp = await apiClient.post(
      "/chat/tts/",
      { text, lang },
      { responseType: "arraybuffer", timeout: 90000 },
    );

    const contentType = resp?.headers?.["content-type"] || "audio/mpeg";
    const provider = resp?.headers?.["x-tts-provider"] || "";

    return {
      blob: new Blob([resp.data], { type: contentType }),
      provider,
    };
  } catch (err) {
    const status = err?.response?.status;
    const headers = err?.response?.headers || {};
    const contentType = headers?.["content-type"] || "";

    let detail = "";
    const data = err?.response?.data;

    try {
      if (typeof data === "string") {
        detail = data;
      } else if (data && data instanceof ArrayBuffer) {
        const text = new TextDecoder("utf-8").decode(new Uint8Array(data));
        if (contentType.includes("application/json")) {
          const parsed = JSON.parse(text);
          detail = parsed?.detail || text;
        } else {
          detail = text;
        }
      } else if (data && typeof data === "object") {
        detail = data?.detail || JSON.stringify(data);
      }
    } catch {
      // ignore parse errors
    }

    const base = String(apiClient?.defaults?.baseURL || "");
    const fallback = (detail || String(err?.message || "").trim() || "TTS request failed") + (status ? " (HTTP " + status + ")" : "");
    const message = base ? (fallback + " | backend: " + base) : (fallback + ".");
    throw new Error(message);
  }
}


