"""HTTP API and the static Inbox Guard page."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import __version__
from app import inference
from app.inference import ModelNotReady, load_artifacts, score_message
from app.mail import MailError, MailNotConfigured, account, configured, fetch_latest, load_env

STATIC = Path(__file__).resolve().parents[1] / "static"
MAX_CHARS = 2000
MAX_BATCH = 25


class CheckIn(BaseModel):
    text: str


class Signal(BaseModel):
    term: str
    strength: float
    leans: str


class CheckOut(BaseModel):
    text: str
    verdict: str
    title: str
    spam_probability: float
    summary: str
    signal_caption: str
    signals: list[Signal]
    cues: list[str]
    cleaned_text: str
    length_note: str
    chars: int


class BatchIn(BaseModel):
    texts: list[str] = Field(default_factory=list)


class BatchOut(BaseModel):
    results: list[CheckOut]


class MailItem(BaseModel):
    sender: str
    subject: str
    date: str
    preview: str
    verdict: str
    title: str
    spam_probability: float


class MailRunOut(BaseModel):
    address: str
    messages: list[MailItem]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_env()
    load_artifacts()
    yield


app = FastAPI(
    title="Inbox Guard",
    version=__version__,
    summary="Score an SMS as spam or a normal message.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model_ready": inference.CARD is not None}


@app.get("/api/stats")
def stats() -> dict:
    if inference.CARD is None:
        raise HTTPException(
            status_code=503,
            detail="The model is not trained yet. From the project folder, run: python train.py",
        )
    return inference.CARD


@app.post("/api/check", response_model=CheckOut)
def check(body: CheckIn) -> dict:
    return _score(prepare_text(body.text))


@app.post("/api/check-batch", response_model=BatchOut)
def check_batch(body: BatchIn) -> dict:
    texts = [item.strip() for item in body.texts if item and item.strip()]
    if not texts:
        raise HTTPException(status_code=400, detail="Add at least one message.")
    if len(texts) > MAX_BATCH:
        raise HTTPException(status_code=400, detail="Check up to 25 messages at a time.")
    for text in texts:
        if len(text) > MAX_CHARS:
            raise HTTPException(status_code=400, detail="Each message must be under 2,000 characters.")
    return {"results": [_score(text) for text in texts]}


def prepare_text(text: str) -> str:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Paste a message first.")
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=400, detail="Keep the message under 2,000 characters.")
    return text


@app.get("/api/inbox")
def inbox_status() -> dict:
    return {"address": account(), "configured": configured()}


@app.post("/api/inbox/run", response_model=MailRunOut)
def run_inbox() -> dict:
    try:
        fetched = fetch_latest()
    except MailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    messages = [_mail_item(item) for item in fetched]
    return {"address": account(), "messages": messages}


def _mail_item(item: dict) -> dict:
    text = f"{item['subject']}\n{item['body']}".strip()
    if text in {"", "(no subject)"}:
        scored = {
            "verdict": "unsure",
            "title": "Not sure",
            "spam_probability": 0.0,
        }
    else:
        scored = _score(text[:MAX_CHARS])
    preview = " ".join(item["body"].split())
    if len(preview) > 220:
        preview = preview[:219].rstrip() + "…"
    return {
        "sender": item["sender"],
        "subject": item["subject"],
        "date": item["date"],
        "preview": preview,
        "verdict": scored["verdict"],
        "title": scored["title"],
        "spam_probability": scored["spam_probability"],
    }


def _score(text: str) -> dict:
    try:
        return score_message(text)
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
