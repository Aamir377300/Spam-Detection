import imaplib

import pytest

from app.mail import MailNotConfigured, fetch_latest


def _message(subject: str, sender: str, body: str, html: bool = False) -> bytes:
    content_type = "text/html" if html else "text/plain"
    content = f"<p>{body}</p>" if html else body
    return (
        f"From: {sender}\r\n"
        f"Subject: {subject}\r\n"
        f"Date: Mon, 9 Nov 2026 10:00:00 +0000\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"\r\n"
        f"{content}\r\n"
    ).encode()


class FakeIMAP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.readonly = None
        self.fetched = []
        self.logged_out = False
        FakeIMAP.instances.append(self)

    def login(self, user, password):
        self.user = user
        self.password = password
        return "OK", []

    def select(self, mailbox, readonly=False):
        self.mailbox = mailbox
        self.readonly = readonly
        return "OK", [b"7"]

    def search(self, charset, criteria):
        return "OK", [b"1 2 3 4 5 6 7"]

    def fetch(self, message_id, query):
        self.fetched.append((message_id, query))
        number = int(message_id)
        raw = _message(
            f"Subject {number}",
            f"Person {number} <p{number}@example.com>",
            f"<b>Hello {number}</b>" if number == 7 else f"Body {number}",
            html=number == 7,
        )
        return "OK", [(b"meta", raw)]

    def logout(self):
        self.logged_out = True
        return "BYE", []


def test_run_needs_an_app_password(monkeypatch):
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with pytest.raises(MailNotConfigured):
        fetch_latest()


def test_fetch_reads_five_newest_without_marking_seen(monkeypatch):
    FakeIMAP.instances = []
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setenv("GMAIL_ADDRESS", "auselessbuddy25@gmail.com")
    monkeypatch.setattr("app.mail.imaplib.IMAP4_SSL", FakeIMAP)

    messages = fetch_latest()

    imap = FakeIMAP.instances[0]
    assert imap.host == "imap.gmail.com"
    assert imap.user == "auselessbuddy25@gmail.com"
    assert imap.password == "abcdefghijklmnop"
    assert imap.mailbox == "INBOX"
    assert imap.readonly is True
    assert [item[0] for item in imap.fetched] == [b"7", b"6", b"5", b"4", b"3"]
    assert all(item[1] == "(BODY.PEEK[])" for item in imap.fetched)
    assert imap.logged_out is True
    assert [item["subject"] for item in messages] == [
        "Subject 7",
        "Subject 6",
        "Subject 5",
        "Subject 4",
        "Subject 3",
    ]
    assert messages[0]["body"] == "Hello 7"
    assert "9 Nov 2026" in messages[0]["date"]


def test_login_failure_does_not_include_the_password(monkeypatch):
    class RefusingIMAP(FakeIMAP):
        def login(self, user, password):
            raise imaplib.IMAP4.error(b"authentication failed")

    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret-password")
    monkeypatch.setattr("app.mail.imaplib.IMAP4_SSL", RefusingIMAP)

    with pytest.raises(Exception) as caught:
        fetch_latest()

    assert "secret-password" not in str(caught.value)
