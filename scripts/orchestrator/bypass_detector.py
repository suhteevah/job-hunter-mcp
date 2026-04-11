"""Bypass-research detector.

Detects sustained drops in board scrape yield (a board returning <50% of its
EMA baseline for N consecutive runs) and writes an alert to
`.pipeline/bypass-library.md`. Does NOT write code or modify scrapers — that
stays human-in-the-loop.

The detector is conservative on purpose: false alarms (a quiet hour, a slow
posting day) would clutter the library and erode trust in the alerts.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[2] / ".pipeline"
BYPASS_LIBRARY = PIPELINE_DIR / "bypass-library.md"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def detect_yield_drops(
    state: dict[str, Any],
    dispatch_results: dict[str, Any],
    filters: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    """Compare each board's current yield against its EMA baseline.

    Returns (new_alerts, updated_state). The state mutation is in place but
    we also return it for clarity.
    """
    rules = filters.get("bypass_detector", {})
    threshold = rules.get("yield_drop_threshold", 0.5)
    min_consecutive = rules.get("min_consecutive_low_yields", 3)
    min_baseline = rules.get("min_baseline_for_alert", 10)
    monitored = rules.get("monitored_boards", [])

    new_alerts: list[str] = []
    boards = state.setdefault("boards", {})

    for board in monitored:
        bd = boards.get(board)
        if not bd:
            continue
        baseline = bd.get("baseline_yield")
        last_yield = bd.get("last_yield")
        if baseline is None or last_yield is None or baseline < min_baseline:
            # Not enough history yet, or board is normally low-volume.
            # Don't fire false alarms during EMA warm-up.
            bd["consecutive_low_yields"] = 0
            continue

        ratio = float(last_yield) / float(baseline)
        if ratio < threshold:
            bd["consecutive_low_yields"] = bd.get("consecutive_low_yields", 0) + 1
            if bd["consecutive_low_yields"] >= min_consecutive:
                # Suspected cause: pattern-match common scenarios
                error = bd.get("last_error") or ""
                cause = "unknown"
                if "cloudflare" in error.lower() or "cf" in error.lower():
                    cause = "Cloudflare challenge"
                elif "turnstile" in error.lower():
                    cause = "Turnstile bot check"
                elif "rate" in error.lower() or "429" in error:
                    cause = "rate limit / 429"
                elif "imap" in error.lower():
                    cause = "IMAP auth or connectivity"
                elif last_yield == 0:
                    cause = "complete block (zero yield)"
                else:
                    cause = "partial block (yield drop)"

                alert = (
                    f"{_utcnow()} | {board} | {last_yield}/{baseline:.0f} "
                    f"({ratio:.0%}) | suspected: {cause}"
                )
                new_alerts.append(alert)
                # Reset counter so we don't spam the same alert every run.
                bd["consecutive_low_yields"] = 0
        else:
            bd["consecutive_low_yields"] = 0

    if new_alerts:
        _append_alerts(new_alerts)
        # Also store in state so the report can show them.
        state.setdefault("bypass_alerts", []).extend(new_alerts)

    return new_alerts, state


def _append_alerts(alerts: list[str]) -> None:
    """Append alerts to the Alerts section of bypass-library.md.

    Locates the line `## Alerts (auto-written by orchestrator)` and inserts
    new alerts immediately after the placeholder line. Preserves the rest
    of the file.
    """
    if not BYPASS_LIBRARY.exists():
        return
    text = BYPASS_LIBRARY.read_text(encoding="utf-8")
    marker = "## Alerts (auto-written by orchestrator)"
    if marker not in text:
        # Append at end as fallback
        with BYPASS_LIBRARY.open("a", encoding="utf-8") as f:
            f.write("\n## Alerts (fallback)\n")
            for a in alerts:
                f.write(f"- {a}\n")
        return

    head, _, tail = text.partition(marker)
    # Strip the placeholder "(none yet — orchestrator has not run)" line.
    tail_lines = tail.splitlines()
    new_tail_lines = [tail_lines[0]] if tail_lines else [""]
    skipping_placeholder = True
    for line in tail_lines[1:]:
        if skipping_placeholder:
            if line.strip() in ("", "_(none yet — orchestrator has not run)_"):
                continue
            skipping_placeholder = False
        new_tail_lines.append(line)

    alert_block = ["", *(f"- {a}" for a in alerts), ""]
    new_text = head + marker + "\n" + "\n".join(alert_block + new_tail_lines)
    BYPASS_LIBRARY.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    # Smoke test with a fake low-yield scenario
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fake_state = {
        "boards": {
            "greenhouse": {
                "baseline_yield": 100.0,
                "last_yield": 5,
                "consecutive_low_yields": 2,
                "last_error": "",
            },
        },
    }
    fake_filters = {
        "bypass_detector": {
            "yield_drop_threshold": 0.5,
            "min_consecutive_low_yields": 3,
            "monitored_boards": ["greenhouse"],
        }
    }
    alerts, _ = detect_yield_drops(fake_state, {}, fake_filters)
    print(f"Alerts triggered: {len(alerts)}")
    for a in alerts:
        print(f"  {a}")
