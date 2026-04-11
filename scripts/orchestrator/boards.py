"""Board scraper dispatch for the orchestrator.

Each function returns a normalized list of job dicts and a yield count, plus
any error string. Wraps existing scripts — does NOT reimplement scrapers.

NEVER calls anything that submits applications. This file is read-only on
the apply side, by design (sniper mode).
"""
from __future__ import annotations

import email
import imaplib
import os
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.header import decode_header
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(r"C:\Users\Matt\.job-hunter-mcp\jobs.db")
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
MEGA_PIPELINE = PROJECT_ROOT / "scripts" / "swarm" / "mega_pipeline.py"

GMAIL_USER = "ridgecellrepair@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "yzpn qern vrax fvta")

# ATS sources we monitor in the database. Defense sources are blocked on
# manual account creation; aggregators have low ROI to resolve. See
# bypass-library.md for the rationale.
ATS_SOURCES = ("greenhouse", "ashby", "lever")


# ─── Scrape trigger ────────────────────────────────────────────────────────


def trigger_ats_scrape(timeout_sec: int = 600) -> tuple[bool, str]:
    """Run `mega_pipeline.py --scrape` to refresh the SQLite jobs table.

    The mega_pipeline script is the source of truth for scraping logic — we
    just shell out to it. Output is captured for the orchestrator log; we
    do NOT stream it to stdout (orchestrator runs unattended).
    """
    try:
        proc = subprocess.run(
            [str(VENV_PYTHON), str(MEGA_PIPELINE), "--scrape"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(PROJECT_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            return False, f"mega_pipeline --scrape exited {proc.returncode}: {proc.stderr[-500:]}"
        return True, proc.stdout[-1000:]
    except subprocess.TimeoutExpired:
        return False, f"mega_pipeline --scrape timed out after {timeout_sec}s"
    except Exception as e:
        return False, f"mega_pipeline --scrape failed: {e}"


# ─── DB diff per ATS source ────────────────────────────────────────────────


def get_new_ats_jobs(source: str, since_iso: str | None) -> list[dict[str, Any]]:
    """Pull jobs added to the DB since the last orchestrator run for this source.

    Filters at the SQL level: only `status='new'` (so jobs we already applied
    to or marked expired are skipped) and `date_found > since_iso` if a
    cursor exists. On the first run (no cursor) we cap at the most recent 200
    so we don't blast the scoring layer with everything in the DB.
    """
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    if since_iso:
        cur.execute(
            """
            SELECT id, source, title, company, url, location, salary,
                   description, tags, date_posted, date_found, fit_score,
                   salary_min, salary_max
            FROM jobs
            WHERE source = ?
              AND status = 'new'
              AND date_found > ?
            ORDER BY date_found DESC
            """,
            (source, since_iso),
        )
    else:
        cur.execute(
            """
            SELECT id, source, title, company, url, location, salary,
                   description, tags, date_posted, date_found, fit_score,
                   salary_min, salary_max
            FROM jobs
            WHERE source = ?
              AND status = 'new'
            ORDER BY date_found DESC
            LIMIT 200
            """,
            (source,),
        )
    rows = [dict(r) for r in cur.fetchall()]
    db.close()
    return rows


# ─── Upwork email IMAP scan ────────────────────────────────────────────────


_UPWORK_URL_RE = re.compile(r"https://www\.upwork\.com/jobs/~\w+")
_SPENT_RE = re.compile(r"\$([\d,.]+[KMkm]?)\s*spent", re.IGNORECASE)
_RATING_RE = re.compile(r"(\d\.\d{1,2})\s+\$[\d,.]+[KMkm]?\s*spent", re.IGNORECASE)
_PAYMENT_VERIFIED_RE = re.compile(r"Payment\s+verified", re.IGNORECASE)
_PROPOSALS_RE = re.compile(r"(\d+)\s+proposals?", re.IGNORECASE)
_EXPERIENCE_RE = re.compile(r"\b(Entry level|Intermediate|Expert)\b", re.IGNORECASE)
_DURATION_RE = re.compile(r"(>\s*\d+\s*month[s]?|<\s*\d+\s*month[s]?|\d+\s*month[s]?)")
_WEEKLY_HOURS_RE = re.compile(r"(>?\s*\d+\s*hr/wk)", re.IGNORECASE)
_POSTED_RE = re.compile(r"Posted on\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})")
# Country line: appears between rating/spent and the skills list. Tight pattern.
_COUNTRY_RE = re.compile(
    r"\$[\d,.]+[KMkm]?\s*spent\s+([A-Z][A-Za-z .'-]{1,40})\s+(?:Python|Data|Machine|Artificial|JavaScript|TypeScript|AI|Claude|API|Node|React|HTML|Generative)"
)


def _parse_dollar(s: str) -> float | None:
    """'$5K' -> 5000.0, '$1,250' -> 1250.0, etc. None if unparseable."""
    s = s.strip().replace(",", "").lstrip("$")
    mult = 1.0
    if s.endswith("K") or s.endswith("k"):
        mult = 1_000.0
        s = s[:-1]
    elif s.endswith("M") or s.endswith("m"):
        mult = 1_000_000.0
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _extract_hourly(text: str) -> tuple[float | None, float | None]:
    """Returns (low, high) hourly USD if a range is present, else (val, val) for single."""
    m = re.search(r"Hourly:\s*\$([\d,.]+)\s*-\s*\$([\d,.]+)", text)
    if m:
        return _parse_dollar(m.group(1)), _parse_dollar(m.group(2))
    m = re.search(r"Hourly:\s*\$([\d,.]+)", text)
    if m:
        v = _parse_dollar(m.group(1))
        return v, v
    return None, None


def _extract_fixed(text: str) -> float | None:
    m = re.search(r"Fixed:\s*\$([\d,]+)", text)
    return _parse_dollar(m.group(1)) if m else None


def scan_upwork_emails(
    since_imap_date: str = "10-Apr-2026",
    max_messages: int = 100,
    max_retries: int = 2,
) -> tuple[list[dict[str, Any]], str | None]:
    """Scan unread Upwork 'New job' alert emails via IMAP.

    Returns (jobs, error). Retries on transient SSL/socket errors which
    Gmail IMAP throws periodically — those are not real failures, just
    flaky connections.
    """
    last_err: str | None = None
    for attempt in range(max_retries + 1):
        jobs, err = _scan_upwork_emails_once(since_imap_date, max_messages)
        if err is None:
            return jobs, None
        last_err = err
        # Only retry on transient socket/SSL errors, not on auth failures
        if not any(
            sig in err.lower()
            for sig in ("ssl", "eof", "timeout", "reset", "broken pipe", "connection")
        ):
            break
    return [], last_err


def _scan_upwork_emails_once(
    since_imap_date: str,
    max_messages: int,
) -> tuple[list[dict[str, Any]], str | None]:
    """Single IMAP scan attempt — wrapped by scan_upwork_emails for retries."""
    jobs: list[dict[str, Any]] = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        result, data = mail.search(
            None,
            f'(UNSEEN FROM "donotreply@upwork.com" SUBJECT "New job" SINCE "{since_imap_date}")',
        )
        if result != "OK":
            mail.logout()
            return [], f"IMAP search failed: {result}"

        ids = data[0].split()[:max_messages]

        for mid in ids:
            res, raw = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)] BODY.PEEK[TEXT])")
            if res != "OK" or not raw:
                continue

            # raw is a list of tuples; the header part and the body part are
            # separate entries. Defensively pull both.
            hdr_text = ""
            body_raw = ""
            for entry in raw:
                if isinstance(entry, tuple) and len(entry) >= 2 and entry[1]:
                    chunk = entry[1].decode("utf-8", "replace")
                    if "Subject:" in chunk or "Date:" in chunk:
                        hdr_text += chunk
                    else:
                        body_raw += chunk

            # Strip HTML and quoted-printable soft-breaks for clean field
            # extraction. The text-plain section is what we actually want
            # but multipart MIME interleaves both.
            body_text = re.sub(r"=\r?\n", "", body_raw)  # qp soft breaks
            body_text = re.sub(r"<[^>]+>", " ", body_text)  # html tags
            body_text = re.sub(r"\s+", " ", body_text).strip()

            subj_m = re.search(r"Subject:\s*(.+)", hdr_text)
            date_m = re.search(r"Date:\s*(.+)", hdr_text)
            raw_subject = subj_m.group(1).strip() if subj_m else "(no title)"
            # Decode MIME-encoded subjects (=?UTF-8?q?...?=) properly.
            decoded_parts = decode_header(raw_subject)
            title = "".join(
                (p.decode(enc or "utf-8", "replace") if isinstance(p, bytes) else p)
                for p, enc in decoded_parts
            ).replace("New job: ", "").strip()
            posted_email = date_m.group(1).strip()[:31] if date_m else ""

            url_m = _UPWORK_URL_RE.search(body_text)
            url = url_m.group(0) if url_m else ""

            hourly_low, hourly_high = _extract_hourly(body_text)
            fixed = _extract_fixed(body_text)

            spent_m = _SPENT_RE.search(body_text)
            client_spent = _parse_dollar("$" + spent_m.group(1)) if spent_m else None

            rating_m = _RATING_RE.search(body_text)
            client_rating = float(rating_m.group(1)) if rating_m else None

            payment_verified = bool(_PAYMENT_VERIFIED_RE.search(body_text))

            proposals_m = _PROPOSALS_RE.search(body_text)
            proposals = int(proposals_m.group(1)) if proposals_m else None

            exp_m = _EXPERIENCE_RE.search(body_text)
            experience = exp_m.group(1) if exp_m else None

            dur_m = _DURATION_RE.search(body_text)
            duration = dur_m.group(1).strip() if dur_m else None

            hrs_m = _WEEKLY_HOURS_RE.search(body_text)
            weekly_hours = hrs_m.group(1).strip() if hrs_m else None

            posted_m = _POSTED_RE.search(body_text)
            posted_on = posted_m.group(1) if posted_m else None

            ctry_m = _COUNTRY_RE.search(body_text)
            client_country = ctry_m.group(1).strip() if ctry_m else None

            # IMPORTANT: do NOT mark as seen here. The orchestrator decides
            # whether to mark seen based on whether the job hit the shortlist.
            # Phase 1: leave unread so the user can also see them in Gmail.

            jobs.append(
                {
                    "source": "upwork_email",
                    "title": title,
                    "url": url,
                    "date_posted_raw": posted_email,
                    "posted_on": posted_on,
                    "hourly_low": hourly_low,
                    "hourly_high": hourly_high,
                    "fixed_budget": fixed,
                    "client_spent": client_spent,
                    "client_rating": client_rating,
                    "client_country": client_country,
                    "payment_verified": payment_verified,
                    "proposals_count": proposals,
                    "experience_level": experience,
                    "duration": duration,
                    "weekly_hours": weekly_hours,
                    "description": body_text[:3000],
                    "imap_message_id": mid.decode("ascii", "replace"),
                }
            )

        mail.logout()
        return jobs, None
    except Exception as e:
        return [], f"IMAP scan failed: {e}"


