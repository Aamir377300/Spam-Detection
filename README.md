# Inbox Guard

A small SMS spam checker built from the study notebook in `notebooks/spam_detection.ipynb`.

Paste a text and the app scores it as spam or a normal message. It also shows the word roots behind the score, flags links, phone numbers, and currency signs, and keeps a model card from a real held-out test.

The model is Multinomial Naive Bayes on TF-IDF, trained on the [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (Almeida, Hidalgo, and Yamakami, 2011).

## Run it

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python train.py
python -m app
```

Open http://127.0.0.1:8000

## Check the Gmail inbox

The Run button reads the five newest messages in `auselessbuddy25@gmail.com` and scores each one. It connects only when you press Run. The messages stay on the page until you close it, and they are not saved.

Gmail will not accept the normal account password. Create an app password, then put it in `.env`:

1. Turn on 2-Step Verification for the Google account.
2. Open https://myaccount.google.com/apppasswords and create a Mail app password.
3. Set `GMAIL_APP_PASSWORD` in `.env` to that 16-character password. `.env.example` shows the shape.
4. Restart `python -m app` and press Run.

`train.py` downloads the public SMS file, cleans it, compares three TF-IDF setups, and saves `models/spam_model.joblib`. The saved model is already in the project, so you can skip training until you want to reproduce it.

API docs: http://127.0.0.1:8000/docs

```bash
curl -s http://127.0.0.1:8000/api/check \
  -H 'content-type: application/json' \
  -d '{"text":"You won a prize. Call now."}'
```

## Tests

```bash
pytest
```

## What is in here

## Layout

```text
app/            checker, Gmail reader, and API
static/         the page
models/         saved model and the model card
notebooks/      the original study notebook
docs/           feature write-up and the Gmail to-do
tests/          automated checks
train.py        rebuild the model
```
