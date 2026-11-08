# Inbox Guard features

Inbox Guard is a small spam checker built from the study notebook in `notebooks/spam_detection.ipynb`. You paste a text, or press Run for the connected Gmail account, and the app says whether it looks like spam.

The model is Multinomial Naive Bayes on TF-IDF. It was trained on the [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (Almeida, Hidalgo, and Yamakami, 2011).

## Check one message

The main box takes one text.

- **Check message** scores it. Ctrl or ⌘ + Enter does the same thing.
- The result is one of three labels: **Likely spam**, **Looks normal**, or **Not sure**.
- A score near the middle stays **Not sure**, so a coin-flip is not shown as a firm label.
- The big number is the spam score, from 0% to 100%.
- The bar underneath runs from Normal to Spam.
- **Clear** empties the box and hides the result.
- A blank message, or one over 2,000 characters, is rejected with a short error.
- A message that is only symbols, such as `?!?!?`, comes back **Not sure** because cleaning leaves no words.

## Why the score moved

Under the label, the app shows the word roots that pushed the score.

- Spam results list roots that lean spam, such as `prize` or `claim`.
- Normal results list roots that lean normal.
- An unsure result lists the strongest roots.
- Each chip has a small bar. A longer bar means that root mattered more in this message.
- **Under the hood** shows the cleaned text the model actually read.
- The same panel says how long the message is. Length is context. The model scores words. In this dataset, spam texts have a median of 148 characters and normal texts have a median of 53.

Cleaning is the same idea as the notebook:

1. Lowercase the text and keep letters and numbers.
2. Drop common words such as "the" and "you".
3. Stem what is left, so "loved" and "loving" both become "love".
4. Turn those roots into TF-IDF weights.
5. Add the weights with Multinomial Naive Bayes.

## Extra cues

Links, phone numbers, and currency signs are flagged beside the model score.

- **Link** catches `http`, `www`, and common web addresses.
- **Phone number** catches numbers with at least 10 digits.
- **Money** catches `$`, `£`, and `€`.

These stay outside the model because cleaning strips symbols and splits numbers, so a word model misses them easily. They do not override the score. They sit next to it.

## Try a message

Six examples sit under the checker. The dot is red for a spam-style example and green for a normal one.

| Example | Kind |
|---|---|
| Prize text | Spam-style prize SMS |
| Prize link | Spam-style prize with a link and a dollar amount |
| Contest | Spam-style competition text |
| Dinner plan | Normal plan |
| Class notes | Normal request |
| On the way | Normal errand |

Clicking one fills the box and checks it.

## Check a list

The **A list** tab checks several messages at once.

- Put one message on each line.
- **Load a sample inbox** fills the six examples and checks them.
- The heading says how many look like spam, for example "3 of 6 look like spam."
- Each row shows the label, the spam score, the message, any link / phone / money cues, and up to three word roots.
- Empty lines are skipped.
- The limit is 25 messages, and each one must be under 2,000 characters.

## Recent checks

Messages you type and check are kept in this browser only, under recent checks.

- The list holds the latest eight.
- Each row shows the text and the spam score.
- Click a row to load that text and check it again.
- **Clear** removes the list.
- List-mode checks and Gmail checks are not added here.

## Model card

The card on the page is filled from the saved test, not from typed-in numbers.

Current saved result, from `models/card.json`:

| | |
|---|---|
| Messages in the file | 5,574 |
| After dropping duplicate texts | 5,160 |
| Normal messages | 4,518 |
| Spam messages | 642 |
| Training messages | 4,128 |
| Held-out test messages | 1,032 |
| Spam precision | 99.0% |
| Accuracy | 97.6% |
| Spam recall | 81.3% |
| Spam F1 | 89.3% |

Confusion matrix on that held-out test:

|  | Predicted normal | Predicted spam |
|---|---:|---:|
| Actual normal | 903 | 1 |
| Actual spam | 24 | 104 |

Precision is the headline because normal messages are the majority. It is the share of spam flags that were truly spam.

**Why this setup** shows the three TF-IDF options trained on the same split. The winner was words and word pairs, top 3,000 terms, chosen for the highest spam precision, then F1, then recall.

| Setup | Precision | Recall | F1 |
|---|---:|---:|---:|
| Single words | 98.9% | 67.2% | 80.0% |
| Single words, top 3,000 | 99.0% | 76.6% | 86.3% |
| Words and pairs, top 3,000 | 99.0% | 81.3% | 89.3% |

The vectorizer is fit on the training messages only. The numbers above are from the messages it did not train on. `python train.py` rebuilds the model and refreshes this card.

## How a message becomes a score

The bottom of the page walks through the four steps: Clean, Stem, Weigh, Score.

The study notebook compared several classifiers. This app uses Multinomial Naive Bayes on TF-IDF, the setup that favored precision when spam is the rare class.

## Gmail Run button

This part is started, and the live login is still to be finished. See `TO-BE-CONTINUED.md`.

What the page already does:

- Shows **Latest mail** for `auselessbuddy25@gmail.com`.
- **Run** is the only time it tries to read mail.
- It asks for the five newest inbox messages.
- Each one would be labeled with the same checker.
- Results stay on the page and disappear when the page is closed.
- Without `GMAIL_APP_PASSWORD` in `.env`, Run explains that Gmail needs an app password.

## API

With the app running, the docs are at http://127.0.0.1:8000/docs.

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Says whether the model is loaded |
| GET | `/api/stats` | Returns the model card |
| POST | `/api/check` | Scores one text: `{"text": "..."}` |
| POST | `/api/check-batch` | Scores a list: `{"texts": ["...", "..."]}` |
| GET | `/api/inbox` | Says which Gmail account is set, and whether an app password is present |
| POST | `/api/inbox/run` | Reads and scores the five newest inbox messages |

Example:

```bash
curl -s http://127.0.0.1:8000/api/check \
  -H 'content-type: application/json' \
  -d '{"text":"You won a prize. Call now."}'
```

## Tests

`pytest` covers the cleaner, the cues, obvious spam and normal messages, blank input, the batch limit, the model card, and the Gmail fetch path with a fake inbox so the tests do not log in to Google.

## Project files

| Path | Role |
|---|---|
| `Spam-Detection/spam_detection.ipynb` | The original study notebook |
| `train.py` | Downloads the dataset, trains the model, writes the model card |
| `app/` | The checker, the Gmail reader, and the API |
| `static/` | The page |
| `models/spam_model.joblib` | The saved model |
| `models/card.json` | The numbers shown on the model card |
| `tests/` | The automated checks |
| `.env.example` | Where the Gmail address and app password go |
