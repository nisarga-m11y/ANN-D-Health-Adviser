const symptomForm = document.getElementById("symptomForm");
const symptomsInput = document.getElementById("symptoms");
const analyzeBtn = document.getElementById("analyzeBtn");
const loader = document.getElementById("loader");
const resultSection = document.getElementById("result");

const resultCard = document.getElementById("resultCard");
const severityBadge = document.getElementById("severityBadge");
const severityText = document.getElementById("severityText");
const diseaseName = document.getElementById("diseaseName");
const confidencePct = document.getElementById("confidencePct");
const tabletList = document.getElementById("tabletList");
const tabletNote = document.getElementById("tabletNote");
const remedyList = document.getElementById("remedyList");
const adviceText = document.getElementById("adviceText");

const speakBtn = document.getElementById("speakBtn");
const resetBtn = document.getElementById("resetBtn");

const micBtn = document.getElementById("micBtn");
micBtn.addEventListener("click", () => {
  toast("Microphone UI only (voice recognition not wired).");
});

function toast(message) {
  const el = document.createElement("div");
  el.textContent = message;
  el.style.position = "fixed";
  el.style.left = "50%";
  el.style.bottom = "18px";
  el.style.transform = "translateX(-50%)";
  el.style.padding = "10px 12px";
  el.style.borderRadius = "14px";
  el.style.border = "1px solid rgba(255,255,255,.18)";
  el.style.background = "rgba(10,3,22,.72)";
  el.style.color = "rgba(246,242,255,.95)";
  el.style.boxShadow = "0 16px 40px rgba(0,0,0,.45)";
  el.style.zIndex = "9999";
  el.style.maxWidth = "min(92vw, 560px)";
  el.style.fontSize = "13px";
  el.style.backdropFilter = "blur(10px)";
  el.style.opacity = "0";
  el.style.transition = "opacity .2s ease, transform .2s ease";
  document.body.appendChild(el);
  requestAnimationFrame(() => {
    el.style.opacity = "1";
    el.style.transform = "translateX(-50%) translateY(-2px)";
  });
  window.setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateX(-50%) translateY(2px)";
    window.setTimeout(() => el.remove(), 250);
  }, 1600);
}

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s,.-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const severityRules = {
  emergency: [
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "faint",
    "unconscious",
    "seizure",
    "stroke",
    "one-sided weakness",
    "slurred speech",
    "severe bleeding",
    "blue lips",
    "confusion",
  ],
  moderate: [
    "high fever",
    "persistent fever",
    "severe pain",
    "vomiting",
    "dehydration",
    "blood",
    "wheezing",
    "severe headache",
    "stiff neck",
    "burning urination",
  ],
};

const pillImages = {
  purple: "assets/tablet-purple.svg",
  teal: "assets/tablet-teal.svg",
  amber: "assets/tablet-amber.svg",
  red: "assets/tablet-red.svg",
};

