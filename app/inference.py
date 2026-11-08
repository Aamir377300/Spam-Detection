"""Score one message with the saved TF-IDF + Naive Bayes model."""

from __future__ import annotations

import json
from pathlib import Path

import joblib

from app.preprocess import find_cues, transform_text

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "spam_model.joblib"
CARD_PATH = ROOT / "models" / "card.json"

UNSURE_LOW = 0.42
UNSURE_HIGH = 0.58

BUNDLE: dict | None = None
CARD: dict | None = None


class ModelNotReady(RuntimeError):
    pass


def load_artifacts() -> None:
    global BUNDLE, CARD
    if not MODEL_PATH.exists() or not CARD_PATH.exists():
        BUNDLE = None
        CARD = None
        return
    BUNDLE = joblib.load(MODEL_PATH)
    CARD = json.loads(CARD_PATH.read_text(encoding="utf-8"))


def score_message(text: str) -> dict:
    if BUNDLE is None or CARD is None:
        raise ModelNotReady(
            "The model is not trained yet. From the project folder, run: python train.py"
        )

    vectorizer = BUNDLE["vectorizer"]
    model = BUNDLE["model"]
    cleaned = transform_text(text)
    probabilities = model.predict_proba(vectorizer.transform([cleaned]))[0]
    classes = list(model.classes_)
    spam_probability = float(probabilities[classes.index(1)])

    if not cleaned:
        verdict = "unsure"
    elif UNSURE_LOW <= spam_probability <= UNSURE_HIGH:
        verdict = "unsure"
    elif spam_probability > 0.5:
        verdict = "spam"
    else:
        verdict = "ham"

    signals, caption = _signals(cleaned, vectorizer, model, verdict)
    return {
        "text": text,
        "verdict": verdict,
        "title": _title(verdict),
        "spam_probability": round(spam_probability, 4),
        "summary": _summary(verdict, cleaned),
        "signal_caption": caption,
        "signals": signals,
        "cues": find_cues(text),
        "cleaned_text": cleaned,
        "length_note": _length_note(text, CARD),
        "chars": len(text),
    }


def _title(verdict: str) -> str:
    return {
        "spam": "Likely spam",
        "ham": "Looks normal",
        "unsure": "Not sure",
    }[verdict]


def _summary(verdict: str, cleaned: str) -> str:
    if not cleaned:
        return "After cleaning, no real words were left. Try a fuller message."
    if verdict == "unsure":
        return "This sits near the middle. Read it yourself before you tap a link or reply."
    if verdict == "spam":
        return "This looks like spam. The chips below are the word roots that pushed the score up."
    return "This looks like a normal message. The chips below are the word roots behind that score."


def _length_note(text: str, card: dict) -> str:
    chars = len(text)
    words = len(text.split())
    ham = card["length"]["ham_median_chars"]
    spam = card["length"]["spam_median_chars"]
    return (
        f"This message is {chars} characters and {words} words. "
        "The model scores words. Length is only context. "
        f"In this dataset, spam texts have a median of {spam} characters, "
        f"and normal texts have a median of {ham}."
    )


def _signals(cleaned: str, vectorizer, model, verdict: str) -> tuple[list[dict], str]:
    if not cleaned:
        return [], ""

    row = vectorizer.transform([cleaned]).tocsr()
    if row.nnz == 0:
        return [], ""

    names = vectorizer.get_feature_names_out()
    classes = list(model.classes_)
    spam_log = model.feature_log_prob_[classes.index(1)]
    ham_log = model.feature_log_prob_[classes.index(0)]

    # Positive means the term is more typical of spam than of normal texts.
    weighted = []
    for index, weight in zip(row.indices, row.data):
        lean = float(spam_log[index] - ham_log[index])
        weighted.append((str(names[index]), lean * float(weight), lean))

    if verdict == "spam":
        chosen = [item for item in weighted if item[1] > 0]
        chosen.sort(key=lambda item: item[1], reverse=True)
        caption = "Roots that lean spam"
    elif verdict == "ham":
        chosen = [item for item in weighted if item[1] < 0]
        chosen.sort(key=lambda item: item[1])
        caption = "Roots that lean normal"
    else:
        chosen = []
        caption = "Strongest word roots"

    if not chosen:
        chosen = sorted(weighted, key=lambda item: abs(item[1]), reverse=True)
        caption = "Strongest word roots"

    chosen = chosen[:5]
    strongest = max(abs(item[1]) for item in chosen) or 1.0
    signals = [
        {
            "term": term,
            "strength": round(abs(score) / strongest, 2),
            "leans": "spam" if lean > 0 else "ham",
        }
        for term, score, lean in chosen
    ]
    return signals, caption