# ─── Top-level dispatch ────────────────────────────────────────────────────


def dispatch_all(state: dict[str, Any]) -> dict[str, Any]:
    """Run scrape trigger + parallel board diffs.

    Returns:
        {
            "scrape_ok": bool,
            "scrape_msg": str,
            "boards": {
                "upwork_email": {"jobs": [...], "error": None},
                "greenhouse":   {"jobs": [...], "error": None},
                "ashby":        {"jobs": [...], "error": None},
                "lever":        {"jobs": [...], "error": None},
            },
        }
    """
    results: dict[str, Any] = {"scrape_ok": False, "scrape_msg": "", "boards": {}}

    # Step 1: trigger ATS scrape (sequential, mega_pipeline parallelizes internally).
    ok, msg = trigger_ats_scrape()
    results["scrape_ok"] = ok
    results["scrape_msg"] = msg

    # Step 2: per-board diff queries in parallel + Upwork IMAP scan.
    def _ats_task(src: str) -> tuple[str, list[dict[str, Any]], str | None]:
        try:
            since = state.get("boards", {}).get(src, {}).get("last_run")
            return src, get_new_ats_jobs(src, since), None
        except Exception as e:
            return src, [], f"db diff failed: {e}"

    def _upwork_task() -> tuple[str, list[dict[str, Any]], str | None]:
        jobs, err = scan_upwork_emails()
        return "upwork_email", jobs, err

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_ats_task, s) for s in ATS_SOURCES]
        futures.append(pool.submit(_upwork_task))
        for fut in as_completed(futures):
            board, jobs, err = fut.result()
            results["boards"][board] = {"jobs": jobs, "error": err}

    return results


if __name__ == "__main__":
    # Smoke test: dispatch with empty state, print yields per board.
    # Skips the actual scrape trigger to keep this fast.
    print("Smoke test — IMAP scan + DB diffs (no mega_pipeline trigger)")
    print()

    fake_state: dict[str, Any] = {"boards": {}}
    print("Upwork IMAP:")
    jobs, err = scan_upwork_emails()
    print(f"  yield: {len(jobs)}  err: {err}")
    if jobs:
        sample = jobs[0]
        print(f"  sample title: {sample['title'][:80]}")
        print(f"  url: {sample['url']}")
        print(
            f"  budget: hr=${sample['hourly_low']}-${sample['hourly_high']} "
            f"fx=${sample['fixed_budget']}"
        )
        print(
            f"  client: spent=${sample['client_spent']} rating={sample['client_rating']} "
            f"verified={sample['payment_verified']} proposals={sample['proposals_count']}"
        )
    print()
    for src in ATS_SOURCES:
        rows = get_new_ats_jobs(src, None)
        print(f"{src}: {len(rows)} new jobs (no cursor, capped at 200)")
