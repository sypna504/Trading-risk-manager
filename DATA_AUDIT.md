# Data Audit

- **Date:** 2026-08-25
- **Base state:** `feature/auto-signal-choseing + research-mvp-final-v9 overlay + frozen research finalization v10`
- **Commit:** NOT CAPTURED in packaging workspace (no .git directory); capture locally with `git rev-parse HEAD` before applying overlay
- **Real Binance research:** NOT RUN
- **Production promotion:** NO

## Real Binance data

**NOT RUN.** No current user-side binary parquet is available in this packaging runtime. The ZIP does not claim a data-quality PASS for the user's latest history.

## Synthetic validation data

Synthetic audit: **PASS**.

- rows: `5760`
- period: `2026-01-01 00:00:00+00:00 → 2026-03-01 23:00:00+00:00`
- symbols: `ADAUSDT, BTCUSDT, ETHUSDT, SOLUSDT`
- duplicates: `0`
- invalid OHLCV rows: `0`
- zero-volume rows: `0`
- gap symbols: `0`

The real full command runs `--update-history`, then audits the mounted host `history_data.parquet` before model research. A failed audit blocks the run.

## Reproduction

```powershell
python scripts\test_all.py
scripts\research_synthetic.cmd
scripts\research_full.cmd
scripts\research_results.cmd
scripts\research_candidate.cmd
```
