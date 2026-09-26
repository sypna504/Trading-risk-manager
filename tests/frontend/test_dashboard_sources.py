from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app/backend/api/app/static"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_files_exist():
    for name in ("index.html", "styles.css", "app.js"):
        path = STATIC / name
        assert path.exists()
        assert _read(path).strip()


def test_dashboard_consumes_required_api_endpoints():
    js = _read(STATIC / "app.js")
    for endpoint in (
        "/api/v1/ml/model-info",
        "/api/v1/health",
        "/api/v1/trading/decision",
        "/api/v1/trading/decisions?limit=10",
    ):
        assert endpoint in js


def test_external_news_rendering_does_not_use_innerhtml():
    js = _read(STATIC / "app.js")
    assert ".innerHTML" not in js
    assert ".outerHTML" not in js
    assert "textContent" in js
    assert "textElement(\"h3\", event.title" in js
    assert "textElement(\"span\", event.source" in js
    assert 'url.protocol !== "http:"' in js
    assert 'url.protocol !== "https:"' in js


def test_interval_selector_uses_only_model_supported_values():
    html = _read(STATIC / "index.html")
    js = _read(STATIC / "app.js")
    assert '<select id="interval"></select>' in html
    assert "populateSelect(intervalSelect, data.supported_intervals || [], \"1h\")" in js
    assert "submitButton.disabled = !data.model_file_exists" in js


def test_news_context_and_top_five_are_rendered():
    js = _read(STATIC / "app.js")
    context = _read(ROOT / "app/news_intelligence/context.py")
    schema = _read(ROOT / "app/backend/api/app/schemas/trade_decision_schemas.py")
    for field in (
        "news_count",
        "sentiment_score",
        "risk_level",
        "positive_count",
        "negative_count",
        "high_impact_count",
        "top_events",
    ):
        assert field in js
    assert ".slice(0, 5)" in js
    assert '"source": item.source_name' in context
    assert "source: str" in schema


def test_missing_news_is_graceful_and_informational_only():
    html = _read(STATIC / "index.html")
    js = _read(STATIC / "app.js")
    assert "informational only" in html
    assert "if (!context)" in js
    assert "News context недоступен" in js
    assert "renderNewsContext(data.news_context || null)" in js


def test_model_unavailable_is_graceful():
    js = _read(STATIC / "app.js")
    assert 'textElement("p", "Model unavailable", "error")' in js
    assert "populateSelect(intervalSelect, [], null)" in js
    assert "submitButton.disabled = true" in js


def test_history_contains_news_risk_and_outcome():
    js = _read(STATIC / "app.js")
    assert '"News risk"' in js
    assert '"Outcome"' in js
    assert "item.news_risk_level" in js
    assert "item.outcome_status" in js


def test_health_block_supports_required_states_and_services():
    js = _read(STATIC / "app.js")
    health = _read(ROOT / "app/backend/api/app/routers/health_router.py")
    for service in ("Backend", "ML Service", "News Service", "LLM"):
        assert service in js
    for state in ("ready", "degraded", "optional unavailable"):
        assert state in js
    assert '"news_service": news_status' in health
    assert '"llm": llm_status' in health
