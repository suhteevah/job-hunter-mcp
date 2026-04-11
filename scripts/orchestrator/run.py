"""Job Hunter Orchestrator — main entry point.

Runs every 30 minutes via Windows Task Scheduler. On each invocation:
  1. Load state from .pipeline/state.json
  2. Trigger ATS scrape (mega_pipeline.py --scrape) and parallel board diffs
  3. Score everything against .pipeline/filters.yaml (HYPER-SELECTIVE)
  4. Detect bypass-worthy yield drops
  5. Write the curated shortlist to .pipeline/shortlist/current.md
  6. Append a run section to .pipeline/reports/YYYY-MM-DD.md
  7. Save state atomically and exit

NEVER asks questions. NEVER auto-applies. Sniper-mode posture: surface, do
not act. The shortlist is the only apply-side surface, and it requires
manual review before any connect is spent or any application submitted.

Usage:
  python scripts/orchestrator/run.py            # full run
  python scripts/orchestrator/run.py --dry-run  # everything except scrape trigger
  python scripts/orchestrator/run.py --no-scrape # skip the mega_pipeline subprocess
"""
from __future__ import annotations

import argparse
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Make sibling modules importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from boards import dispatch_all, get_new_ats_jobs, scan_upwork_emails  # noqa: E402
from bypass_detector import detect_yield_drops  # noqa: E402
from reporter import append_run_section  # noqa: E402
from scoring import score_ats, score_upwork  # noqa: E402
from shortlist import write_shortlist  # noqa: E402
from state import (  # noqa: E402
    PIPELINE_DIR,
    load_filters,
    load_state,
    record_run,
    save_state,
    update_board,
    utcnow_iso,
)

LOG_DIR = PIPELINE_DIR / "logs"


