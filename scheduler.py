"""
Job Hunter Scheduler Daemon
============================
Runs autonomously on a schedule:
  - Every 4 hours: Searches all job APIs with all presets
  - Every 30 min: Checks for approved emails to send via Gmail MCP
  - Continuous: Logs all activity for dashboard visibility

Usage:
  python scheduler.py              # Run one full cycle
  python scheduler.py --daemon     # Run continuously
  python scheduler.py --search     # Just run searches
  python scheduler.py --emails     # Just process email queue

On Windows, register with Task Scheduler for automatic runs.
"""
import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src import db, apis
from src.config import (
    SEARCH_PRESETS, SCHEDULER, DATA_DIR, LOG_FILE, USER_PROFILE
)
from src.gmail import run_email_cycle, process_approved_emails, check_inbox

# ============================================================
# LOGGING
# ============================================================
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), mode="a"),
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger("job_hunter.scheduler")


# ============================================================
# SEARCH CYCLE
# ============================================================
async def run_search_cycle():
    """Run all preset searches and save results."""
    logger.info("=" * 50)
    logger.info("SEARCH CYCLE STARTING")
    logger.info("=" * 50)

    jsearch_key = db.get_api_key("rapidapi")
    total_new = 0
    total_found = 0
    cycle_start = time.time()

    for preset_name, preset in SEARCH_PRESETS.items():
        logger.info(f"--- Running preset: {preset_name} ---")

        for query in preset.get("queries", []):
            cat = preset.get("categories", ["software-dev"])[0]
            try:
                result = await apis.search_all(query, jsearch_key, cat, 40)
                new_count = 0
                for job in result["jobs"]:
                    if db.upsert_job(job):
                        new_count += 1

                total_new += new_count
                total_found += result["total"]
                db.log_search(query, list(result["source_counts"].keys()),
                             result["total"], new_count)

                logger.info(f"  '{query}': {result['total']} found, {new_count} new")

                # Rate limit: don't hammer APIs
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"  '{query}' FAILED: {e}")
                db.audit("search_error", f"query='{query}' error={e}")

    elapsed = time.time() - cycle_start
    db.audit("search_cycle_complete",
             f"found={total_found} new={total_new} elapsed={elapsed:.1f}s")
    db.set_state("last_search", datetime.now(timezone.utc).isoformat())

    logger.info("=" * 50)
    logger.info(f"SEARCH CYCLE COMPLETE: {total_found} found, {total_new} new ({elapsed:.1f}s)")
    logger.info("=" * 50)

    # Log high-score jobs
    top_jobs = db.get_jobs(status="new", min_score=30, limit=10)
    if top_jobs:
        logger.info("TOP NEW MATCHES:")
        for j in top_jobs:
            logger.info(f"  [{j['fit_score']}] {j['title']} @ {j['company']} - {j['url']}")

    return {"total_found": total_found, "new_saved": total_new}


# ============================================================
# EMAIL PROCESSING (via Gmail SMTP + IMAP)
# ============================================================
async def process_emails():
    """Full email cycle: send approved emails via SMTP + check inbox via IMAP."""
    try:
        results = run_email_cycle()
        logger.info(f"Email cycle results: {json.dumps(results)}")
        return results
    except FileNotFoundError:
        logger.warning("secrets.json not found - skipping email cycle. "
                      "Copy secrets.json.example to secrets.json and fill in your credentials.")
        return {"sent": 0, "error": "no secrets.json"}
    except Exception as e:
        logger.error(f"Email cycle failed: {e}")
        return {"sent": 0, "error": str(e)}


