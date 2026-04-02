#!/usr/bin/env python
"""
indeed_enterprise_flare.py
Scrape Indeed for enterprise/defense company jobs via FlareSolverr CF bypass.
Targets: Honeywell, Boeing, Lockheed, Northrop, GD, L3Harris, MITRE, Booz Allen.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe indeed_enterprise_flare.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import hashlib
import json
import re
import time
import logging
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import urllib.parse

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
FLARE_URL = "http://localhost:8191/v1"

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("indeed_enterprise")

QUERIES = [
    ("Honeywell software engineer remote", "Honeywell"),
    ("Honeywell firmware engineer", "Honeywell"),
    ("Honeywell test engineer", "Honeywell"),
    ("Boeing software engineer remote", "Boeing"),
    ("Lockheed Martin software engineer remote", "Lockheed Martin"),
    ("Northrop Grumman software engineer remote", "Northrop Grumman"),
    ("General Dynamics IT engineer", "General Dynamics"),
    ("L3Harris software engineer", "L3Harris"),
    ("MITRE software engineer", "MITRE"),
    ("Booz Allen software engineer", "Booz Allen"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def job_exists_by_source_id(conn, source_id):
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE source_id = ? AND source = 'indeed'",
        (source_id,)
    ).fetchone()
    return row is not None


def url_exists(conn, url):
    row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
    return row is not None


def insert_job(conn, jd):
    if url_exists(conn, jd["url"]):
        return False
    if job_exists_by_source_id(conn, jd["source_id"]):
        return False
    job_id = hashlib.sha256(("indeed:" + jd["source_id"]).encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, source_id, title, company, url, location,
           salary, job_type, category, description, tags, date_posted, date_found,
           fit_score, fit_reason, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id, "indeed", jd["source_id"], jd["title"], jd["company"],
            jd["url"], jd["location"], None, None, "engineering",
            jd.get("description", ""), json.dumps(["indeed", "enterprise", "defense"]),
            None, now, jd.get("fit_score", 0.0), jd.get("fit_reason", ""), "new"
        )
    )
    conn.commit()
    return True


def score_job(title, company, location):
    score = 0
    t = (title or "").lower()
    c = (company or "").lower()
    loc = (location or "").lower()
    if re.search(r'\bsoftware engineer\b|\bsoftware developer\b', t):
        score += 25
    if re.search(r'\bfirmware\b|\bembedded\b', t):
        score += 30
    if re.search(r'\btest engineer\b|\bquality\b|\bqa\b', t):
        score += 20
    if re.search(r'\bai\b|\bmachine learning\b|\bml\b|\bllm\b', t):
        score += 35
    if re.search(r'\bpython\b|\brust\b|\bc\+\+\b', t):
        score += 15
    if re.search(r'\bsenior\b|\bstaff\b|\blead\b', t):
        score += 10
    if re.search(r'\bpcb\b|\bsoldering\b|\bhardware\b|\btest fixture\b', t):
        score += 20
    if re.search(r'\bremote\b', loc):
        score += 10
    # Defense/aerospace company bonus
    if re.search(r'honeywell|boeing|lockheed|northrop|l3harris|mitre|booz allen|general dynamics', c):
        score += 20
    return min(score, 100)


def flare_get(url):
    payload = json.dumps({
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 45000
    }).encode("utf-8")
    req = Request(
        FLARE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            status = data.get("status", "")
            if status != "ok":
                log.warning("FlareSolverr status: %s", status)
            solution = data.get("solution", {})
            return solution.get("response", "")
    except Exception as e:
        log.warning("FlareSolverr error for %s: %s", url, e)
        return ""


def parse_indeed_jobs(html, default_company):
    """Parse Indeed search results HTML. Returns list of job dicts."""
    jobs = []
    if not html:
        return jobs

    # Job keys embedded in HTML (16-char hex)
    job_keys = re.findall(r'data-jk=["\']([a-f0-9]{16})["\']', html)
    job_keys = list(dict.fromkeys(job_keys))  # dedupe preserving order

    if not job_keys:
        # Try JSON embedded data
        json_matches = re.findall(r'"jobKey"\s*:\s*"([a-f0-9]{16})"', html)
        job_keys = list(dict.fromkeys(json_matches))

    log.info("  Found %d unique job keys", len(job_keys))

    # Extract titles — multiple patterns
    titles = re.findall(r'"normTitle"\s*:\s*"([^"]+)"', html)
    if not titles:
        titles = re.findall(r'"jobTitle"\s*:\s*"([^"]+)"', html)
    if not titles:
        titles = re.findall(
            r'<span[^>]+class="[^"]*jobTitle[^"]*"[^>]*>\s*<span[^>]*>([^<]+)</span>',
            html
        )

    # Extract company names
    companies = re.findall(r'"companyName"\s*:\s*"([^"]+)"', html)
    if not companies:
        companies = re.findall(
            r'class="[^"]*companyName[^"]*"[^>]*>\s*<span[^>]*>([^<]+)</span>',
            html
        )

    # Extract locations
    locations = re.findall(r'"formattedLocation"\s*:\s*"([^"]+)"', html)
    if not locations:
        locations = re.findall(r'"jobLocationCity"\s*:\s*"([^"]+)"', html)
    if not locations:
        locations = re.findall(
            r'class="[^"]*companyLocation[^"]*"[^>]*>([^<]+)<',
            html
        )

    log.info("  Parsed: %d titles, %d companies, %d locations",
             len(titles), len(companies), len(locations))

    for i, jk in enumerate(job_keys):
        title = titles[i].strip() if i < len(titles) else f"{default_company} Position"
        company = companies[i].strip() if i < len(companies) else default_company
        location = locations[i].strip() if i < len(locations) else "United States"
        url = f"https://www.indeed.com/viewjob?jk={jk}"
        jobs.append({
            "source_id": jk,
            "title": title,
            "company": company,
            "url": url,
            "location": location,
            "fit_score": score_job(title, company, location),
            "fit_reason": f"Indeed enterprise/defense search: {default_company}",
        })

    return jobs


def main():
    log.info("=" * 70)
    log.info("INDEED ENTERPRISE SCRAPE via FlareSolverr")
    log.info("Queries: %d", len(QUERIES))
    log.info("=" * 70)

    # Check FlareSolverr is alive
    try:
        req = Request("http://localhost:8191/v1",
                      data=json.dumps({"cmd": "sessions.list"}).encode(),
                      headers={"Content-Type": "application/json"},
                      method="POST")
        with urlopen(req, timeout=5) as r:
            log.info("FlareSolverr alive: %s", r.status)
    except Exception as e:
        log.error("FlareSolverr not reachable at localhost:8191: %s", e)
        log.error("Continuing anyway — may still work for non-CF pages")

    conn = get_db()
    total_inserted = 0
    total_skipped = 0

    for query_text, company_display in QUERIES:
        log.info("")
        log.info("Searching Indeed: '%s'", query_text)
        encoded = urllib.parse.quote_plus(query_text)
        # filter=0 includes all listings, sort=date for freshness
        url = (
            f"https://www.indeed.com/jobs"
            f"?q={encoded}&remotejobs=1&filter=0&sort=date&limit=50"
        )
        log.info("  URL: %s", url)

        html = flare_get(url)
        if not html:
            log.warning("  No HTML returned from FlareSolverr, skipping")
            time.sleep(2)
            continue

        log.info("  HTML size: %d bytes", len(html))

        # Check if we got a CAPTCHA/block page
        if "captcha" in html.lower() or "are you a robot" in html.lower():
            log.warning("  CAPTCHA detected! Saving debug HTML.")
            debug_path = f"C:/Users/Matt/.job-hunter-mcp/debug_indeed_{company_display.replace(' ', '_')}.html"
            try:
                with open(debug_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(html[:10000])
            except Exception:
                pass
            time.sleep(5)
            continue

        jobs = parse_indeed_jobs(html, company_display)

        if not jobs:
            log.warning("  No jobs parsed from HTML")
            # Save debug snippet
            debug_path = f"C:/Users/Matt/.job-hunter-mcp/debug_indeed_{company_display.replace(' ', '_')}.html"
            try:
                with open(debug_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(html[:8000])
                log.info("  Saved 8KB debug HTML to %s", debug_path)
            except Exception:
                pass
        else:
            inserted = 0
            skipped = 0
            for jd in jobs:
                if insert_job(conn, jd):
                    inserted += 1
                    total_inserted += 1
                    log.info("    + %s | %s @ %s | score=%d",
                             jd["source_id"], jd["title"], jd["company"], jd["fit_score"])
                else:
                    skipped += 1
                    total_skipped += 1
            log.info("  Inserted: %d | Skipped/dup: %d", inserted, skipped)

        time.sleep(3)

    conn.close()

    print("")
    print("=== INDEED ENTERPRISE SCRAPE DONE ===")
    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped:  {total_skipped}")


if __name__ == "__main__":
    main()