const conditions = [
  {
    name: "Common Cold",
    keywords: ["runny nose", "sneezing", "mild fever", "congestion", "sore throat", "cough"],
    baseSeverity: "mild",
    tablets: [
      { name: "Paracetamol (if fever)", meta: "Use as directed; avoid duplicate acetaminophen products.", img: pillImages.teal },
      { name: "Antihistamine (if sneezing)", meta: "May cause drowsiness; avoid driving if sleepy.", img: pillImages.purple },
    ],
    remedies: ["Warm fluids (tea/soup)", "Steam inhalation", "Rest and hydration", "Honey for cough (avoid in infants)"],
    advice:
      "Monitor symptoms for 24–48 hours. Seek medical advice if fever persists, breathing difficulty occurs, or symptoms worsen. This is not a diagnosis.",
  },
  {
    name: "Flu / Viral Fever",
    keywords: ["fever", "body ache", "fatigue", "chills", "cough", "sore throat", "headache"],
    baseSeverity: "moderate",
    tablets: [
      { name: "Paracetamol", meta: "For fever/pain. Follow label dosing; avoid alcohol.", img: pillImages.teal },
      { name: "ORS / Electrolytes", meta: "Helps hydration; sip slowly if nauseated.", img: pillImages.amber },
    ],
    remedies: ["Rest in a cool room", "Warm water gargle", "Hydration + light meals", "Avoid heavy workouts until better"],
    advice:
      "If fever is high or lasts >3 days, or if you have chest pain/shortness of breath, consult a doctor urgently. This is not a diagnosis.",
  },
  {
    name: "Migraine Pattern",
    keywords: ["headache", "nausea", "light sensitivity", "sound sensitivity", "throbbing", "one sided"],
    baseSeverity: "moderate",
    tablets: [
      { name: "Pain relief (doctor-approved)", meta: "Avoid overuse. Consult a clinician for recurrent headaches.", img: pillImages.purple },
    ],
    remedies: ["Dark, quiet room", "Cold compress", "Hydration", "Regular meals and sleep"],
    advice:
      "Seek urgent care if headache is sudden/worst ever, with weakness, confusion, or stiff neck. This is not a diagnosis.",
  },
  {
    name: "Gastritis / Acidity",
    keywords: ["acidity", "heartburn", "burning stomach", "gas", "bloating", "nausea", "after eating"],
    baseSeverity: "mild",
    tablets: [{ name: "Antacid (short-term)", meta: "Follow label; avoid if you have kidney disease unless advised.", img: pillImages.amber }],
    remedies: ["Small frequent meals", "Avoid spicy/oily foods", "Avoid lying down after meals", "Warm water sips"],
    advice:
      "If pain is severe, persistent, or you see blood/black stools, consult a doctor. This is not a diagnosis.",
  },
  {
    name: "Allergy / Irritation",
    keywords: ["itchy", "rash", "sneezing", "watery eyes", "hives", "allergy"],
    baseSeverity: "mild",
    tablets: [{ name: "Antihistamine (if needed)", meta: "May cause drowsiness. Follow label instructions.", img: pillImages.purple }],
    remedies: ["Cool compress on itchy areas", "Avoid known triggers", "Gentle moisturiser", "Hydration"],
    advice:
      "Emergency signs: swelling of lips/face, wheezing, or breathing difficulty — seek help immediately. This is not a diagnosis.",
  },
  {
    name: "Food-borne Illness (possible)",
    keywords: ["diarrhea", "vomiting", "stomach cramps", "nausea", "bad food", "loose motion"],
    baseSeverity: "moderate",
    tablets: [
      { name: "ORS / Electrolytes", meta: "Main priority is hydration.", img: pillImages.amber },
      { name: "Probiotic (optional)", meta: "May help some people; avoid if immunocompromised unless advised.", img: pillImages.teal },
    ],
    remedies: ["Rest", "Small sips of fluids", "Banana/rice/toast", "Avoid dairy and oily foods temporarily"],
    advice:
      "See a doctor if there is blood in stool, severe dehydration, or symptoms persist. This is not a diagnosis.",
  },
];

function pickBestCondition(text) {
  const hay = normalize(text);
  const scored = conditions
    .map((c) => {
      const hits = c.keywords.filter((k) => hay.includes(k));
      const score = hits.length / Math.max(1, c.keywords.length);
      return { condition: c, hits, score };
    })
    .sort((a, b) => b.score - a.score);

  const top = scored[0];
  if (!top || top.score < 0.18) {
    return {
      name: "General Symptom Review",
      confidence: 0.42,
      severity: inferSeverity(hay, "mild"),
      tablets: [{ name: "Avoid self-medication", meta: "If symptoms are concerning, seek professional care.", img: pillImages.red }],
      remedies: ["Rest", "Hydration", "Light meals", "Monitor symptoms for changes"],
      advice: "If symptoms are severe, sudden, or worsening, consult a doctor urgently. This is not a diagnosis.",
      tabletNote:
        "If you are pregnant, have chronic conditions, or take regular medicines, consult a clinician before taking new tablets.",
    };
  }

  const confidence = clamp(0.55 + top.score * 0.4, 0.55, 0.92);
  const severity = inferSeverity(hay, top.condition.baseSeverity);
  const tabletNote =
    severity === "emergency"
      ? "Emergency: do not delay care. Avoid self-medication unless a clinician has advised it previously."
      : "Tablet suggestions are general and may not be suitable for everyone. Follow labels and consult a clinician for persistent symptoms.";

  return {
    name: top.condition.name,
    confidence,
    severity,
    tablets: top.condition.tablets,
    remedies: top.condition.remedies,
    advice: top.condition.advice,
    tabletNote,
  };
}

