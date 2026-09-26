from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .prompts import SYSTEM_PROMPT
from .schemas import AgentQueryResponse, EvidenceItem, EvidenceKind
from .tools import ReadOnlyAnalyticsTools


class AnalyticalAgentService:
    def __init__(self, tools: ReadOnlyAnalyticsTools, *, llm_transport=None) -> None:
        self.tools = tools
        self.llm_transport = llm_transport or self._ollama_transport

    @staticmethod
    def _ollama_transport(prompt: str) -> str:
        provider = os.getenv("NEWS_LLM_PROVIDER", "rule_based").strip().lower()
        model = os.getenv("NEWS_LLM_MODEL", "").strip()
        if provider != "ollama" or not model:
            raise RuntimeError("local LLM is not configured")
        url = os.getenv("NEWS_LLM_URL", "http://ollama:11434").rstrip("/") + "/api/generate"
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=float(os.getenv("NEWS_LLM_TIMEOUT_SECONDS", "8"))) as response:
            body = json.loads(response.read().decode("utf-8"))
        answer = str(body.get("response") or "").strip()
        if not answer:
            raise RuntimeError("empty LLM response")
        return answer

    def _collect(self, message: str) -> list[EvidenceItem]:
        lower = message.casefold()
        calls: list[tuple[str, dict[str, Any], EvidenceKind]] = []
        if "почему" in lower or "trade" in lower or "сделк" in lower or "decision" in lower:
            calls.extend([
                ("get_decision", {}, EvidenceKind.MODEL_ESTIMATE),
                ("get_active_model", {}, EvidenceKind.FACT),
            ])
        symbol = "BTC" if "btc" in lower else ("ETH" if "eth" in lower else None)
        if "новост" in lower and symbol and "get_news_for_symbol" in self.tools.providers:
            calls.append(("get_news_for_symbol", {"symbol": symbol}, EvidenceKind.NEWS_CLASSIFICATION))
        elif "новост" in lower or "событ" in lower:
            calls.append(("get_recent_news", {}, EvidenceKind.NEWS_CLASSIFICATION))
        if "high impact" in lower or "высок" in lower and "событ" in lower:
            calls.append(("get_high_impact_events", {}, EvidenceKind.NEWS_CLASSIFICATION))
        if "geopolit" in lower or "геополит" in lower or "risk" in lower:
            calls.append(("get_geopolitical_events", {}, EvidenceKind.FACT))
        if "модель" in lower or "model" in lower:
            calls.extend([( "get_active_model", {}, EvidenceKind.FACT), ("get_model_metrics", {}, EvidenceKind.MODEL_ESTIMATE)])
        if "false positive" in lower or "fp" in lower:
            calls.append(("get_false_positives", {}, EvidenceKind.MODEL_ESTIMATE))
        if "false negative" in lower or "fn" in lower:
            calls.append(("get_false_negatives", {}, EvidenceKind.MODEL_ESTIMATE))
        if "research" in lower or "исслед" in lower:
            calls.append(("get_research_summary", {}, EvidenceKind.FACT))
        if "paper" in lower or "позици" in lower or "портф" in lower:
            calls.append(("get_paper_portfolio", {}, EvidenceKind.FACT))
        if "health" in lower or "систем" in lower:
            calls.append(("get_system_health", {}, EvidenceKind.FACT))
        if not calls:
            calls = [("get_market_snapshot", {}, EvidenceKind.FACT)]

        evidence: list[EvidenceItem] = []
        seen: set[str] = set()
        for name, kwargs, kind in calls:
            if name in seen:
                continue
            seen.add(name)
            value = self.tools.call(name, **kwargs)
            if value is None:
                continue
            rows = value if isinstance(value, list) else [value]
            for row in rows[:20]:
                if not isinstance(row, dict):
                    row = {"value": row}
                evidence.append(
                    EvidenceItem(
                        kind=kind,
                        source=name,
                        record_id=str(row.get("id") or row.get("event_id") or row.get("model_version") or "") or None,
                        url=row.get("url") or row.get("source_url"),
                        timestamp=str(row.get("timestamp") or row.get("published_at") or row.get("created_at") or "") or None,
                        data=row,
                    )
                )
        return evidence

    @staticmethod
    def _degraded_answer(message: str, evidence: list[EvidenceItem]) -> str:
        if not evidence:
            return "Данных для подтверждённого ответа сейчас нет. Аналитический агент работает в degraded read-only режиме."
        labels = ", ".join(sorted({item.source for item in evidence}))
        return (
            f"Доступны подтверждённые записи из: {labels}. "
            "Локальная LLM недоступна, поэтому возвращается только grounded evidence без свободной интерпретации."
        )

    def query(self, message: str) -> AgentQueryResponse:
        evidence = self._collect(message)
        evidence_payload = [item.model_dump(mode="json") for item in evidence]
        prompt = SYSTEM_PROMPT + "\n\nUSER: " + message + "\nEVIDENCE:\n" + json.dumps(evidence_payload, ensure_ascii=False)
        try:
            answer = self.llm_transport(prompt)
            return AgentQueryResponse(
                answer=answer, evidence=evidence, uncertainty=0.35 if evidence else 0.9,
                model_used=os.getenv("NEWS_LLM_MODEL", "local-llm") or "local-llm", degraded=False,
            )
        except Exception:
            return AgentQueryResponse(
                answer=self._degraded_answer(message, evidence), evidence=evidence,
                uncertainty=0.6 if evidence else 1.0, model_used="deterministic-fallback", degraded=True,
            )
