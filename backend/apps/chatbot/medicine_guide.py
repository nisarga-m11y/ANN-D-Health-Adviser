from __future__ import annotations


def get_food_timing_for_image_key(image_key: str) -> str:
    key = str(image_key or "").strip().lower()
    if not key:
        return ""

    timing = FOOD_TIMING_BY_IMAGE_KEY.get(key)
    return str(timing or "").strip()


FOOD_TIMING_BY_IMAGE_KEY: dict[str, str] = {
    "paracetamol": "Can be taken with or without food. If it causes stomach upset, take after food. Follow the label/prescription.",
    "acetaminophen": "Can be taken with or without food. If it causes stomach upset, take after food. Follow the label/prescription.",

    "cetirizine": "Can be taken with or without food. It may cause drowsiness in some people—many take it at night. Follow the label/prescription.",
    "loratadine": "Can be taken with or without food. Follow the label/prescription.",

    "ibuprofen": "Commonly taken with/after food to reduce stomach irritation. Follow the label/prescription.",
    "naproxen": "Commonly taken with/after food to reduce stomach irritation. Follow the label/prescription.",
    "meloxicam": "Prescription NSAID: commonly taken with food to reduce stomach irritation. Follow the prescription.",
    "dolokind_plus": "Pain medicine combination: commonly taken after food to reduce stomach irritation. Follow the prescription.",
    "celeheal": "Pain medicine: commonly taken after food to reduce stomach irritation. Follow the label/prescription.",

    "antacid": "Timing depends on the antacid type. Many are taken after meals and/or at bedtime. Follow the label or pharmacist advice.",
    "probiotic": "Often taken after food (varies by brand). Follow the label/prescription.",
    "ors": "Not a tablet. Sip frequently as per packet instructions. If severe dehydration, seek medical care.",

    "diclofenac_gel": "Topical gel (apply on skin). Food timing is not applicable.",

    "amoxicillin": "Prescription antibiotic: take exactly as prescribed. Food timing depends on the specific instructions on the label.",
    "penicillin": "Prescription antibiotic: take exactly as prescribed. Food timing depends on the specific instructions on the label.",

    "tramadol": "Prescription-only pain medicine: take exactly as prescribed. Food timing depends on the prescription.",
    "triptan": "Prescription migraine medicine: take exactly as prescribed. Food timing depends on the prescription.",
    "gepant": "Prescription migraine medicine: take exactly as prescribed. Food timing depends on the prescription.",

    "revital_h": "Supplement: typically taken after food (varies by brand). Follow the label.",
    "zincovid": "Supplement: typically taken after food (varies by brand). Follow the label.",
    "deconestand": "Cold/flu medicine: follow the label/prescription. If it upsets the stomach, many take it after food.",
    "sprays": "Spray medicine: food timing is not applicable. Use as directed on the label.",
}


def build_medicine_safety_note(extra: str = "") -> str:
    base = "For reference only. Consult a doctor/pharmacist."
    extra = str(extra or "").strip()
    if not extra:
        return base
    if "consult" in extra.lower():
        return extra
    return (extra + " " + base).strip()
