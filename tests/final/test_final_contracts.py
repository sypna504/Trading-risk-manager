from __future__ import annotations

from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]

def read(path:str)->str:return (ROOT/path).read_text(encoding="utf-8")

def test_backend_routes_are_wired():
    main=read("app/backend/api/app/main.py")
    for name in ("geopolitical_router","agent_router","paper_router","research_router"):
        assert name in main

def test_no_real_order_endpoint_or_agent_mutation():
    all_text="\n".join(p.read_text(encoding="utf-8") for p in (ROOT/"app").rglob("*.py"))
    assert "/orders/real" not in all_text
    tools=read("app/agent/tools.py")
    for forbidden in ("execute_order","promote_model","rollback_model","change_threshold","change_risk","modify_portfolio"):
        assert forbidden not in tools.split("ALLOWED =",1)[1].split("}",1)[0]

def test_compose_final_stack_and_optional_profiles():
    compose=yaml.safe_load(read("docker-compose.yml"));services=compose["services"]
    for name in ("backend","ml_service","ml_trainer","news_service","frontend"):
        assert name in services
    assert services["ollama"]["profiles"]==["llm"]
    assert services["postgres"]["profiles"]==["postgres"]
    assert "ollama" not in (services["backend"].get("depends_on") or {})

def test_ci_has_final_jobs():
    ci=yaml.safe_load(read(".github/workflows/ci.yml"));jobs=ci["jobs"]
    for name in ("compile","backend","ml","research","automl-synthetic","news","agent-paper","frontend","docker-build","docker-integration","e2e"):
        assert name in jobs

def test_cd_builds_only_paper_platform_images():
    cd=read(".github/workflows/cd.yml")
    for image in ("backend","ml_service","news_service","frontend"):
        assert f"name: {image}" in cd
    assert "real trading" in cd.lower()

def test_required_docs_exist():
    for rel in ("ARCHITECTURE.md","docs/QUANT_RESEARCH.md","docs/NEWS_INTELLIGENCE.md","docs/GEOPOLITICAL_EVENTS.md","docs/LOCAL_LLM.md","docs/AGENT.md","docs/PAPER_TRADING.md","docs/TESTING.md","docs/DEPLOYMENT.md","docs/DATA_CONTRACTS.md","E2E_REPORT.md","PAPER_TRADING_REPORT.md"):
        assert (ROOT/rel).exists(), rel

def test_news_gate_rule_is_preserved_in_docs_and_paper():
    assert "does not modify `trade_allowed`" in read("README.md") or "do not modify `trade_allowed`" in read("README.md")
    paper=read("app/paper/service.py")
    assert 'decision.get("trade_allowed")' in paper
