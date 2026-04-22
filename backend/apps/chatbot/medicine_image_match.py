from __future__ import annotations

import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MEDS_DIR = _REPO_ROOT / "frontend" / "public" / "meds"


def _normalize_stem(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(stem or "").lower())


_STEM_ALIASES: dict[str, str] = {
    "diclofenacgel": "diclofenac_gel",
    "revitalh": "revital_h",
    "deconestand": "deconestand",
    "cetrizine": "cetirizine",
    "acetaminophenpng": "acetaminophen",
    "acetaminophenpngjpeg": "acetaminophen",
}


def _stem_to_image_key(stem: str) -> str | None:
    norm = _normalize_stem(stem)
    if not norm:
        return None

    # e.g. "naproxen1" from "naproxen (1)"
    norm = re.sub(r"\d+$", "", norm)

    if norm in _STEM_ALIASES:
        return _STEM_ALIASES[norm]

    # Common direct matches
    candidates = {
        "acetaminophen",
        "paracetamol",
        "amoxicillin",
        "antacid",
        "celeheal",
        "cetirizine",
        "deconestand",
        "diclofenac_gel",
        "gepant",
        "ibuprofen",
        "loratadine",
        "meloxicam",
        "naproxen",
        "penicillin",
        "probiotic",
        "revital_h",
        "sprays",
        "tramadol",
        "triptan",
        "zincovid",
    }

    # Some stems have underscores/spaces originally; after normalization they become e.g. diclofenac_gel -> diclofenacgel
    if norm == "diclofenacgel":
        return "diclofenac_gel"
    if norm == "revitalh":
        return "revital_h"

    if norm in candidates:
        return norm

    return None


def _ahash_from_bytes(image_bytes: bytes, hash_size: int = 8) -> int | None:
    if not image_bytes:
        return None

    try:
        with Image.open(BytesIO(image_bytes)) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
            pixels = list(im.getdata())
    except Exception:
        return None

    if not pixels:
        return None

    avg = sum(pixels) / float(len(pixels))
    bits = 0
    for px in pixels:
        bits = (bits << 1) | (1 if px > avg else 0)
    return bits


def _hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@lru_cache(maxsize=1)
def _load_reference_hashes() -> list[tuple[str, int]]:
    refs: list[tuple[str, int]] = []
    if not _MEDS_DIR.exists():
        return refs

    for path in _MEDS_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue

        image_key = _stem_to_image_key(path.stem)
        if not image_key:
            continue

        try:
            data = path.read_bytes()
        except OSError:
            continue

        h = _ahash_from_bytes(data)
        if h is None:
            continue

        refs.append((image_key, h))

    return refs


def match_uploaded_medicine_image(image_bytes: bytes) -> dict | None:
    """Best-effort match of an uploaded medicine/tablet image to a known catalog image.

    Returns: { image_key, confidence, distance } or None.

    This is a simple perceptual-hash match against the reference images in `frontend/public/meds`.
    """

    uploaded_hash = _ahash_from_bytes(image_bytes)
    if uploaded_hash is None:
        return None

    refs = _load_reference_hashes()
    if not refs:
        return None

    best_key: str | None = None
    best_dist: int | None = None

    for key, ref_hash in refs:
        dist = _hamming_distance(uploaded_hash, ref_hash)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_key = key

    if best_key is None or best_dist is None:
        return None

    # 64-bit aHash: small distances are better. Keep threshold conservative.
    if best_dist > 12:
        return None

    confidence = max(0.0, min(1.0, 1.0 - (best_dist / 64.0)))
    return {"image_key": best_key, "distance": best_dist, "confidence": confidence}
