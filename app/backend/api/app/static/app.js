const form = document.querySelector("#decision-form");
const statusNode = document.querySelector("#status");
const resultNode = document.querySelector("#result");
const historyNode = document.querySelector("#history");
const submitButton = document.querySelector("#submit-button");

const number = (value, digits = 4) => value == null ? "—" : Number(value).toFixed(digits);

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderResult(data) {
  const className = data.status === "no_signal"
    ? "no-signal"
    : data.trade_allowed
      ? "allowed"
      : data.risk_level === "medium"
        ? "medium"
        : "blocked";

  const risk = data.risk_parameters || {};
  resultNode.className = "panel";
  resultNode.innerHTML = `
    <div class="result-card ${className}">
      <p class="eyebrow">${data.status}</p>
      <h2>${data.trade_allowed ? "Сделка разрешена" : data.status === "no_signal" ? "Сигнала нет" : "Сделка запрещена"}</h2>
      <p>${data.reason}</p>
      <div class="result-grid">
        ${metric("Стратегия", data.selected_strategy || "—")}
        ${metric("Вероятность", number(data.prob_good_trade, 4))}
        ${metric("Threshold", number(data.threshold, 4))}
        ${metric("Risk level", data.risk_level || "—")}
        ${metric("Entry", number(data.entry_price, 4))}
        ${metric("Stop-loss", number(risk.stop_loss_price, 4))}
        ${metric("Take-profit", number(risk.take_profit_price, 4))}
        ${metric("Размер позиции", number(risk.recommended_position_size, 6))}
        ${metric("Номинал позиции", number(risk.recommended_position_notional, 2))}
        ${metric("Model version", data.model_version || "—")}
        ${metric("Время", new Date(data.checked_at).toLocaleString())}
      </div>
    </div>`;
}

async function loadHistory() {
  historyNode.innerHTML = "Загрузка...";
  try {
    const response = await fetch("/api/v1/trading/decisions?limit=10");
    if (!response.ok) throw new Error(await response.text());
    const rows = await response.json();
    historyNode.innerHTML = rows.length ? rows.map(row => `
      <div class="history-item">
        <div><strong>${row.symbol}</strong><br><small>${new Date(row.created_at).toLocaleString()}</small></div>
        <div>${row.status}<br><small>${row.selected_strategy || "—"}</small></div>
        <div>p=${number(row.probability, 4)}<br><small>${row.risk_level || "—"}</small></div>
        <div>${row.trade_allowed ? "разрешено" : "запрещено"}<br><small>${row.model_version || "—"}</small></div>
      </div>`).join("") : "История пока пустая";
  } catch (error) {
    historyNode.innerHTML = `<span class="error">${error.message}</span>`;
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  submitButton.disabled = true;
  statusNode.textContent = "Получаем свечи и проверяем сигнал...";

  const params = new URLSearchParams({
    exchange: document.querySelector("#exchange").value,
    symbol: document.querySelector("#symbol").value.trim().toUpperCase(),
    interval: document.querySelector("#interval").value,
    limit: document.querySelector("#limit").value,
    account_balance: document.querySelector("#account-balance").value,
    risk_per_trade_pct: document.querySelector("#risk-per-trade").value,
    max_position_share_pct: document.querySelector("#max-position-share").value,
  });

  try {
    const response = await fetch(`/api/v1/trading/decision?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || JSON.stringify(data));
    renderResult(data);
    statusNode.textContent = "Проверка завершена";
    await loadHistory();
  } catch (error) {
    statusNode.innerHTML = `<span class="error">${error.message}</span>`;
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector("#refresh-history").addEventListener("click", loadHistory);
loadHistory();
