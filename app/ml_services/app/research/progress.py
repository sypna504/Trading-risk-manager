from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class ResearchProgress:
    """Small console/file tracer for long-running research jobs.

    It is intentionally observational only: no model-selection or research
    decisions depend on these events. Console output is flushed immediately and
    the same events are persisted under the configured research output root.
    """

    def __init__(self, output_root: Path) -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.output_root / "PROGRESS.jsonl"
        self.current_path = self.output_root / "PROGRESS.json"
        self.started = time.monotonic()
        self.heartbeat_seconds = max(
            5,
            int(os.getenv("ML_RESEARCH_TRACE_HEARTBEAT_SECONDS", "30")),
        )
        self._lock = threading.Lock()
        self._model_experiment_count = 0
        self._current_phase: dict[str, Any] | None = None
        self._stop = threading.Event()
        self._phase_thread = threading.Thread(
            target=self._phase_heartbeat,
            name="research-phase-heartbeat",
            daemon=True,
        )
        self._phase_thread.start()


    def _phase_heartbeat(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            current = self._current_phase
            if not current:
                continue
            self.emit(
                "heartbeat",
                f"{current['message']} — still running",
                phase=current["name"],
                phase_number=current["number"],
                phase_total=current["total"],
                phase_elapsed_seconds=round(time.monotonic() - current["started"], 1),
            )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_current(self, payload: dict[str, Any]) -> None:
        temporary = self.current_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.current_path)

    def emit(self, event: str, message: str, **fields: Any) -> None:
        payload = {
            "timestamp": self._utc_now(),
            "elapsed_seconds": round(time.monotonic() - self.started, 2),
            "event": event,
            "message": message,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=False, default=str)
        pretty_elapsed = f"{payload['elapsed_seconds']:>8.1f}s"
        phase = fields.get("phase")
        prefix = f"[{pretty_elapsed}] [research]"
        if phase:
            prefix += f" [{phase}]"
        print(f"{prefix} {event.upper():<9} {message}", flush=True)
        with self._lock:
            with self.events_path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
            self._write_current(payload)


    @property
    def current_phase_name(self) -> str:
        if not self._current_phase:
            return "experiment"
        return str(self._current_phase["name"])

    def phase(self, number: int, total: int, name: str, message: str) -> None:
        self._current_phase = {
            "number": number,
            "total": total,
            "name": name,
            "message": message,
            "started": time.monotonic(),
        }
        self.emit(
            "phase",
            message,
            phase=name,
            phase_number=number,
            phase_total=total,
        )

    @contextmanager
    def task(self, name: str, message: str, *, phase: str | None = None, **fields: Any) -> Iterator[None]:
        if phase is None and self._current_phase:
            phase = str(self._current_phase["name"])
        if name == "model_experiment":
            self._model_experiment_count += 1
            fields = {"model_experiment_index": self._model_experiment_count, **fields}
            message = f"#{self._model_experiment_count} {message}"
        started = time.monotonic()
        stop = threading.Event()
        self.emit("start", message, phase=phase, task=name, **fields)

        def heartbeat() -> None:
            while not stop.wait(self.heartbeat_seconds):
                self.emit(
                    "heartbeat",
                    f"{message} — still running",
                    phase=phase,
                    task=name,
                    task_elapsed_seconds=round(time.monotonic() - started, 1),
                    **fields,
                )

        thread = threading.Thread(target=heartbeat, name=f"research-progress-{name}", daemon=True)
        thread.start()
        try:
            yield
        except Exception as error:
            stop.set()
            self.emit(
                "failed",
                f"{message}: {type(error).__name__}: {error}",
                phase=phase,
                task=name,
                task_elapsed_seconds=round(time.monotonic() - started, 2),
                **fields,
            )
            raise
        else:
            stop.set()
            self.emit(
                "done",
                message,
                phase=phase,
                task=name,
                task_elapsed_seconds=round(time.monotonic() - started, 2),
                **fields,
            )
        finally:
            stop.set()

    def experiment_result(self, row: dict[str, Any]) -> None:
        if row.get("error"):
            self.emit(
                "result",
                f"{row.get('experiment_id')} failed: {row['error']}",
                phase=str(row.get("phase") or "experiment"),
                experiment_id=row.get("experiment_id"),
                status="failed",
            )
            return
        values = []
        for label, key in (
            ("score", "score"),
            ("ROC", "roc_auc"),
            ("PR", "pr_auc"),
            ("PF", "profit_factor"),
            ("return", "portfolio_return"),
        ):
            value = row.get(key)
            if value is not None:
                try:
                    values.append(f"{label}={float(value):.4f}")
                except (TypeError, ValueError):
                    values.append(f"{label}={value}")
        suffix = " ".join(values)
        self.emit(
            "result",
            f"{row.get('experiment_id')} {suffix}".strip(),
            phase=str(row.get("phase") or "experiment"),
            experiment_id=row.get("experiment_id"),
            status="completed",
            score=row.get("score"),
            roc_auc=row.get("roc_auc"),
            pr_auc=row.get("pr_auc"),
            profit_factor=row.get("profit_factor"),
            portfolio_return=row.get("portfolio_return"),
        )

    def finish(self, *, research_result: str, experiment_count: int, promotion_ready: bool) -> None:
        self._current_phase = None
        self._stop.set()
        self.emit(
            "complete",
            f"research_result={research_result}; experiments={experiment_count}; promotion_ready={promotion_ready}",
            phase="final",
            research_result=research_result,
            experiment_count=experiment_count,
            promotion_ready=promotion_ready,
        )
