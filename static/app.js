const EXAMPLES = [
  {
    label: "Prize text",
    tone: "spam",
    text: "URGENT! You have won a FREE prize. Call 09061701461 now to claim. Reply STOP to end. Valid 12 hours only.",
  },
  {
    label: "Prize link",
    tone: "spam",
    text: "Winner! Claim your $500 reward at http://prize-claim.com before midnight.",
  },
  {
    label: "Contest",
    tone: "spam",
    text: "Free entry in a weekly competition to win FA Cup final tickets. Text WIN to 87121 to enter. Txt stop to opt out.",
  },
  {
    label: "Dinner plan",
    tone: "ham",
    text: "Hey, are we still on for dinner at 7? I can grab a table if you are running late.",
  },
  {
    label: "Class notes",
    tone: "ham",
    text: "Can you send me the notes from today's class? I missed the last twenty minutes.",
  },
  {
    label: "On the way",
    tone: "ham",
    text: "I'll be home in 20 minutes. Do you need anything from the store?",
  },
];

const HISTORY_KEY = "inbox-guard.history.v1";

const message = document.querySelector("#message");
const charCount = document.querySelector("#char-count");
const checkBtn = document.querySelector("#check-btn");
const clearBtn = document.querySelector("#clear-btn");
const sampleBtn = document.querySelector("#sample-inbox");
const formError = document.querySelector("#form-error");
const result = document.querySelector("#result");
const form = document.querySelector("#checker");
const examples = document.querySelector("#examples");
const historyEl = document.querySelector("#history");
const clearHistoryBtn = document.querySelector("#clear-history");
const modelCard = document.querySelector("#model-card");
const banner = document.querySelector("#banner");
const statusPill = document.querySelector("#status-pill");
const messageLabel = document.querySelector("#message-label");
const modeOne = document.querySelector("#mode-one");
const modeList = document.querySelector("#mode-list");

let mode = "one";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function h(tag, attrs, children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  });
  (children || []).forEach((child) => {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  });
  return node;
}

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function metric(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function num(value) {
  return new Intl.NumberFormat().format(value);
}

async function api(path, options) {
  let response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Can't reach the app server. Start it with python -m app, then refresh.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const text = typeof detail === "string" ? detail : "The check failed. Try again.";
    throw new Error(text);
  }
  return data;
}

function showError(text) {
  formError.hidden = false;
  formError.textContent = text;
}

function clearError() {
  formError.hidden = true;
  formError.textContent = "";
}

function hideResult() {
  result.hidden = true;
  result.replaceChildren();
  result.className = "";
}

function setMode(next) {
  mode = next;
  const list = next === "list";
  modeOne.setAttribute("aria-selected", String(!list));
  modeList.setAttribute("aria-selected", String(list));
  sampleBtn.hidden = !list;
  messageLabel.textContent = list ? "Messages, one per line" : "Message";
  message.placeholder = list ? "Paste one message per line…" : "Paste a text message…";
  checkBtn.textContent = list ? "Check list" : "Check message";
  updateCount();
  hideResult();
  clearError();
}

function updateCount() {
  if (mode === "list") {
    const count = message.value.split("\n").map((line) => line.trim()).filter(Boolean).length;
    charCount.textContent = count === 1 ? "1 message" : `${count} messages`;
    return;
  }
  charCount.textContent = `${message.value.length} / 2000`;
}

function readHistory() {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
  } catch {
    return [];
  }
}

function writeHistory(items) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 8)));
  renderHistory();
}

function remember(item) {
  const items = readHistory().filter((saved) => saved.text !== item.text);
  items.unshift({
    text: item.text,
    title: item.title,
    verdict: item.verdict,
    spam_probability: item.spam_probability,
  });
  writeHistory(items);
}

function renderHistory() {
  const items = readHistory();
  historyEl.replaceChildren();
  if (!items.length) {
    historyEl.append(h("p", { class: "empty" }, ["Messages you check show up here, on this browser only."]));
    return;
  }
  items.forEach((item) => {
    const button = h("button", { type: "button", class: "history-item" }, [
      h("span", {}, [item.text]),
      h("span", { class: `tag ${item.verdict}` }, [pct(item.spam_probability)]),
    ]);
    button.addEventListener("click", () => {
      setMode("one");
      message.value = item.text;
      updateCount();
      checkCurrent();
    });
    historyEl.append(button);
  });
}

