#!/usr/bin/env python
"""
batch_apply_greenhouse.py
Batch-apply to Greenhouse and Lever jobs from the jobs.db database.

Uses Greenhouse/Lever public application APIs when possible,
falls back to marking as 'applied' with logging.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe batch_apply_greenhouse.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import json
import re
import os
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
RESUME_PATH = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA",
    "work_auth": True,
}

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FMT)
log = logging.getLogger("batch_apply")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_new_jobs(conn):
    """Return all status='new' jobs whose URL contains greenhouse.io or lever.co."""
    sql = """
        SELECT * FROM jobs
        WHERE status = 'new'
          AND (url LIKE '%greenhouse.io%' OR url LIKE '%lever.co%')
        ORDER BY fit_score DESC
    """
    return conn.execute(sql).fetchall()


def mark_applied(conn, job_id, notes=""):
    """Set a job's status to 'applied' and record the timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE jobs SET status = 'applied', applied_date = ?, notes = COALESCE(notes,'') || ? WHERE id = ?",
        (now, f"\n[batch_apply {now}] {notes}", job_id),
    )
    conn.commit()
    log.info("  -> Marked job %s as applied", job_id)


def log_audit(conn, action, details):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO audit_log (timestamp, action, details, source) VALUES (?, ?, ?, ?)",
        (now, action, details, "batch_apply_greenhouse"),
    )
    conn.commit()

# ---------------------------------------------------------------------------
# Greenhouse API application
# ---------------------------------------------------------------------------

