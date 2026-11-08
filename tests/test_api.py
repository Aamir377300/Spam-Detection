import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        ready = test_client.get("/api/health").json()["model_ready"]
        if not ready:
            pytest.skip("Run python train.py first")
        yield test_client


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Inbox Guard" in response.text
    assert "/static/app.js" in response.text


def test_stats_are_from_a_held_out_split(client):
    body = client.get("/api/stats").json()
    assert body["metrics"]["precision"] > 0.9
    assert body["split"]["stratified"] is True
    assert body["test_size"] > 0
    assert len(body["metrics"]["confusion_matrix"]) == 2


def test_obvious_spam_and_ham(client):
    spam = client.post(
        "/api/check",
        json={
            "text": "WINNER!! You have won a $1000 prize. Call 09061701461 to claim now. Reply STOP to end."
        },
    )
    assert spam.status_code == 200
    spam_body = spam.json()
    assert spam_body["verdict"] == "spam"
    assert spam_body["spam_probability"] > 0.8
    assert "Phone number" in spam_body["cues"]
    assert "Money" in spam_body["cues"]
    assert spam_body["signals"]

    ham = client.post(
        "/api/check",
        json={"text": "Hey, are we still meeting at the library around 6?"},
    )
    assert ham.status_code == 200
    ham_body = ham.json()
    assert ham_body["spam_probability"] < 0.5
    assert ham_body["verdict"] == "ham"


def test_blank_and_batch_limits(client):
    blank = client.post("/api/check", json={"text": "   "})
    assert blank.status_code == 400

    skipped = client.post(
        "/api/check-batch",
        json={"texts": ["  ", "Can you send me the class notes from today?"]},
    )
    assert skipped.status_code == 200
    assert len(skipped.json()["results"]) == 1

    too_many = client.post("/api/check-batch", json={"texts": ["hello"] * 26})
    assert too_many.status_code == 400


def test_inbox_run_scores_the_fetched_messages(client, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "auselessbuddy25@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "")
    status = client.get("/api/inbox")
    assert status.status_code == 200
    assert status.json()["address"] == "auselessbuddy25@gmail.com"
    assert status.json()["configured"] is False

    monkeypatch.setattr(
        "app.main.fetch_latest",
        lambda: [
            {
                "sender": "Sam <sam@example.com>",
                "subject": "Library",
                "date": "9 Nov 2026, 18:00",
                "body": "Hey, are we still meeting at the library around 6?",
            },
            {
                "sender": "Prize <prize@example.com>",
                "subject": "Winner",
                "date": "9 Nov 2026, 18:01",
                "body": "WINNER!! You have won a $1000 prize. Call 09061701461 to claim now.",
            },
        ],
    )
    response = client.post("/api/inbox/run")
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert [item["verdict"] for item in messages] == ["ham", "spam"]
    assert "library" in messages[0]["preview"]
    assert messages[1]["spam_probability"] > 0.8


def test_symbols_only_are_unsure(client):
    response = client.post("/api/check", json={"text": "?!?!?"})
    assert response.status_code == 200
    assert response.json()["verdict"] == "unsure"
    assert response.json()["cleaned_text"] == ""
