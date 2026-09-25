const form = document.querySelector("#decision-form");
const statusNode = document.querySelector("#status");
const resultNode = document.querySelector("#result");
const historyNode = document.querySelector("#history");
const modelInfoNode = document.querySelector("#model-info");
const healthNode = document.querySelector("#system-health");
const newsNode = document.querySelector("#news-context");
const submitButton = document.querySelector("#submit-button");
const intervalSelect = document.querySelector("#interval");
const exchangeSelect = document.querySelector("#exchange");

const number = (value, digits = 4) => value == null ? "—" : Number(value).toFixed(digits);
const yesNo = value => value ? "да" : "нет";

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function textElement(tag, text, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = String(text ?? "—");
  return node;
}

function addMetric(container, label, value) {
  const item = document.createElement("div");
  item.className = "metric";
  item.append(textElement("span", label), textElement("strong", value));
  container.appendChild(item);
}

function populateSelect(select, values, preferred) {
  clear(select);
  const safeValues = Array.isArray(values) && values.length ? values : [];
  for (const value of safeValues) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (value === preferred) option.selected = true;
    select.appendChild(option);
  }
}

function normalizeServiceState(value) {
  const raw = String(value || "").toLowerCase().replaceAll("_", " ");
  if (["ready", "serving", "available", "ok"].includes(raw)) return "ready";
  if (["optional unavailable", "optional-unavailable"].includes(raw)) return "optional unavailable";
  return "degraded";
}

function renderHealthItem(label, state) {
  const normalized = normalizeServiceState(state);
  const item = document.createElement("div");
  item.className = "health-item";
  item.appendChild(textElement("strong", label));
  const stateNode = textElement("span", normalized, `health-state ${normalized.replaceAll(" ", "-")}`);
  item.appendChild(stateNode);
  healthNode.appendChild(item);
}

async function loadHealth() {
  clear(healthNode);
  try {
    const response = await fetch("/api/v1/health");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "health failed");
    const services = data.services || {};
    renderHealthItem("Backend", services.backend || data.readiness);
    renderHealthItem("ML Service", services.ml_service || data.ml_service);
    renderHealthItem("News Service", services.news_service || "degraded");
    renderHealthItem("LLM", services.llm || "optional unavailable");
  } catch (error) {
    clear(healthNode);
    renderHealthItem("Backend", "degraded");
    renderHealthItem("ML Service", "degraded");
    renderHealthItem("News Service", "degraded");
    renderHealthItem("LLM", "optional unavailable");
    healthNode.appendChild(textElement("span", error.message, "error"));
  }
}

async function loadModelInfo() {
  try {
    const response = await fetch("/api/v1/ml/model-info");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "model-info failed");
    clear(modelInfoNode);
    const grid = document.createElement("div");
    grid.className = "result-grid";
    addMetric(grid, "Model version", data.model_version || "—");
    addMetric(grid, "Model status", data.model_status || "—");
    addMetric(grid, "Schema version", data.feature_schema_version || "—");
    addMetric(grid, "Supported interval", (data.supported_intervals || []).join(", ") || "—");
    addMetric(grid, "Model age", data.model_age_days == null ? "—" : `${data.model_age_days} d`);
    modelInfoNode.appendChild(grid);
    for (const warning of data.warnings || []) {
      modelInfoNode.appendChild(textElement("p", warning, "error"));
    }

    // The interval selector is built only from model-supported values.
    populateSelect(intervalSelect, data.supported_intervals || [], "1h");
    populateSelect(exchangeSelect, data.supported_exchanges || ["binance"], "binance");
    submitButton.disabled = !data.model_file_exists || !data.config_file_exists || !intervalSelect.value;
  } catch (error) {
    clear(modelInfoNode);
    modelInfoNode.appendChild(textElement("p", "Model unavailable", "error"));
    modelInfoNode.appendChild(textElement("span", error.message, "muted"));
    populateSelect(intervalSelect, [], null);
    populateSelect(exchangeSelect, ["binance"], "binance");
    submitButton.disabled = true;
  }
}

function renderResult(data) {
  clear(resultNode);
  resultNode.className = "panel";
  const card = document.createElement("div");
  const statusClass = data.status === "no_signal" ? "no-signal" : data.trade_allowed ? "allowed" : "blocked";
  card.className = `result-card ${statusClass}`;
  card.appendChild(textElement("p", data.status, "eyebrow"));
  card.appendChild(textElement("h2", data.trade_allowed ? "Сделка разрешена" : data.status === "no_signal" ? "Сигнала нет" : "Сделка запрещена"));
  card.appendChild(textElement("p", data.reason));

  const grid = document.createElement("div");
  grid.className = "result-grid";
  const risk = data.risk_parameters || {};
  addMetric(grid, "Symbol", data.symbol || "—");
  addMetric(grid, "Strategy", data.selected_strategy || "—");
  addMetric(grid, "Signal detected", yesNo(data.signal_detected));
  addMetric(grid, "Trade allowed", yesNo(data.trade_allowed));
  addMetric(grid, "Raw probability", number(data.raw_prob_good_trade, 4));
  addMetric(grid, "Calibrated probability", number(data.prob_good_trade, 4));
  addMetric(grid, "Threshold", number(data.threshold, 4));
  addMetric(grid, "Signal close", number(data.signal_close_price, 4));
  addMetric(grid, "Planned entry", number(data.planned_entry_price, 4));
  addMetric(grid, "SL", number(risk.stop_loss_price, 4));
  addMetric(grid, "TP", number(risk.take_profit_price, 4));
  addMetric(grid, "Position size", number(risk.recommended_position_size, 6));
  addMetric(grid, "Risk level", data.risk_level || "—");
  card.appendChild(grid);

  for (const warning of data.model_warnings || []) {
    card.appendChild(textElement("p", warning, "error"));
  }
  resultNode.appendChild(card);
}

