"""Clean an SMS the same way the study notebook did.

Lowercase, keep letters and numbers, drop common words, then Porter-stem.
Link, phone, and currency cues stay outside the model: cleaning destroys them.
"""

from __future__ import annotations

import re
from pathlib import Path

from nltk.stem.porter import PorterStemmer

_STOPWORDS = frozenset(
    Path(__file__).with_name("stopwords.txt").read_text(encoding="utf-8").split()
)
_STEMMER = PorterStemmer()
_TOKENS = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_PHONE = re.compile(r"\+?\d[\d\-\s().]{8,}\d")
_LINK = re.compile(
    r"https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|info|biz|ly|io|co\.uk)\b",
    re.IGNORECASE,
)
_MONEY = re.compile(r"[$£€]")


def transform_text(text: str) -> str:
    kept = []
    for token in _TOKENS.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        kept.append(_STEMMER.stem(token))
    return " ".join(kept)


def find_cues(text: str) -> list[str]:
    cues: list[str] = []
    if _LINK.search(text):
        cues.append("Link")
    if _has_phone(text):
        cues.append("Phone number")
    if _MONEY.search(text):
        cues.append("Money")
    return cues


def _has_phone(text: str) -> bool:
    for match in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if len(digits) >= 10:
            return True
    return False
