import pytest
from app.agent.service import AnalyticalAgentService
from app.agent.tools import ReadOnlyAnalyticsTools

def test_read_only_enforcement():
 with pytest.raises(ValueError):ReadOnlyAnalyticsTools({"change_threshold":lambda:None})
 tools=ReadOnlyAnalyticsTools({});
 with pytest.raises(PermissionError):tools.call("execute_order")

def test_llm_unavailable_degrades_without_inventing_data():
 tools=ReadOnlyAnalyticsTools({"get_recent_news":lambda:[{"id":"n1","title":"fixture","url":"https://example.com/n1","published_at":"2026-09-25T12:00:00Z"}]})
 service=AnalyticalAgentService(tools,llm_transport=lambda prompt:(_ for _ in()).throw(RuntimeError("down")))
 out=service.query("какие новости BTC?");assert out.degraded;assert out.model_used=="deterministic-fallback";assert len(out.evidence)==1;assert out.evidence[0].record_id=="n1";assert "https://example.com/n1" not in out.answer

def test_no_invented_model_version():
 tools=ReadOnlyAnalyticsTools({"get_decision":lambda:{"id":1,"model_version":"real-v1","probability":.6,"threshold":.5},"get_active_model":lambda:{"model_version":"real-v1"}})
 out=AnalyticalAgentService(tools,llm_transport=lambda p:(_ for _ in()).throw(RuntimeError())).query("почему trade запрещён?");assert {e.data.get("model_version") for e in out.evidence}=={"real-v1"}

def test_tool_calls_are_grounded():
 calls=[];tools=ReadOnlyAnalyticsTools({"get_paper_portfolio":lambda:calls.append("paper") or {"id":"p","equity":100}});AnalyticalAgentService(tools,llm_transport=lambda p:"ok").query("какие позиции paper portfolio?");assert calls==["paper"]

def test_missing_data_is_explicit():
 out=AnalyticalAgentService(ReadOnlyAnalyticsTools({}),llm_transport=lambda p:(_ for _ in()).throw(RuntimeError())).query("health");assert out.degraded and not out.evidence and out.uncertainty==1


def test_symbol_news_question_uses_symbol_tool():
    calls=[]
    tools=ReadOnlyAnalyticsTools({"get_news_for_symbol":lambda symbol: calls.append(symbol) or [{"id":"btc1","title":"fixture"}]})
    out=AnalyticalAgentService(tools,llm_transport=lambda p:"ok").query("какие новости сейчас релевантны BTC?")
    assert calls==["BTC"] and out.evidence[0].record_id=="btc1"
