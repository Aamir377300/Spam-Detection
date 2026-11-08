"""Train the Inbox Guard model and write models/spam_model.joblib.

The study notebook settled on TF-IDF + Multinomial Naive Bayes because the
dataset is imbalanced and precision matters. This script keeps that model,
tries three small TF-IDF setups on one stratified split, and saves the one
with the best spam precision.

The vectorizer is fit on training messages only.
"""

from __future__ import annotations

import json
import ssl
import statistics
import urllib.request
from datetime import date
from pathlib import Path

import certifi

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

from app.preprocess import transform_text

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "sms.tsv"
MODEL_PATH = ROOT / "models" / "spam_model.joblib"
CARD_PATH = ROOT / "models" / "card.json"

DATA_URLS = (
    "https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv",
    "https://cdn.jsdelivr.net/gh/justmarkham/pycon-2016-tutorial@master/data/sms.tsv",
)

CONFIGS = (
    {"name": "Single words", "params": {"ngram_range": (1, 1)}},
    {"name": "Single words, top 3,000", "params": {"ngram_range": (1, 1), "max_features": 3000}},
    {
        "name": "Words and pairs, top 3,000",
        "params": {"ngram_range": (1, 2), "max_features": 3000},
    },
)


def main() -> None:
    rows = _load_rows(_download())
    if len(rows) < 5000:
        raise SystemExit(f"Expected thousands of messages, found {len(rows)}.")

    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, text in rows:
        if text in seen:
            continue
        seen.add(text)
        unique.append((label, text))

    labels = [0 if label == "ham" else 1 for label, _ in unique]
    cleaned = [transform_text(text) for _, text in unique]
    ham_chars = [len(text) for label, text in unique if label == "ham"]
    spam_chars = [len(text) for label, text in unique if label == "spam"]

    x_train, x_test, y_train, y_test = train_test_split(
        cleaned,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    search = []
    best_key = None
    best_bundle = None
    best_record = None

    for config in CONFIGS:
        vectorizer = TfidfVectorizer(lowercase=False, **config["params"])
        model = MultinomialNB()
        metrics = _fit_and_score(vectorizer, model, x_train, x_test, y_train, y_test)
        record = {"name": config["name"], "selected": False, **metrics}
        search.append(record)
        key = (metrics["precision"], metrics["f1"], metrics["recall"])
        if best_key is None or key > best_key:
            best_key = key
            best_bundle = (vectorizer, model, config)
            best_record = record

    assert best_bundle is not None and best_record is not None
    best_record["selected"] = True
    vectorizer, model, config = best_bundle
    if list(model.classes_) != [0, 1]:
        raise SystemExit(f"Unexpected classes: {list(model.classes_)}")

    spam_count = sum(labels)
    ham_count = len(labels) - spam_count
    card = {
        "app": "Inbox Guard",
        "model_name": "Multinomial Naive Bayes",
        "dataset": "UCI SMS Spam Collection",
        "dataset_url": "https://archive.ics.uci.edu/dataset/228/sms+spam+collection",
        "citation": "Almeida, Hidalgo, and Yamakami, 2011",
        "rows_raw": len(rows),
        "rows_clean": len(unique),
        "ham_count": ham_count,
        "spam_count": spam_count,
        "spam_share": round(spam_count / len(unique), 4),
        "train_size": len(y_train),
        "test_size": len(y_test),
        "split": {"test_size": 0.2, "random_state": 42, "stratified": True},
        "selection_rule": "Highest spam precision, then F1, then recall.",
        "vectorizer": {
            "name": config["name"],
            "lowercase": False,
            "ngram_range": list(config["params"]["ngram_range"]),
            "max_features": config["params"].get("max_features"),
            "n_features": int(len(vectorizer.get_feature_names_out())),
        },
        "metrics": {
            "accuracy": best_record["accuracy"],
            "precision": best_record["precision"],
            "recall": best_record["recall"],
            "f1": best_record["f1"],
            "confusion_matrix": best_record["confusion_matrix"],
            "positive_class": "spam",
        },
        "length": {
            "ham_median_chars": int(statistics.median(ham_chars)),
            "spam_median_chars": int(statistics.median(spam_chars)),
        },
        "search": search,
        "sklearn_version": sklearn.__version__,
        "trained_at": date.today().isoformat(),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    _print_report(card)


def _download() -> Path:
    if DATA_PATH.exists() and DATA_PATH.stat().st_size > 0:
        print(f"Using {DATA_PATH}")
        return DATA_PATH

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for url in DATA_URLS:
        try:
            print(f"Downloading {url}")
            request = urllib.request.Request(url, headers={"User-Agent": "inbox-guard-train"})
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(request, timeout=60, context=context) as response:
                DATA_PATH.write_bytes(response.read())
            return DATA_PATH
        except Exception as exc:  # noqa: BLE001 - try the next public mirror
            last_error = exc
            print(f"Download failed: {exc}")
    raise SystemExit(f"Could not download the SMS dataset. Last error: {last_error}")


def _load_rows(path: Path) -> list[tuple[str, str]]:
    raw = path.read_bytes()
    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_data = raw.decode("latin-1")

    rows: list[tuple[str, str]] = []
    for line in text_data.splitlines():
        label, separator, text = line.partition("\t")
        label = label.strip().lower()
        text = text.strip()
        if separator and label in {"ham", "spam"} and text:
            rows.append((label, text))
    return rows


def _fit_and_score(vectorizer, model, x_train, x_test, y_train, y_test) -> dict:
    model.fit(vectorizer.fit_transform(x_train), y_train)
    predicted = model.predict(vectorizer.transform(x_test))
    matrix = confusion_matrix(y_test, predicted, labels=[0, 1])
    return {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 6),
        "precision": round(float(precision_score(y_test, predicted, pos_label=1, zero_division=0)), 6),
        "recall": round(float(recall_score(y_test, predicted, pos_label=1, zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, predicted, pos_label=1, zero_division=0)), 6),
        "confusion_matrix": [[int(value) for value in row] for row in matrix],
    }


def _print_report(card: dict) -> None:
    print()
    print(f"{'Setup':<28} {'Precision':>10} {'Recall':>8} {'F1':>8} {'Accuracy':>10}")
    for row in card["search"]:
        mark = "*" if row["selected"] else " "
        print(
            f"{mark} {row['name']:<26} {row['precision']:>10.3f} "
            f"{row['recall']:>8.3f} {row['f1']:>8.3f} {row['accuracy']:>10.3f}"
        )
    print()
    print(f"Saved {MODEL_PATH}")
    print("Start the app with: python -m app")
    print("Then open http://127.0.0.1:8000")


if __name__ == "__main__":
    main()