function inferSeverity(hay, baseSeverity) {
  if (severityRules.emergency.some((k) => hay.includes(k))) return "emergency";
  if (severityRules.moderate.some((k) => hay.includes(k))) return "moderate";
  return baseSeverity || "mild";
}

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

function setHidden(el, hidden) {
  if (hidden) el.setAttribute("hidden", "");
  else el.removeAttribute("hidden");
}

function setSeverityUI(severity) {
  resultCard.classList.remove("severity-mild", "severity-moderate", "severity-emergency");
  const normalized = severity === "severe" ? "emergency" : severity;
  resultCard.classList.add(`severity-${normalized}`);

  severityBadge.classList.remove("severity-mild", "severity-moderate", "severity-emergency");
  severityBadge.classList.add(`severity-${normalized}`);

  const label = normalized === "emergency" ? "Emergency" : normalized === "moderate" ? "Moderate" : "Mild";
  severityText.textContent = label;
}

function renderTablets(items) {
  tabletList.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "tablet";

    const img = document.createElement("img");
    img.alt = item.name;
    img.src = item.img;
    img.loading = "lazy";

    const body = document.createElement("div");
    const name = document.createElement("div");
    name.className = "tablet__name";
    name.textContent = item.name;

    const meta = document.createElement("div");
    meta.className = "tablet__meta";
    meta.textContent = item.meta;

    body.appendChild(name);
    body.appendChild(meta);

    row.appendChild(img);
    row.appendChild(body);
    tabletList.appendChild(row);
  }
}

function renderRemedies(items) {
  remedyList.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    remedyList.appendChild(li);
  }
}

function buildSpeakText(model) {
  const severityLine =
    model.severity === "emergency"
      ? "Severity looks urgent."
      : model.severity === "moderate"
        ? "Severity looks moderate."
        : "Severity looks mild.";
  const confidenceLine = `Confidence about ${Math.round(model.confidence * 100)} percent.`;
  const remedies = model.remedies.slice(0, 3).join(", ");
  return `ANN-D Health Advisor result. Predicted: ${model.name}. ${severityLine} ${confidenceLine} Home remedies: ${remedies}. Advice: ${model.advice}`;
}

function speak(text) {
  const synth = window.speechSynthesis;
  if (!synth || typeof window.SpeechSynthesisUtterance !== "function") {
    toast("Speech not supported in this browser.");
    return;
  }
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1;
  u.pitch = 1;
  u.volume = 1;
  synth.speak(u);
}

function stopSpeaking() {
  const synth = window.speechSynthesis;
  if (synth) synth.cancel();
}

let lastModel = null;

symptomForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  stopSpeaking();

  const text = normalize(symptomsInput.value);
  if (!text) return;

  setHidden(resultSection, true);
  setHidden(loader, false);
  analyzeBtn.disabled = true;
  symptomsInput.disabled = true;

  await wait(1100 + Math.random() * 700);

  const model = pickBestCondition(text);
  lastModel = model;

  diseaseName.textContent = model.name;
  confidencePct.textContent = String(Math.round(model.confidence * 100));
  tabletNote.textContent = model.tabletNote;
  adviceText.textContent = model.advice;
  setSeverityUI(model.severity);
  renderTablets(model.tablets);
  renderRemedies(model.remedies);

  setHidden(loader, true);
  setHidden(resultSection, false);
  analyzeBtn.disabled = false;
  symptomsInput.disabled = false;
});

resetBtn.addEventListener("click", () => {
  stopSpeaking();
  symptomsInput.value = "";
  symptomsInput.focus();
  setHidden(resultSection, true);
  setHidden(loader, true);
});

speakBtn.addEventListener("click", () => {
  if (!lastModel) return;
  speak(buildSpeakText(lastModel));
});

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

