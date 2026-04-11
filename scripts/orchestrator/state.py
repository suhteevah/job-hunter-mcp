"""Atomic state I/O for the job orchestrator.

State lives in `.pipeline/state.json`. Reads are plain JSON; writes go through
an atomic temp-file + os.replace dance so a crash mid-write cannot corrupt
the file. The orchestrator runs unattended every 30 minutes, so corruption
recovery is not optional.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PIPELINE_DIR = Path(__file__).resolve().parents[2] / ".pipeline"
STATE_PATH = PIPELINE_DIR / "state.json"
FILTERS_PATH = PIPELINE_DIR / "filters.yaml"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict[str, Any]:
    """Load state.json. Raises if missing — orchestrator must scaffold first."""
    if not STATE_PATH.exists():
        raise FileNotFoundError(
            f"state.json missing at {STATE_PATH}. "
            "Run scripts/orchestrator/run.py --init to bootstrap."
        )
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    """Atomic write: temp file -> fsync -> os.replace."""
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".state-", suffix=".json.tmp", dir=str(PIPELINE_DIR)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STATE_PATH)
    except Exception:
        # Best-effort cleanup of the temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_filters() -> dict[str, Any]:
    """Load filters.yaml. Lazy-imports yaml so the dep is optional at runtime
    until scoring actually needs it."""
    import yaml  # noqa: PLC0415

    with FILTERS_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def record_run(state: dict[str, Any], run_summary: dict[str, Any]) -> None:
    """Update top-level run metrics. Mutates state in place."""
    state["last_run"] = utcnow_iso()
    state["last_run_id"] = state.get("last_run_id", 0) + 1
    state["metrics"]["runs_total"] = state["metrics"].get("runs_total", 0) + 1
    if run_summary.get("shortlist_hits", 0) > 0:
        state["metrics"]["runs_with_shortlist_hits"] = (
            state["metrics"].get("runs_with_shortlist_hits", 0) + 1
        )
    state["metrics"]["scrapes_completed"] = (
        state["metrics"].get("scrapes_completed", 0) + run_summary.get("scrapes", 0)
    )


def update_board(
    state: dict[str, Any],
    board: str,
    yield_count: int,
    error: str | None = None,
) -> None:
    """Update per-board metrics and roll the baseline yield (EMA, alpha=0.3)."""
    boards = state.setdefault("boards", {})
    b = boards.setdefault(
        board,
        {
            "baseline_yield": None,
            "last_yield": None,
            "last_run": None,
            "last_error": None,
            "consecutive_low_yields": 0,
        },
    )
    b["last_yield"] = yield_count
    b["last_run"] = utcnow_iso()
    b["last_error"] = error
    if b["baseline_yield"] is None:
        b["baseline_yield"] = float(yield_count)
    else:
        # Exponential moving average — adapts but does not whipsaw.
        b["baseline_yield"] = round(
            0.3 * float(yield_count) + 0.7 * float(b["baseline_yield"]), 2
        )


if __name__ == "__main__":
    # Smoke test: load + re-save state, prove atomic write works.
    s = load_state()
    save_state(s)
    print(f"OK — state has {len(s.get('boards', {}))} boards tracked")
