from app.backend.api.app.services.market_services import GetCandles


class FakeExchange:
    rateLimit = 0

    def __init__(self, rows, now_ms):
        self.rows = rows
        self.now_ms = now_ms
        self.calls = 0

    def parse_timeframe(self, interval):
        assert interval == "1h"
        return 3600

    def milliseconds(self):
        return self.now_ms

    def fetch_ohlcv(self, *_args, **_kwargs):
        self.calls += 1
        return self.rows if self.calls == 1 else []


def _downloader(limit=2):
    result = object.__new__(GetCandles)
    result.symbol = "BTC/USDT"
    result.interval = "1h"
    result.limit = limit
    return result


def test_download_excludes_current_candle_sorts_and_deduplicates():
    hour = 3_600_000
    current_open = 10 * hour
    rows = [
        [9 * hour, 100, 102, 99, 101, 10],
        [8 * hour, 90, 92, 89, 91, 9],
        [9 * hour, 100, 103, 99, 102, 11],
        [current_open, 102, 104, 101, 103, 12],
    ]
    candles = _downloader()._download(
        FakeExchange(rows, current_open + 1_000),
        "Fake",
    )

    assert [item.timestamp.timestamp() * 1000 for item in candles.items] == [
        8 * hour,
        9 * hour,
    ]
    assert candles.items[-1].close == 102


def test_download_rejects_non_finite_values():
    hour = 3_600_000
    rows = [[8 * hour, 100, 102, 99, float("nan"), 10]]
    try:
        _downloader(limit=1)._download(FakeExchange(rows, 10 * hour), "Fake")
    except ValueError as error:
        assert "finite" in str(error)
    else:
        raise AssertionError("non-finite candle was accepted")