function renderExamples() {
  EXAMPLES.forEach((example) => {
    const button = h("button", { type: "button" }, [
      h("i", { class: `dot ${example.tone}`, "aria-hidden": "true" }),
      example.label,
    ]);
    button.addEventListener("click", () => {
      setMode("one");
      message.value = example.text;
      updateCount();
      checkCurrent();
    });
    examples.append(button);
  });
}

function chip(signal) {
  const bar = h("i", {});
  bar.style.width = `${Math.max(12, Math.round(signal.strength * 100))}%`;
  return h("span", { class: `chip ${signal.leans}` }, [signal.term, h("b", {}, [bar])]);
}

function animateMeter(fill, probability) {
  const apply = () => {
    fill.style.transition = reduceMotion ? "none" : "width 420ms ease";
    fill.style.width = `${probability * 100}%`;
  };
  window.requestAnimationFrame(() => window.requestAnimationFrame(apply));
}

function renderSingle(item) {
  result.hidden = false;
  result.className = `result ${item.verdict}`;
  const meter = h("i", {});
  const bits = [
    h("div", { class: "result-top" }, [
      h("h3", { class: "verdict" }, [item.title]),
      h("p", { class: "score" }, [pct(item.spam_probability), h("small", {}, ["spam score"])]),
    ]),
    h("p", { class: "summary" }, [item.summary]),
    h("div", { class: "meter", role: "img", "aria-label": `Spam score ${pct(item.spam_probability)}` }, [meter]),
    h("div", { class: "meter-scale" }, [h("span", {}, ["Normal"]), h("span", {}, ["Spam"])]),
  ];
  if (item.cues.length) {
    bits.push(h("div", { class: "cues" }, item.cues.map((cue) => h("span", { class: "cue" }, [cue]))));
  }
  if (item.signals.length) {
    bits.push(h("p", { class: "signal-caption" }, [item.signal_caption]));
    bits.push(h("div", { class: "chips" }, item.signals.map(chip)));
  }
  const cleaned = item.cleaned_text || "No usable words.";
  bits.push(
    h("details", {}, [
      h("summary", {}, ["Under the hood"]),
      h("p", { class: "cleaned" }, [cleaned]),
      h("p", { class: "length-note" }, [item.length_note]),
      h("p", { class: "rule-note" }, [
        "Links, phone numbers, and currency signs are flagged with simple rules. Cleaning strips symbols and splits numbers, so those clues are easy for a word model to miss.",
      ]),
    ]),
  );
  result.replaceChildren(...bits);
  animateMeter(meter, item.spam_probability);
  result.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
}

function batchHeadline(results) {
  const spamCount = results.filter((item) => item.verdict === "spam").length;
  const total = results.length;
  if (total === 1) return results[0].title;
  if (spamCount === 0) return `None of these ${total} look like spam.`;
  if (spamCount === total) return `All ${total} look like spam.`;
  return `${spamCount} of ${total} look like spam.`;
}

function renderBatch(results) {
  result.hidden = false;
  result.className = "result batch-wrap";
  const rows = results.map((item) => {
    const articleBits = [
      h("div", { class: "batch-row" }, [
        h("span", { class: `tag ${item.verdict}` }, [item.title]),
        h("span", {}, [pct(item.spam_probability)]),
      ]),
      h("p", {}, [item.text]),
    ];
    if (item.cues.length) {
      articleBits.push(h("div", { class: "cues" }, item.cues.map((cue) => h("span", { class: "cue" }, [cue]))));
    }
    if (item.signals.length) {
      articleBits.push(h("div", { class: "chips" }, item.signals.slice(0, 3).map(chip)));
    }
    return h("article", {}, articleBits);
  });
  result.replaceChildren(
    h("h3", { class: "batch-title" }, [batchHeadline(results)]),
    h("div", { class: "batch" }, rows),
  );
  result.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
}