def _should_trigger_full_scrape(state: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Decide whether to call mega_pipeline.py --scrape this run.

    Default: only every `scrape.full_scrape_interval_hours` hours. Between
    scrapes, the orchestrator runs in IMAP+DB-diff-only mode (fast).

    This is the key decoupling: Upwork polling stays at 30min, but the
    heavy ATS HTTP refresh only happens 4× per day.
    """
    interval_hours = (
        filters.get("scrape", {}).get("full_scrape_interval_hours", 6)
    )
    last = state.get("scrape", {}).get("last_full_scrape_at")
    if last is None:
        # First run ever — DON'T trigger heavy scrape immediately. Mark
        # the cursor to "now" so the next scrape happens after one full
        # interval has elapsed. This gets the user fast IMAP polling
        # immediately and lets the heavy scrape ramp up gracefully.
        state.setdefault("scrape", {})["last_full_scrape_at"] = utcnow_iso()
        return False
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return True
    elapsed = datetime.now(timezone.utc) - last_dt
    return elapsed.total_seconds() / 3600.0 >= interval_hours


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"orchestrator-{stamp}.log"

    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if module is reloaded
    logger.handlers.clear()

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger


def _no_scrape_dispatch(state: dict[str, Any], reason: str = "no-scrape mode") -> dict[str, Any]:
    """Dispatch without triggering mega_pipeline.

    Still does the IMAP scan and the SQLite diff queries. Used when the
    interval gate has not elapsed OR when --no-scrape is passed.
    """
    results: dict[str, Any] = {
        "scrape_ok": True,
        "scrape_msg": f"(skipped: {reason})",
        "boards": {},
    }

    upwork_jobs, upwork_err = scan_upwork_emails()
    results["boards"]["upwork_email"] = {"jobs": upwork_jobs, "error": upwork_err}

    for src in ("greenhouse", "ashby", "lever"):
        try:
            since = state.get("boards", {}).get(src, {}).get("last_run")
            results["boards"][src] = {
                "jobs": get_new_ats_jobs(src, since),
                "error": None,
            }
        except Exception as e:
            results["boards"][src] = {"jobs": [], "error": str(e)}

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Job Hunter Orchestrator")
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip the mega_pipeline scrape subprocess (faster, IMAP+DB only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except writing state and shortlist (no side effects)",
    )
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Orchestrator run starting")
    logger.info(
        "Flags: no_scrape=%s dry_run=%s", args.no_scrape, args.dry_run
    )

    try:
        state = load_state()
    except Exception as e:
        logger.error("Failed to load state: %s", e)
        return 1

    try:
        filters = load_filters()
    except Exception as e:
        logger.error("Failed to load filters: %s", e)
        return 1

    # ─── Phase 1: Scrape + diff ────────────────────────────────────────────
    logger.info("Phase 1: scrape + per-board diff")
    do_full_scrape = (not args.no_scrape) and _should_trigger_full_scrape(
        state, filters
    )
    if do_full_scrape:
        logger.info("  full ATS scrape: YES (interval elapsed)")
        dispatch = dispatch_all(state)
        state.setdefault("scrape", {})
        state["scrape"]["last_full_scrape_at"] = utcnow_iso()
        state["scrape"]["last_full_scrape_status"] = (
            "ok" if dispatch["scrape_ok"] else "failed"
        )
        if dispatch["scrape_ok"]:
            state["scrape"]["consecutive_failures"] = 0
        else:
            state["scrape"]["consecutive_failures"] = (
                state["scrape"].get("consecutive_failures", 0) + 1
            )
    else:
        if args.no_scrape:
            logger.info("  full ATS scrape: SKIPPED (--no-scrape)")
            dispatch = _no_scrape_dispatch(state, reason="--no-scrape flag")
        else:
            logger.info("  full ATS scrape: SKIPPED (interval not elapsed)")
            dispatch = _no_scrape_dispatch(state, reason="interval not elapsed")
    logger.info(
        "scrape_ok=%s, msg=%s",
        dispatch["scrape_ok"],
        (dispatch["scrape_msg"] or "")[:120],
    )
    for board, data in dispatch["boards"].items():
        logger.info(
            "  %s: %d jobs, err=%s",
            board,
            len(data["jobs"]),
            data["error"],
        )
        update_board(state, board, len(data["jobs"]), data["error"])

    # ─── Phase 2: Score + filter ───────────────────────────────────────────
    logger.info("Phase 2: hyper-selective scoring")
    upwork_results = [
        score_upwork(j, filters)
        for j in dispatch["boards"].get("upwork_email", {}).get("jobs", [])
    ]
    ats_results: list[Any] = []
    for src in ("greenhouse", "ashby", "lever"):
        for j in dispatch["boards"].get(src, {}).get("jobs", []):
            ats_results.append(score_ats(j, filters))

    upwork_passes = [r for r in upwork_results if r.passed]
    ats_passes = [r for r in ats_results if r.passed]
    near_misses = [
        r
        for r in (upwork_results + ats_results)
        if not r.passed and r.composite >= 80
    ]

    logger.info(
        "Upwork: %d scanned, %d passed, %d near-miss",
        len(upwork_results),
        len(upwork_passes),
        sum(1 for r in upwork_results if not r.passed and r.composite >= 80),
    )
    logger.info(
        "ATS:    %d scanned, %d passed, %d near-miss",
        len(ats_results),
        len(ats_passes),
        sum(1 for r in ats_results if not r.passed and r.composite >= 80),
    )

    # ─── Phase 3: Bypass detector ──────────────────────────────────────────
    logger.info("Phase 3: bypass detector")
    bypass_alerts, _ = detect_yield_drops(state, dispatch, filters)
    if bypass_alerts:
        logger.warning("Bypass alerts: %d", len(bypass_alerts))
        for a in bypass_alerts:
            logger.warning("  %s", a)

    # ─── Phase 4: Write shortlist + report ─────────────────────────────────
    if not args.dry_run:
        logger.info("Phase 4: writing shortlist + report")
        connects = state.get("upwork", {}).get("connects_remaining", 18)
        try:
            sl_path = write_shortlist(
                upwork_passes,
                ats_passes,
                near_misses=near_misses,
                upwork_connects_remaining=connects,
            )
            logger.info("  shortlist -> %s", sl_path)
        except Exception as e:
            logger.error("  shortlist write failed: %s", e)
            logger.error(traceback.format_exc())

        try:
            rp_path = append_run_section(
                state,
                dispatch,
                upwork_passes,
                ats_passes,
                near_misses,
                bypass_alerts,
            )
            logger.info("  report    -> %s", rp_path)
        except Exception as e:
            logger.error("  report write failed: %s", e)
            logger.error(traceback.format_exc())

        # Update top-level state metrics
        state["shortlist"]["current_count"] = len(upwork_passes) + len(ats_passes)
        state["shortlist"]["last_updated"] = utcnow_iso()
        state["shortlist"]["items_surfaced_lifetime"] = (
            state["shortlist"].get("items_surfaced_lifetime", 0)
            + len(upwork_passes)
            + len(ats_passes)
        )
        record_run(
            state,
            {
                "shortlist_hits": len(upwork_passes) + len(ats_passes),
                "scrapes": 1 if dispatch["scrape_ok"] else 0,
            },
        )

        # ─── Phase 5: Atomic state save ────────────────────────────────────
        try:
            save_state(state)
            logger.info("State saved (run #%d)", state["last_run_id"])
        except Exception as e:
            logger.error("State save FAILED: %s", e)
            return 2
    else:
        logger.info("--dry-run: skipping shortlist/report/state writes")

    logger.info("Orchestrator run complete")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