# ============================================================
# AUTO COVER LETTER DRAFTING
# ============================================================
async def auto_draft_cover_letters():
    """Auto-draft cover letters for high-scoring new jobs."""
    if not SCHEDULER["auto_draft_cover_letters"]:
        return

    threshold = SCHEDULER["cover_letter_threshold"]
    jobs = db.get_jobs(status="new", min_score=threshold, limit=10)

    drafted = 0
    for job in jobs:
        if job.get("cover_letter"):
            continue  # Already has one

        # Generate a cover letter prompt context (Claude Code will refine)
        context = (
            f"DRAFT COVER LETTER NEEDED\n"
            f"Job: {job['title']} at {job['company']}\n"
            f"Score: {job['fit_score']} - {job['fit_reason']}\n"
            f"URL: {job['url']}\n"
            f"Description excerpt: {job.get('description', '')[:500]}\n\n"
            f"Applicant: {USER_PROFILE['name']}, {USER_PROFILE['title']}\n"
            f"Key skills match: {job['fit_reason']}\n"
        )

        db.update_job(job["id"], notes=f"[AUTO] Cover letter draft needed. Score={job['fit_score']}")
        db.update_job(job["id"], status="saved")
        drafted += 1
        logger.info(f"Flagged for cover letter: {job['title']} @ {job['company']} (score={job['fit_score']})")

    if drafted:
        db.audit("auto_draft", f"Flagged {drafted} jobs for cover letters (threshold={threshold})")
        logger.info(f"Flagged {drafted} jobs for cover letter drafting")


# ============================================================
# DAILY SUMMARY
# ============================================================
def generate_daily_summary() -> str:
    """Generate a daily summary for the dashboard."""
    stats = db.get_stats()
    top = db.get_jobs(min_score=30, limit=5)

    summary = [
        f"## Daily Job Hunt Summary - {datetime.now().strftime('%Y-%m-%d')}",
        f"",
        f"**Pipeline:** {stats['new']} new | {stats['saved']} saved | "
        f"{stats['applied']} applied | {stats['interviewing']} interviewing",
        f"**Total tracked:** {stats['total']} | **Avg score:** {stats['avg_score']}",
        f"**Pending emails:** {stats['pending_emails']} | **Sent:** {stats['sent_emails']}",
        f"",
        f"### Top Opportunities:",
    ]

    for j in top:
        summary.append(f"- [{j['fit_score']}] {j['title']} @ {j['company']} [{j['status']}]")

    return "\n".join(summary)


# ============================================================
# MAIN DAEMON LOOP
# ============================================================
async def run_full_cycle():
    """Run one complete cycle: search + emails + drafts."""
    logger.info("*** FULL CYCLE START ***")

    await run_search_cycle()
    await auto_draft_cover_letters()
    await process_emails()

    summary = generate_daily_summary()
    logger.info(summary)

    # Save summary
    summary_file = DATA_DIR / "latest_summary.md"
    with open(summary_file, "w") as f:
        f.write(summary)

    logger.info("*** FULL CYCLE COMPLETE ***")


async def daemon_loop():
    """Run continuously with configurable intervals."""
    logger.info("DAEMON MODE: Starting continuous operation")
    search_interval = SCHEDULER["search_interval_hours"] * 3600
    email_interval = SCHEDULER["email_check_interval_minutes"] * 60

    last_search = 0
    last_email = 0

    while True:
        now = time.time()

        if now - last_search >= search_interval:
            try:
                await run_search_cycle()
                await auto_draft_cover_letters()
                last_search = now
            except Exception as e:
                logger.error(f"Search cycle error: {e}")

        if now - last_email >= email_interval:
            try:
                await process_emails()
                last_email = now
            except Exception as e:
                logger.error(f"Email cycle error: {e}")

        # Sleep 60s between checks
        await asyncio.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="Job Hunter Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--search", action="store_true", help="Run search cycle only")
    parser.add_argument("--emails", action="store_true", help="Process email queue only")
    parser.add_argument("--summary", action="store_true", help="Generate daily summary")
    args = parser.parse_args()

    if args.daemon:
        asyncio.run(daemon_loop())
    elif args.search:
        asyncio.run(run_search_cycle())
    elif args.emails:
        asyncio.run(process_emails())
    elif args.summary:
        print(generate_daily_summary())
    else:
        asyncio.run(run_full_cycle())


if __name__ == "__main__":
    main()
