from __future__ import annotations

import re

from .base import NewsAnalyzer
from ..models import ImpactDirection, NewsEventType, NewsItem, NewsSentiment


_ASSET_PATTERNS = {
    "BTC": ("bitcoin", "btc"),
    "ETH": ("ethereum", "ether", "eth"),
    "SOL": ("solana", "sol"),
    "XRP": ("xrp", "ripple"),
    "BNB": ("bnb", "binance coin"),
    "USDT": ("usdt", "tether"),
    "USDC": ("usdc", "usd coin"),
}

_EVENT_KEYWORDS = {
    NewsEventType.HACK: ("hack", "hacked", "exploit", "breach", "stolen", "drain"),
    NewsEventType.ETF: ("etf", "exchange-traded fund", "exchange traded fund"),
    NewsEventType.REGULATION: ("regulation", "regulator", "sec ", "cftc", "ban", "lawsuit", "compliance", "license"),
    NewsEventType.STABLECOIN: ("stablecoin", "depeg", "usdt", "usdc", "tether"),
    NewsEventType.EXCHANGE: ("exchange", "binance", "coinbase", "kraken", "bybit", "listing", "delisting"),
    NewsEventType.MACRO: ("inflation", "cpi", "interest rate", "rates", "federal reserve", "fed ", "ecb", "gdp", "recession", "jobs report"),
    NewsEventType.GEOPOLITICAL: ("war", "sanctions", "geopolitical", "ceasefire", "conflict", "tariff"),
}

_POSITIVE = (
    "approved", "approval", "inflow", "record inflow", "launch", "adoption",
    "partnership", "upgrade", "rally", "surge", "wins", "settlement approved",
)
_NEGATIVE = (
    "hack", "hacked", "exploit", "breach", "stolen", "ban", "banned",
    "lawsuit", "crackdown", "outflow", "depeg", "default", "liquidation",
    "sanction", "recession", "delisting", "fraud",
)
_CRYPTO_TERMS = (
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain", "token",
    "stablecoin", "defi", "btc", "eth", "solana", "xrp", "binance", "coinbase",
)


def _contains(text: str, keyword: str) -> bool:
    if " " in keyword or keyword.endswith(" "):
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


class RuleBasedNewsAnalyzer(NewsAnalyzer):
    """Deterministic fallback that never needs an external service."""

    def analyze(self, item: NewsItem) -> NewsItem:
        content = f"{item.title} {item.text}".casefold()
        assets = list(item.crypto_assets)
        for asset, patterns in _ASSET_PATTERNS.items():
            if any(_contains(content, pattern) for pattern in patterns) and asset not in assets:
                assets.append(asset)

        event_type = NewsEventType.OTHER
        for candidate in (
            NewsEventType.HACK,
            NewsEventType.ETF,
            NewsEventType.REGULATION,
            NewsEventType.STABLECOIN,
            NewsEventType.EXCHANGE,
            NewsEventType.MACRO,
            NewsEventType.GEOPOLITICAL,
        ):
            if any(_contains(content, keyword) for keyword in _EVENT_KEYWORDS[candidate]):
                event_type = candidate
                break
        if event_type == NewsEventType.OTHER and assets:
            event_type = NewsEventType.TOKEN_SPECIFIC

        positive_hits = sum(_contains(content, word) for word in _POSITIVE)
        negative_hits = sum(_contains(content, word) for word in _NEGATIVE)
        if positive_hits > negative_hits:
            sentiment = NewsSentiment.POSITIVE
            direction = ImpactDirection.BULLISH
        elif negative_hits > positive_hits:
            sentiment = NewsSentiment.NEGATIVE
            direction = ImpactDirection.BEARISH
        else:
            sentiment = NewsSentiment.NEUTRAL
            direction = ImpactDirection.UNCERTAIN

        explicit_crypto = sum(_contains(content, term) for term in _CRYPTO_TERMS)
        if assets:
            relevance = 1.0
        elif explicit_crypto:
            relevance = 0.85
        elif event_type in {NewsEventType.MACRO, NewsEventType.GEOPOLITICAL}:
            relevance = 0.35
        else:
            relevance = 0.05

        base_impact = {
            NewsEventType.HACK: 0.90,
            NewsEventType.ETF: 0.85,
            NewsEventType.REGULATION: 0.80,
            NewsEventType.STABLECOIN: 0.85,
            NewsEventType.EXCHANGE: 0.70,
            NewsEventType.MACRO: 0.60,
            NewsEventType.GEOPOLITICAL: 0.60,
            NewsEventType.TOKEN_SPECIFIC: 0.55,
            NewsEventType.OTHER: 0.20,
        }[event_type]
        credibility_multiplier = 0.60 + 0.40 * float(item.credibility_score)
        impact_probability = min(1.0, base_impact * credibility_multiplier)
        if relevance <= 0.10:
            impact_probability = min(impact_probability, 0.10)

        uncertainty = 0.65 if direction == ImpactDirection.UNCERTAIN else 0.35
        if relevance <= 0.10:
            uncertainty = max(uncertainty, 0.80)

        return item.model_copy(
            update={
                "crypto_assets": assets,
                "event_type": event_type,
                "sentiment": sentiment,
                "crypto_relevance": round(relevance, 4),
                "impact_direction": direction,
                "impact_probability": round(impact_probability, 4),
                "uncertainty": round(uncertainty, 4),
            }
        )
