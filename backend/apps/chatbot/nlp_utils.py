import re
from typing import List

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


_NLTK_READY = False


def _ensure_nltk_resources():
    global _NLTK_READY
    if _NLTK_READY:
        return

    for resource, locator in [
        ("punkt", "tokenizers/punkt"),
        ("punkt_tab", "tokenizers/punkt_tab"),
        ("stopwords", "corpora/stopwords"),
    ]:
        try:
            nltk.data.find(locator)
        except LookupError:
            nltk.download(resource, quiet=True)

    _NLTK_READY = True


def preprocess_text(text: str) -> str:
    _ensure_nltk_resources()

    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens: List[str] = word_tokenize(text)
    stop_words = set(stopwords.words("english"))
    filtered = [token for token in tokens if token not in stop_words and len(token) > 2]
    return " ".join(filtered)
