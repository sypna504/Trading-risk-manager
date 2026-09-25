# Research progress trace

This overlay adds observational progress tracing only. It does not change targets, features, splits, selection logic, gates, backtests, promotion rules, or model architecture.

## What appears in the main terminal

`research_full.cmd` now prints flushed progress messages such as:

```text
[     0.0s] [research] [data] PHASE     update/load/audit Binance history
[    34.2s] [research] [target] START     #1 model architecture=pooled ...
[    92.4s] [research] [target] DONE      #1 model architecture=pooled ...
[    92.4s] [research] [target] RESULT    live score=... ROC=... PR=... PF=... return=...
```

A heartbeat is printed every 30 seconds while the current phase/task is still running.

## Files

During a run the tracer writes:

- `runtime/research/PROGRESS.json` — latest event/current state;
- `runtime/research/PROGRESS.jsonl` — append-only event log.

Synthetic research uses its configured output root, normally `runtime/synthetic_research`.

## Watch from another terminal

Full real-data research:

```powershell
scripts\research_watch.cmd
```

Synthetic research:

```powershell
scripts\research_watch.cmd runtime\synthetic_research
```

Linux/macOS equivalent:

```bash
scripts/research_watch.sh runtime/research
```

## Heartbeat interval

Default is 30 seconds. Inside a direct Docker command it can be overridden without changing research logic:

```powershell
docker compose --profile training run --rm `
  -e ML_RESEARCH_TRACE_HEARTBEAT_SECONDS=15 `
  ml_trainer `
  python -m app.research.runner --mode full --update-history
```

## Important

If a research run was already started before this overlay was applied, that already-running Python process will not gain tracing. Stop it and restart the research command if live progress output is desired.