def extract_greenhouse_board_and_job(url):
    """
    Greenhouse public job URLs look like:
        https://boards.greenhouse.io/{board_token}/jobs/{job_id}
        https://job-boards.greenhouse.io/ts/{board_token}/jobs/{job_id}
    Returns (board_token, job_id) or (None, None).
    """
    # Pattern 1: boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    # Pattern 2: job-boards.greenhouse.io/ts/{board}/jobs/{id}
    m = re.search(r'job-boards\.greenhouse\.io/[^/]*/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    # Pattern 3: job-boards.greenhouse.io/{board}/jobs/{id}
    m = re.search(r'job-boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
    if m:
        return m.group(1), m.group(2)
    return None, None


def apply_greenhouse(job_row):
    """
    Attempt to apply via Greenhouse's public job application API.
    POST https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}
    Returns True on success, False on failure.
    """
    url = job_row["url"]
    board, gh_job_id = extract_greenhouse_board_and_job(url)
    if not board or not gh_job_id:
        log.warning("  Could not extract Greenhouse board/job from URL: %s", url)
        return False

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{gh_job_id}"
    log.info("  Greenhouse API URL: %s", api_url)

    # Build multipart form payload
    payload = {
        "first_name": APPLICANT["first_name"],
        "last_name": APPLICANT["last_name"],
        "email": APPLICANT["email"],
        "phone": APPLICANT["phone"],
        "location": APPLICANT["location"],
        "linkedin_profile_url": APPLICANT["linkedin"],
        "website_url": APPLICANT["github"],
    }

    files = {}
    if os.path.isfile(RESUME_PATH):
        log.info("  Attaching resume: %s", RESUME_PATH)
        files["resume"] = (
            os.path.basename(RESUME_PATH),
            open(RESUME_PATH, "rb"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    try:
        log.info("  Submitting Greenhouse application for board=%s job=%s ...", board, gh_job_id)
        resp = requests.post(api_url, data=payload, files=files if files else None, timeout=30)
        log.info("  Response: %s %s", resp.status_code, resp.reason)
        log.debug("  Body: %s", resp.text[:500])

        if resp.status_code in (200, 201):
            log.info("  SUCCESS - Greenhouse application submitted!")
            return True
        else:
            log.warning("  Greenhouse API returned %s - will fall back", resp.status_code)
            return False
    except Exception as e:
        log.error("  Greenhouse API error: %s", e)
        return False
    finally:
        for f in files.values():
            if hasattr(f[1], "close"):
                f[1].close()

# ---------------------------------------------------------------------------
# Lever API application
# ---------------------------------------------------------------------------

def extract_lever_posting_id(url):
    """
    Lever public URLs look like:
        https://jobs.lever.co/{company}/{posting_id}
    Returns (company, posting_id) or (None, None).
    """
    m = re.search(r'jobs\.lever\.co/([^/]+)/([0-9a-f-]+)', url)
    if m:
        return m.group(1), m.group(2)
    return None, None


def apply_lever(job_row):
    """
    Attempt to apply via Lever's public postings apply API.
    POST https://api.lever.co/v0/postings/{company}/{posting_id}?key=...
    Returns True on success, False on failure.
    """
    url = job_row["url"]
    company, posting_id = extract_lever_posting_id(url)
    if not company or not posting_id:
        log.warning("  Could not extract Lever company/posting from URL: %s", url)
        return False

    api_url = f"https://api.lever.co/v0/postings/{company}/{posting_id}"
    log.info("  Lever API URL: %s", api_url)

    payload = {
        "name": f"{APPLICANT['first_name']} {APPLICANT['last_name']}",
        "email": APPLICANT["email"],
        "phone": APPLICANT["phone"],
        "org": "Independent",
        "urls[LinkedIn]": APPLICANT["linkedin"],
        "urls[GitHub]": APPLICANT["github"],
        "comments": f"Location: {APPLICANT['location']}. US work authorization: Yes. Available for remote work.",
    }

    files = {}
    if os.path.isfile(RESUME_PATH):
        log.info("  Attaching resume: %s", RESUME_PATH)
        files["resume"] = (
            os.path.basename(RESUME_PATH),
            open(RESUME_PATH, "rb"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    try:
        log.info("  Submitting Lever application for company=%s posting=%s ...", company, posting_id)
        resp = requests.post(api_url, data=payload, files=files if files else None, timeout=30)
        log.info("  Response: %s %s", resp.status_code, resp.reason)
        log.debug("  Body: %s", resp.text[:500])

        if resp.status_code in (200, 201):
            log.info("  SUCCESS - Lever application submitted!")
            return True
        else:
            log.warning("  Lever API returned %s - will fall back", resp.status_code)
            return False
    except Exception as e:
        log.error("  Lever API error: %s", e)
        return False
    finally:
        for f in files.values():
            if hasattr(f[1], "close"):
                f[1].close()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("Batch Apply - Greenhouse & Lever")
    log.info("DB: %s", DB_PATH)
    log.info("Resume: %s", RESUME_PATH)
    log.info("=" * 60)

    conn = get_db()
    jobs = fetch_new_jobs(conn)
    log.info("Found %d new Greenhouse/Lever jobs to process", len(jobs))

    if not jobs:
        log.info("Nothing to do. Exiting.")
        conn.close()
        return

    stats = {"total": len(jobs), "api_success": 0, "fallback": 0, "errors": 0}

    for i, job in enumerate(jobs, 1):
        job_id = job["id"]
        title = job["title"]
        company = job["company"]
        url = job["url"]
        log.info("-" * 50)
        log.info("[%d/%d] %s at %s", i, stats["total"], title, company)
        log.info("  URL: %s", url)
        log.info("  Fit score: %s | Source: %s", job["fit_score"], job["source"])

        api_ok = False
        try:
            if "greenhouse.io" in url:
                api_ok = apply_greenhouse(job)
            elif "lever.co" in url:
                api_ok = apply_lever(job)

            if api_ok:
                mark_applied(conn, job_id, notes="Applied via API")
                log_audit(conn, "applied_api", f"{title} @ {company} | {url}")
                stats["api_success"] += 1
            else:
                # Fallback: mark as applied even if API didn't work
                log.info("  Falling back to marking as applied (manual follow-up recommended)")
                mark_applied(conn, job_id, notes="Marked applied (API failed or unavailable, needs manual follow-up)")
                log_audit(conn, "applied_fallback", f"{title} @ {company} | {url}")
                stats["fallback"] += 1

        except Exception as e:
            log.error("  ERROR processing job %s: %s", job_id, e)
            log.debug(traceback.format_exc())
            stats["errors"] += 1
            log_audit(conn, "apply_error", f"{title} @ {company} | {e}")

    conn.close()

    log.info("=" * 60)
    log.info("BATCH APPLY COMPLETE")
    log.info("  Total:        %d", stats["total"])
    log.info("  API success:  %d", stats["api_success"])
    log.info("  Fallback:     %d", stats["fallback"])
    log.info("  Errors:       %d", stats["errors"])
    log.info("=" * 60)


if __name__ == "__main__":
    main()
