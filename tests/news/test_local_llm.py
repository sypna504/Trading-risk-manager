from __future__ import annotations

import json

from app.news_intelligence.analysis import LocalLLMNewsAnalyzer, RuleBasedNewsAnalyzer


VALID = {
    "sentiment": "positive",
    "event_type": "etf",
    "crypto_relevance": 0.95,
    "impact_direction": "bullish",
    "impact_probability": 0.8,
    "affected_assets": ["btc"],
    "uncertainty": 0.2,
}


def make_analyzer(transport, *, model="qwen-test"):
    return LocalLLMNewsAnalyzer(
        base_url="http://ollama:11434",
        model=model,
        timeout_seconds=0.2,
        fallback=RuleBasedNewsAnalyzer(),
        transport=transport,
    )


def test_valid_ollama_json_is_applied(make_news_item):
    analyzer = make_analyzer(lambda *_args: {"response": json.dumps(VALID)})
    item = make_news_item(text="Bitcoin ETF approved with inflows")
    result = analyzer.analyze(item)
    assert result.sentiment.value == "positive"
    assert result.event_type.value == "etf"
    assert result.crypto_assets == ["BTC"]
    assert result.uncertainty == 0.2


def test_invalid_json_uses_rule_fallback(make_news_item):
    analyzer = make_analyzer(lambda *_args: {"response": "not-json"})
    result = analyzer.analyze(make_news_item(text="Exchange hacked and funds stolen"))
    assert result.event_type.value == "hack"
    assert result.sentiment.value == "negative"


def test_timeout_uses_rule_fallback(make_news_item):
    def transport(*_args):
        raise TimeoutError("slow")
    result = make_analyzer(transport).analyze(
        make_news_item(text="Bitcoin ETF approved with inflows")
    )
    assert result.event_type.value == "etf"


def test_unavailable_model_uses_rule_fallback(make_news_item):
    def transport(*_args):
        raise RuntimeError("model not found")
    result = make_analyzer(transport).analyze(
        make_news_item(text="Exchange hacked and funds stolen")
    )
    assert result.event_type.value == "hack"


def test_empty_ollama_response_uses_rule_fallback(make_news_item):
    result = make_analyzer(lambda *_args: {"response": ""}).analyze(
        make_news_item(text="Bitcoin ETF approved")
    )
    assert result.event_type.value == "etf"


def test_invalid_structured_score_uses_fallback(make_news_item):
    invalid = dict(VALID, crypto_relevance=1.4)
    result = make_analyzer(lambda *_args: {"response": json.dumps(invalid)}).analyze(
        make_news_item(text="Exchange hacked and funds stolen")
    )
    assert result.event_type.value == "hack"


def test_missing_model_uses_fallback_without_transport(make_news_item):
    called = False
    def transport(*_args):
        nonlocal called
        called = True
        return {"response": json.dumps(VALID)}
    result = make_analyzer(transport, model=None).analyze(
        make_news_item(text="Bitcoin ETF approved")
    )
    assert result.event_type.value == "etf"
    assert called is False


def test_llm_receives_only_news_text_and_preserves_metadata(make_news_item):
    captured = {}
    def transport(_url, payload, _timeout):
        captured.update(payload)
        return {"response": json.dumps(VALID)}

    item = make_news_item(
        source_name="Secret Source Name",
        url="https://private.example/news/1",
        text="Bitcoin ETF approved",
    )
    result = make_analyzer(transport).analyze(item)
    prompt = captured["prompt"]
    assert item.text in prompt
    assert item.source_name not in prompt
    assert item.url not in prompt
    assert result.source_name == item.source_name
    assert result.url == item.url
    assert result.published_at == item.published_at


def test_extra_llm_fields_are_rejected_and_fallback(make_news_item):
    invalid = dict(VALID, source="invented", price=12345)
    result = make_analyzer(lambda *_args: {"response": json.dumps(invalid)}).analyze(
        make_news_item(text="Exchange hacked and funds stolen")
    )
    assert result.event_type.value == "hack"
    assert result.sentiment.value == "negative"
