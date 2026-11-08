"""Read the five newest Gmail messages when Run is pressed.

The connection opens for that request and closes. Message text is not written
to disk.
"""

from __future__ import annotations

import email
import imaplib
import os
import re
from email.header import decode_header
from email.message import Message
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
GMAIL_HOST = "imap.gmail.com"
DEFAULT_ADDRESS = "auselessbuddy25@gmail.com"
LATEST_COUNT = 5

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?is)<(script|style).*?>.*?</\1>")
_SPACE = re.compile(r"\s+")


class MailNotConfigured(Exception):
    """The Gmail app password has not been set."""


class MailError(Exception):
    """Gmail could not be read for this Run."""


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def account() -> str:
    configured = os.environ.get("GMAIL_ADDRESS", "").strip()
    return configured or DEFAULT_ADDRESS


def app_password() -> str:
    return os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()


def configured() -> bool:
    return bool(app_password())


def fetch_latest(limit: int = LATEST_COUNT) -> list[dict]:
    password = app_password()
    if not password:
        raise MailNotConfigured(
            "Add a Gmail app password to the .env file as GMAIL_APP_PASSWORD, then restart the app. "
            "Gmail will not accept the normal account password."
        )

    try:
        imap = imaplib.IMAP4_SSL(GMAIL_HOST, 993, timeout=20)
    except OSError as exc:
        raise MailError("Could not reach Gmail. Check the network and press Run again.") from exc

    try:
        try:
            imap.login(account(), password)
        except imaplib.IMAP4.error as exc:
            raise MailError(
                f"Gmail refused the login for {account()}. "
                "Use a 16-character app password from the Google account, with IMAP enabled."
            ) from exc

        status, _ = imap.select("INBOX", readonly=True)
        if status != "OK":
            raise MailError("Could not open the inbox.")

        status, data = imap.search(None, "ALL")
        if status != "OK":
            raise MailError("Could not list the inbox.")
        message_ids = data[0].split() if data and data[0] else []
        chosen = message_ids[-limit:]

        messages = []
        for message_id in reversed(chosen):
            status, fetched = imap.fetch(message_id, "(BODY.PEEK[])")
            if status != "OK":
                continue
            raw = _raw_message(fetched)
            if not raw:
                continue
            messages.append(_parse_message(raw))
        return messages
    finally:
        try:
            imap.logout()
        except Exception:
            try:
                imap.shutdown()
            except Exception:
                pass


def _raw_message(fetched) -> bytes:
    for item in fetched or []:
        if isinstance(item, tuple):
            for piece in item:
                if isinstance(piece, bytes) and b"\r\n" in piece:
                    return piece
    return b""


def _parse_message(raw: bytes) -> dict:
    message = email.message_from_bytes(raw)
    subject = _header(message.get("Subject")) or "(no subject)"
    sender = _header(message.get("From")) or "(unknown sender)"
    sent_at = _format_date(_header(message.get("Date")))
    body = _body_text(message)
    return {
        "sender": sender,
        "subject": subject,
        "date": sent_at,
        "body": body[:5000],
    }


def _header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts).strip()


def _format_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return value
    if parsed is None:
        return value
    return f"{parsed.day} {parsed.strftime('%b %Y, %H:%M')}"


def _body_text(message: Message) -> str:
    if message.is_multipart():
        plain = _first_part(message, "text/plain")
        if plain:
            return _SPACE.sub(" ", plain).strip()
        html = _first_part(message, "text/html")
        return _strip_html(html) if html else ""
    content = _decode_part(message)
    if message.get_content_type() == "text/html":
        return _strip_html(content)
    return _SPACE.sub(" ", content).strip()


def _first_part(message: Message, content_type: str) -> str:
    for part in message.walk():
        if part.get_content_type() != content_type:
            continue
        disposition = (part.get("Content-Disposition") or "").lower()
        if "attachment" in disposition:
            continue
        return _decode_part(part) if content_type == "text/plain" else _decode_part(part)
    return ""


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        text = part.get_payload()
        return text if isinstance(text, str) else ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _strip_html(value: str) -> str:
    text = _BLOCK.sub(" ", value)
    text = _TAG.sub(" ", text)
    return _SPACE.sub(" ", unescape(text)).strip()