function sentimentLabel(score) {
  const value = Number(score || 0);
  if (value > 0.15) return "positive";
  if (value < -0.15) return "negative";
  return "neutral";
}

function safeExternalUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value, window.location.origin);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.href;
  } catch (_error) {
    return null;
  }
}

function renderNewsContext(context) {
  clear(newsNode);
  if (!context) {
    newsNode.appendChild(textElement("div", "News context недоступен. Решение всё равно рассчитано только Quant/ML слоем.", "empty-state"));
    return;
  }

  const summary = document.createElement("div");
  summary.className = "result-grid news-summary";
  addMetric(summary, `Last ${context.window_hours || 24}h count`, context.news_count ?? 0);
  addMetric(summary, "Sentiment", `${sentimentLabel(context.sentiment_score)} (${number(context.sentiment_score, 2)})`);
  addMetric(summary, "Risk level", context.risk_level || "low");
  addMetric(summary, "Positive / Negative", `${context.positive_count ?? 0} / ${context.negative_count ?? 0}`);
  addMetric(summary, "High impact events", context.high_impact_count ?? 0);
  newsNode.appendChild(summary);

  const events = Array.isArray(context.top_events) ? context.top_events.slice(0, 5) : [];
  if (!events.length) {
    newsNode.appendChild(textElement("div", "Релевантных новостей за окно нет.", "empty-state"));
    return;
  }

  const list = document.createElement("div");
  list.className = "news-list";
  for (const event of events) {
    const item = document.createElement("article");
    item.className = "news-item";

    const header = document.createElement("div");
    header.className = "news-item-header";
    header.append(
      textElement("span", event.published_at ? new Date(event.published_at).toLocaleString() : "—"),
      textElement("span", event.source || "unknown source"),
    );
    item.appendChild(header);
    item.appendChild(textElement("h3", event.title || "Без заголовка", "news-title"));

    const meta = document.createElement("div");
    meta.className = "news-meta";
    meta.append(
      textElement("span", `event=${event.event_type || "other"}`),
      textElement("span", `sentiment=${event.sentiment || "neutral"}`),
      textElement("span", `impact=${number(event.impact_probability, 2)}`),
      textElement("span", `direction=${event.impact_direction || "uncertain"}`),
    );
    item.appendChild(meta);

    const safeUrl = safeExternalUrl(event.url);
    if (safeUrl) {
      const link = document.createElement("a");
      link.className = "news-link";
      link.href = safeUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Открыть источник";
      item.appendChild(link);
    }
    list.appendChild(item);
  }
  newsNode.appendChild(list);
}

function appendHistoryCell(row, value, className = "") {
  row.appendChild(textElement("td", value, className));
}

async function loadHistory() {
  historyNode.textContent = "Загрузка...";
  try {
    const response = await fetch("/api/v1/trading/decisions?limit=10");
    const rows = await response.json();
    if (!response.ok) throw new Error(rows.detail || "history failed");
    clear(historyNode);
    if (!rows.length) {
      historyNode.appendChild(textElement("div", "История пока пустая", "empty-state"));
      return;
    }

    const table = document.createElement("table");
    table.className = "history-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    for (const title of ["Symbol", "Time", "Strategy", "Probability", "Trade", "News risk", "Outcome"]) {
      headRow.appendChild(textElement("th", title));
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const item of rows) {
      const row = document.createElement("tr");
      appendHistoryCell(row, item.symbol || "—");
      appendHistoryCell(row, item.created_at ? new Date(item.created_at).toLocaleString() : "—");
      appendHistoryCell(row, item.selected_strategy || "—");
      appendHistoryCell(row, number(item.probability, 4));

      const tradeCell = document.createElement("td");
      tradeCell.appendChild(textElement("span", item.trade_allowed ? "allowed" : "blocked", `tag ${item.trade_allowed ? "allowed" : "blocked"}`));
      row.appendChild(tradeCell);

      const newsRisk = item.news_risk_level || (item.news_context_available ? "low" : "—");
      const newsCell = document.createElement("td");
      newsCell.appendChild(textElement("span", newsRisk, `tag ${["low", "medium", "high"].includes(newsRisk) ? newsRisk : ""}`));
      row.appendChild(newsCell);

      appendHistoryCell(row, item.outcome_status || "—");
      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    historyNode.appendChild(table);
  } catch (error) {
    clear(historyNode);
    historyNode.appendChild(textElement("span", error.message, "error"));
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  submitButton.disabled = true;
  statusNode.className = "status";
  statusNode.textContent = "Получаем закрытые свечи и проверяем контракт модели...";
  const params = new URLSearchParams({
    exchange: exchangeSelect.value,
    symbol: document.querySelector("#symbol").value.trim().toUpperCase(),
    interval: intervalSelect.value,
    limit: document.querySelector("#limit").value,
    account_balance: document.querySelector("#account-balance").value,
    risk_per_trade_pct: document.querySelector("#risk-per-trade").value,
    max_position_share_pct: document.querySelector("#max-position-share").value,
  });
  try {
    const response = await fetch(`/api/v1/trading/decision?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "decision failed");
    renderResult(data);
    renderNewsContext(data.news_context || null);
    statusNode.textContent = "Проверка завершена";
    await loadHistory();
    await loadHealth();
  } catch (error) {
    statusNode.textContent = error.message;
    statusNode.className = "status error";
    renderNewsContext(null);
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#refresh-history").addEventListener("click", loadHistory);
document.querySelector("#refresh-dashboard").addEventListener("click", async () => {
  await Promise.all([loadModelInfo(), loadHealth(), loadHistory()]);
});

loadModelInfo();
loadHealth();
loadHistory();
