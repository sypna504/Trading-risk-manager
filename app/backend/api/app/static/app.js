const form = document.querySelector("#decision-form");
const statusNode = document.querySelector("#status");
const resultNode = document.querySelector("#result");
const historyNode = document.querySelector("#history");
const modelInfoNode = document.querySelector("#model-info");
const submitButton = document.querySelector("#submit-button");
const intervalSelect = document.querySelector("#interval");
const exchangeSelect = document.querySelector("#exchange");

const number = (value, digits = 4) => value == null ? "—" : Number(value).toFixed(digits);

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
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (value === preferred) option.selected = true;
    select.appendChild(option);
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
    addMetric(grid, "Version", data.model_version);
    addMetric(grid, "Status", data.model_status);
    addMetric(grid, "Schema", data.feature_schema_version);
    addMetric(grid, "Calibration", data.calibration_method || "none");
    addMetric(grid, "Data age, h", number(data.data_age_hours, 1));
    addMetric(grid, "Stale", data.is_model_stale ? "да" : "нет");
    modelInfoNode.appendChild(grid);
    for (const warning of data.warnings || []) {
      modelInfoNode.appendChild(textElement("p", warning, "error"));
    }
    populateSelect(intervalSelect, data.supported_intervals || ["1h"], "1h");
    populateSelect(exchangeSelect, data.supported_exchanges || ["binance"], "binance");
    submitButton.disabled = !data.model_file_exists || !data.config_file_exists;
  } catch (error) {
    clear(modelInfoNode);
    modelInfoNode.appendChild(textElement("span", error.message, "error"));
    populateSelect(intervalSelect, ["1h"], "1h");
    populateSelect(exchangeSelect, ["binance"], "binance");
    submitButton.disabled = true;
  }
}

function renderResult(data) {
  clear(resultNode);
  resultNode.className = "panel";
  const card = document.createElement("div");
  card.className = `result-card ${data.trade_allowed ? "allowed" : "blocked"}`;
  card.appendChild(textElement("p", data.status, "eyebrow"));
  card.appendChild(textElement("h2", data.trade_allowed ? "Сделка разрешена" : data.status === "no_signal" ? "Сигнала нет" : "Сделка запрещена"));
  card.appendChild(textElement("p", data.reason));
  const grid = document.createElement("div");
  grid.className = "result-grid";
  const risk = data.risk_parameters || {};
  addMetric(grid, "Стратегия", data.selected_strategy || "—");
  addMetric(grid, "Raw probability", number(data.raw_prob_good_trade, 4));
  addMetric(grid, "Calibrated probability", number(data.prob_good_trade, 4));
  addMetric(grid, "Threshold", number(data.threshold, 4));
  addMetric(grid, "Calibration", data.calibration_method || "none");
  addMetric(grid, "Model status", data.model_status || "—");
  addMetric(grid, "Signal close", number(data.signal_close_price, 4));
  addMetric(grid, "Planned entry estimate", number(data.planned_entry_price, 4));
  addMetric(grid, "Entry convention", data.entry_convention || "—");
  addMetric(grid, "Stop-loss", number(risk.stop_loss_price, 4));
  addMetric(grid, "Take-profit", number(risk.take_profit_price, 4));
  addMetric(grid, "Outcome status", data.outcome_status || "—");
  addMetric(grid, "Model version", data.model_version || "—");
  card.appendChild(grid);
  for (const warning of data.model_warnings || []) card.appendChild(textElement("p", warning, "error"));
  resultNode.appendChild(card);
}

async function loadHistory() {
  historyNode.textContent = "Загрузка...";
  try {
    const response = await fetch("/api/v1/trading/decisions?limit=10");
    const rows = await response.json();
    if (!response.ok) throw new Error(rows.detail || "history failed");
    clear(historyNode);
    if (!rows.length) {
      historyNode.textContent = "История пока пустая";
      return;
    }
    for (const row of rows) {
      const item = document.createElement("div");
      item.className = "history-item";
      item.append(
        textElement("div", `${row.symbol} · ${new Date(row.created_at).toLocaleString()}`),
        textElement("div", `${row.status} · ${row.selected_strategy || "—"}`),
        textElement("div", `p=${number(row.probability, 4)} · ${row.model_status || "—"}`),
        textElement("div", `${row.trade_allowed ? "разрешено" : "запрещено"} · outcome=${row.outcome_status || "—"}`),
      );
      historyNode.appendChild(item);
    }
  } catch (error) {
    clear(historyNode);
    historyNode.appendChild(textElement("span", error.message, "error"));
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  submitButton.disabled = true;
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
    statusNode.textContent = "Проверка завершена";
    await loadHistory();
  } catch (error) {
    statusNode.textContent = error.message;
    statusNode.className = "status error";
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#refresh-history").addEventListener("click", loadHistory);
loadModelInfo();
loadHistory();