async function checkCurrent() {
  clearError();
  const raw = message.value;
  if (mode === "one") {
    if (!raw.trim()) {
      showError("Paste a message first.");
      return;
    }
    if (raw.trim().length > 2000) {
      showError("Keep the message under 2,000 characters.");
      return;
    }
  } else if (!raw.split("\n").some((line) => line.trim())) {
    showError("Add at least one message.");
    return;
  }

  checkBtn.disabled = true;
  const previous = checkBtn.textContent;
  checkBtn.textContent = "Checking…";
  try {
    if (mode === "one") {
      const data = await api("/api/check", {
        method: "POST",
        body: JSON.stringify({ text: raw }),
      });
      renderSingle(data);
      remember(data);
    } else {
      const data = await api("/api/check-batch", {
        method: "POST",
        body: JSON.stringify({ texts: raw.split("\n") }),
      });
      renderBatch(data.results);
    }
  } catch (error) {
    hideResult();
    showError(error.message);
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = previous;
  }
}

function renderModel(card) {
  const matrix = card.metrics.confusion_matrix;
  const vectorizer = card.vectorizer;
  const featureText = vectorizer.max_features
    ? `${num(vectorizer.n_features)} weighted terms`
    : `${num(vectorizer.n_features)} word roots`;
  const trained = new Date(`${card.trained_at}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const searchTable = h("table", { class: "search" }, [
    h("thead", {}, [
      h("tr", {}, [
        h("th", { scope: "col" }, ["Setup"]),
        h("th", { scope: "col" }, ["Precision"]),
        h("th", { scope: "col" }, ["Recall"]),
        h("th", { scope: "col" }, ["F1"]),
      ]),
    ]),
    h("tbody", {}, card.search.map((row) => h("tr", { class: row.selected ? "selected" : "" }, [
      h("td", {}, [row.selected ? `${row.name} · selected` : row.name]),
      h("td", {}, [metric(row.precision)]),
      h("td", {}, [metric(row.recall)]),
      h("td", {}, [metric(row.f1)]),
    ]))),
  ]);

  modelCard.replaceChildren(
    h("h2", { class: "section-label" }, ["Model"]),
    h("p", { class: "precision" }, [metric(card.metrics.precision), h("span", {}, ["Spam precision"])]),
    h("div", { class: "metrics" }, [
      h("div", {}, [h("strong", {}, [metric(card.metrics.accuracy)]), h("span", {}, ["Accuracy"])]),
      h("div", {}, [h("strong", {}, [metric(card.metrics.recall)]), h("span", {}, ["Recall"])]),
      h("div", {}, [h("strong", {}, [metric(card.metrics.f1)]), h("span", {}, ["F1"])]),
    ]),
    h("p", { class: "hint" }, [
      "Precision is the headline because normal messages are the majority. It is the share of spam flags that were truly spam.",
    ]),
    h("div", { class: "balance", role: "img", "aria-label": "Share of normal and spam messages" }, [
      h("span", { class: "ham", style: `flex:${card.ham_count}` }),
      h("span", { class: "spam", style: `flex:${card.spam_count}` }),
    ]),
    h("p", { class: "balance-label" }, [
      h("span", {}, [`${num(card.ham_count)} normal`]),
      h("span", {}, [`${num(card.spam_count)} spam`]),
    ]),
    h("table", { class: "matrix" }, [
      h("caption", {}, ["Held-out test. Rows are the real label. Columns are the prediction."]),
      h("thead", {}, [
        h("tr", {}, [
          h("th", { scope: "col" }, [""]),
          h("th", { scope: "col" }, ["Normal"]),
          h("th", { scope: "col" }, ["Spam"]),
        ]),
      ]),
      h("tbody", {}, [
        h("tr", {}, [h("th", { scope: "row" }, ["Normal"]), h("td", {}, [num(matrix[0][0])]), h("td", {}, [num(matrix[0][1])])]),
        h("tr", {}, [h("th", { scope: "row" }, ["Spam"]), h("td", {}, [num(matrix[1][0])]), h("td", {}, [num(matrix[1][1])])]),
      ]),
    ]),
    h("ul", { class: "facts" }, [
      h("li", {}, [`${card.model_name} · ${vectorizer.name}`]),
      h("li", {}, [featureText]),
      h("li", {}, [`${num(card.rows_clean)} unique texts after dropping duplicates`]),
      h("li", {}, [`Trained on ${num(card.train_size)}, scored on ${num(card.test_size)} held-out texts`]),
      h("li", {}, [`Vectorizer fit on the training texts only · ${trained}`]),
    ]),
    h("details", {}, [
      h("summary", {}, ["Why this setup"]),
      h("p", { class: "hint" }, [card.selection_rule]),
      searchTable,
    ]),
  );
}

async function loadStats() {
  try {
    const card = await api("/api/stats");
    statusPill.textContent = "Model ready";
    statusPill.className = "pill ready";
    renderModel(card);
  } catch (error) {
    statusPill.textContent = "Model missing";
    statusPill.className = "pill missing";
    banner.hidden = false;
    banner.textContent = error.message;
    modelCard.replaceChildren(
      h("h2", { class: "section-label" }, ["Model"]),
      h("p", { class: "hint" }, ["Run python train.py from the project folder, then refresh this page."]),
    );
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  checkCurrent();
});

message.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    checkCurrent();
  }
});

message.addEventListener("input", updateCount);
clearBtn.addEventListener("click", () => {
  message.value = "";
  updateCount();
  hideResult();
  clearError();
  message.focus();
});
sampleBtn.addEventListener("click", () => {
  setMode("list");
  message.value = EXAMPLES.map((example) => example.text).join("\n");
  updateCount();
  checkCurrent();
});
modeOne.addEventListener("click", () => setMode("one"));
modeList.addEventListener("click", () => setMode("list"));
clearHistoryBtn.addEventListener("click", () => writeHistory([]));

const runMailBtn = document.querySelector("#run-mail");
const mailAccount = document.querySelector("#mail-account");
const mailStatus = document.querySelector("#mail-status");
const mailError = document.querySelector("#mail-error");
const mailResults = document.querySelector("#mail-results");

function mailHeadline(messages) {
  const spamCount = messages.filter((item) => item.verdict === "spam").length;
  const total = messages.length;
  if (spamCount === 0) return `None of these ${total} look like spam.`;
  if (spamCount === total) return total === 1 ? "This message looks like spam." : `All ${total} look like spam.`;
  return `${spamCount} of ${total} look like spam.`;
}

function renderMail(messages) {
  mailResults.hidden = false;
  if (!messages.length) {
    mailResults.replaceChildren(h("p", { class: "empty" }, ["The inbox has no messages."]));
    return;
  }
  const rows = messages.map((item) => {
    const bits = [
      h("div", { class: "batch-row" }, [
        h("span", { class: `tag ${item.verdict}` }, [item.title]),
        h("span", {}, [pct(item.spam_probability)]),
      ]),
      h("p", { class: "mail-subject" }, [item.subject]),
      h("p", { class: "mail-meta" }, [item.date ? `${item.sender} · ${item.date}` : item.sender]),
    ];
    if (item.preview) bits.push(h("p", {}, [item.preview]));
    return h("article", {}, bits);
  });
  mailResults.replaceChildren(
    h("h3", { class: "batch-title" }, [mailHeadline(messages)]),
    h("div", { class: "batch" }, rows),
  );
}

async function loadMailStatus() {
  try {
    const status = await api("/api/inbox");
    mailAccount.textContent = status.address;
    mailStatus.textContent = status.configured
      ? "Ready. Press Run to check the five newest messages."
      : "Add the Gmail app password in the .env file, then restart the app.";
  } catch (error) {
    mailStatus.textContent = error.message;
  }
}

async function runMail() {
  mailError.hidden = true;
  mailError.textContent = "";
  runMailBtn.disabled = true;
  runMailBtn.textContent = "Running…";
  try {
    const data = await api("/api/inbox/run", { method: "POST" });
    mailAccount.textContent = data.address;
    renderMail(data.messages);
    mailStatus.textContent = "Checked just now. Press Run to check again.";
  } catch (error) {
    mailResults.hidden = true;
    mailResults.replaceChildren();
    mailError.hidden = false;
    mailError.textContent = error.message;
  } finally {
    runMailBtn.disabled = false;
    runMailBtn.textContent = "Run";
  }
}

runMailBtn.addEventListener("click", runMail);

renderExamples();
renderHistory();
updateCount();
loadStats();
loadMailStatus();
