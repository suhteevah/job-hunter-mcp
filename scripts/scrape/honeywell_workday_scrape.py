"""
honeywell_workday_scrape.py
============================
Scrape Honeywell's Workday career site for software/firmware/test engineer jobs.
Uses FlareSolverr for CF bypass + direct Workday API calls with session cookies.

Honeywell uses Workday at: https://honeywell.wd5.myworkdayjobs.com/en-US/Honeywell

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe honeywell_workday_scrape.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
import logging
from datetime import datetime, timezone
from urllib.request import urlopen, Request
import urllib.parse

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
FLARE_URL = "http://localhost:8191/v1"

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("honeywell_workday")

# Honeywell Workday configuration
WORKDAY_BASE = "https://honeywell.wd5.myworkdayjobs.com"
TENANT = "honeywell"
BOARD = "Honeywell"
# Direct Workday search page URLs to fetch via FlareSolverr
SEARCH_TERMS = [
    "software engineer",
    "firmware engineer",
    "test engineer",
    "embedded software",
    "hardware engineer",
    "systems engineer",
    "AI engineer",
    "python developer",
    "automation engineer",
]

# Matt's match keywords (firmware, PCB, test fixture, microsoldering)
TITLE_KEYWORDS = {
    "software engineer": 25, "software developer": 20,
    "firmware": 35, "embedded": 30, "pcb": 25, "test engineer": 20,
    "hardware engineer": 20, "test fixture": 25, "microsoldering": 30,
    "ai ": 20, "machine learning": 25, "llm": 25,
    "python": 15, "backend": 10, "automation": 15,
    "systems engineer": 15, "devops": 10, "cloud": 10,
    "avionics": 20, "aerospace": 15, "defense": 15,
}
NEGATIVE_KEYWORDS = ["manager", "director", "vp ", "sales", "marketing", "recruiter"]


def score_job(title, location=""):
    t = (title or "").lower()
    score = 20
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in t:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in t:
            score -= 20
    if re.search(r"\bremote\b", (location or "").lower()):
        score += 10
    return min(score, 100)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def url_exists(conn, url):
    return conn.execute("SELECT 1 FROM jobs WHERE url=?", (url,)).fetchone() is not None


def source_id_exists(conn, sid):
    return conn.execute(
        "SELECT 1 FROM jobs WHERE source='workday_honeywell' AND source_id=?", (sid,)
    ).fetchone() is not None


def insert_job(conn, jd):
    if url_exists(conn, jd["url"]):
        return False
    if source_id_exists(conn, jd["source_id"]):
        return False
    job_id = hashlib.sha256(("workday_honeywell:" + jd["source_id"]).encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, source_id, title, company, url, location,
           salary, job_type, category, description, tags, date_posted, date_found,
           fit_score, fit_reason, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id, "workday_honeywell", jd["source_id"], jd["title"], "Honeywell",
            jd["url"], jd["location"], None, None, "engineering",
            jd.get("description", ""),
            json.dumps(["workday", "honeywell", "aerospace", "defense"]),
            jd.get("date_posted"), now,
            jd.get("fit_score", 0), jd.get("fit_reason", "Honeywell Workday"), "new"
        )
    )
    conn.commit()
    return True


def flare_get(url, max_timeout=45000):
    """Fetch URL via FlareSolverr for CF bypass."""
    payload = json.dumps({
        "cmd": "request.get",
        "url": url,
        "maxTimeout": max_timeout
    }).encode("utf-8")
    req = Request(
        FLARE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            if data.get("status") != "ok":
                log.warning("FlareSolverr non-ok status: %s", data.get("status"))
            return data.get("solution", {}).get("response", "")
    except Exception as e:
        log.warning("FlareSolverr error: %s", e)
        return ""


def try_workday_api(search_text="", offset=0, limit=20):
    """
    Try to call Workday's jobs API directly.
    Returns list of job dicts or empty list.
    """
    url = f"{WORKDAY_BASE}/wday/cxs/{TENANT}/{BOARD}/jobs"
    payload = json.dumps({
        "appliedFacets": {},
        "limit": limit,
        "offset": offset,
        "searchText": search_text
    }).encode("utf-8")
    req = Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{WORKDAY_BASE}/en-US/{BOARD}",
        "Origin": WORKDAY_BASE,
        "X-Calypso-CSRF-Token": "undefined",
    }, method="POST")
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data.get("jobPostings", []), data.get("total", 0)
    except Exception as e:
        log.debug("Workday API error (expected): %s", e)
        return [], 0


def parse_workday_html(html):
    """Parse Workday jobs from HTML page content."""
    jobs = []
    if not html:
        return jobs

    # Workday embeds job data in JSON-LD or window.__WD_CONFIG__
    # Try JSON-LD first
    json_ld_matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    for match in json_ld_matches:
        try:
            data = json.loads(match.strip())
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "JobPosting":
                        jobs.append(_parse_jsonld_job(item))
            elif data.get("@type") == "JobPosting":
                jobs.append(_parse_jsonld_job(data))
        except Exception:
            pass

    if jobs:
        log.info("  Parsed %d jobs from JSON-LD", len(jobs))
        return jobs

    # Try to find job links directly
    job_paths = re.findall(
        r'href=["\']([^"\']*en-US/Honeywell/job/[^"\']+)["\']',
        html
    )
    job_paths = list(dict.fromkeys(job_paths))

    for path in job_paths:
        if not path.startswith("http"):
            path = WORKDAY_BASE + path
        # Extract ID from path
        path_parts = path.rstrip("/").split("/")
        job_id = path_parts[-1] if path_parts else path

        # Try to find title near the href
        title_match = re.search(
            re.escape(path) + r'[^>]*>([^<]{5,80})<',
            html
        )
        title = title_match.group(1).strip() if title_match else "Honeywell Position"

        jobs.append({
            "source_id": job_id,
            "title": title,
            "location": "",
            "url": path,
            "date_posted": "",
        })

    if jobs:
        log.info("  Parsed %d jobs from href patterns", len(jobs))
        return jobs

    # Look for embedded JSON state
    state_match = re.search(r'window\.__WD_DATA__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if not state_match:
        state_match = re.search(r'"jobPostings"\s*:\s*(\[.*?\])', html, re.DOTALL)
    if state_match:
        try:
            data = json.loads(state_match.group(1))
            if isinstance(data, list):
                for j in data:
                    jobs.append({
                        "source_id": str(j.get("bulletFields", [""])[0] if j.get("bulletFields") else j.get("title", "unknown")),
                        "title": j.get("title", "Unknown"),
                        "location": j.get("locationsText", ""),
                        "url": WORKDAY_BASE + j.get("externalPath", ""),
                        "date_posted": j.get("postedOn", ""),
                    })
        except Exception:
            pass

    return jobs


def _parse_jsonld_job(data):
    return {
        "source_id": re.sub(r"[^a-zA-Z0-9_-]", "", data.get("identifier", {}).get("value", str(hash(data.get("title",""))))) if isinstance(data.get("identifier"), dict) else str(hash(data.get("title", ""))),
        "title": data.get("title", "Unknown"),
        "location": data.get("jobLocation", {}).get("address", {}).get("addressLocality", "") if isinstance(data.get("jobLocation"), dict) else "",
        "url": data.get("url", ""),
        "date_posted": data.get("datePosted", ""),
        "description": data.get("description", "")[:500],
    }


def main():
    log.info("=" * 70)
    log.info("HONEYWELL WORKDAY SCRAPER")
    log.info("=" * 70)

    conn = get_db()
    total_inserted = 0
    total_skipped = 0

    # Method 1: Try direct Workday API (often 422 but worth trying)
    log.info("Method 1: Direct Workday API...")
    for term in SEARCH_TERMS[:3]:
        jobs_raw, total = try_workday_api(search_text=term)
        if jobs_raw:
            log.info("  API SUCCESS for '%s': %d jobs (total=%d)", term, len(jobs_raw), total)
            for j in jobs_raw:
                ext_path = j.get("externalPath", "")
                url = f"{WORKDAY_BASE}{ext_path}" if ext_path else ""
                if not url:
                    continue
                # Extract ID from path
                sid = ext_path.rstrip("/").split("/")[-1]
                jd = {
                    "source_id": sid,
                    "title": j.get("title", "Unknown"),
                    "location": j.get("locationsText", ""),
                    "url": url,
                    "date_posted": j.get("postedOn", ""),
                    "fit_score": score_job(j.get("title", ""), j.get("locationsText", "")),
                    "fit_reason": f"Honeywell Workday API: {term}",
                }
                if insert_job(conn, jd):
                    total_inserted += 1
                    log.info("  + %s | %s | %s", sid, jd["title"], jd["location"])
                else:
                    total_skipped += 1
        else:
            log.info("  API not available for '%s' (expected)", term)
        time.sleep(0.5)

    # Method 2: FlareSolverr to fetch Workday search pages
    log.info("")
    log.info("Method 2: FlareSolverr page scrape...")

    for term in SEARCH_TERMS:
        enc = urllib.parse.quote_plus(term)
        url = f"{WORKDAY_BASE}/en-US/{BOARD}/jobs?q={enc}"
        log.info("  Fetching: %s", url)

        html = flare_get(url, max_timeout=45000)
        if not html:
            log.warning("  No HTML returned")
            time.sleep(2)
            continue

        log.info("  HTML size: %d bytes", len(html))

        # Check for blocks
        if "Access Denied" in html or "403 Forbidden" in html:
            log.warning("  Access denied")
            time.sleep(5)
            continue

        jobs = parse_workday_html(html)
        log.info("  Parsed %d jobs for '%s'", len(jobs), term)

        ins = 0
        skp = 0
        for j in jobs:
            j["fit_score"] = score_job(j.get("title", ""), j.get("location", ""))
            j["fit_reason"] = f"Honeywell Workday FlareSolverr: {term}"
            if not j.get("source_id"):
                j["source_id"] = hashlib.sha256((j.get("url","") + j.get("title","")).encode()).hexdigest()[:12]
            if not j.get("url"):
                continue
            if insert_job(conn, j):
                ins += 1
                total_inserted += 1
                log.info("    + %s | %s @ %s | score=%d",
                         j["source_id"][:20], j["title"][:50], j["location"][:30], j["fit_score"])
            else:
                skp += 1
                total_skipped += 1

        log.info("  Inserted: %d | Duplicates: %d", ins, skp)
        time.sleep(3)

    # Method 3: Scrape Honeywell's main careers page for job listing links
    log.info("")
    log.info("Method 3: Honeywell main careers page...")
    careers_url = "https://careers.honeywell.com/en/sites/Honeywell"
    html = flare_get(careers_url, max_timeout=45000)
    if html:
        log.info("  Careers page: %d bytes", len(html))
        # Look for job board links
        board_links = re.findall(r'href=["\']([^"\']*(?:jobs|careers|positions)[^"\']*)["\']', html, re.I)
        unique_links = list(dict.fromkeys(board_links))[:10]
        log.info("  Found %d potential board links: %s", len(unique_links), unique_links[:5])

    conn.close()

    print("")
    print("=" * 70)
    print("HONEYWELL WORKDAY SCRAPE COMPLETE")
    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped:  {total_skipped}")
    print("=" * 70)


if __name__ == "__main__":
    main()
