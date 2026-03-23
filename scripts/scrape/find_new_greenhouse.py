#!/usr/bin/env python
"""
find_new_greenhouse.py
Search Greenhouse and Lever job boards for new postings matching target roles,
then insert them into jobs.db.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe find_new_greenhouse.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import hashlib
import json
import re
import logging
import traceback
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

SEARCH_KEYWORDS = [
    "AI engineer",
    "software engineer",
    "backend engineer",
    "DevOps engineer",
    "Python developer",
]

# Focus on remote / USA positions
LOCATION_FILTERS = ["remote", "usa", "united states", "us"]

# Well-known companies that use Greenhouse/Lever and hire remote engineers
# We query their public board APIs directly
GREENHOUSE_BOARDS = [
    "airbnb", "ashbyhq", "airtable", "anduril", "anthropic", "brex",
    "canva", "cloudflare", "coinbase", "databricks", "datadog",
    "discord", "figma", "github", "gitlab", "gusto", "hashicorp",
    "hubspot", "instacart", "loom", "lyft", "mongodb", "netlify",
    "notion", "openai", "palantir", "pinterestcareers", "plaid",
    "ramp", "reddit", "remotecom", "replit", "retool", "rippling",
    "robinhood", "scale", "snyk", "sourcegraph", "splice",
    "square", "stripe", "supabase", "twitch", "twilio",
    "vercel", "wealthsimple", "zapier", "zscaler",
]

LEVER_COMPANIES = [
    "Netflix", "shopify", "netlify", "auth0", "postman",
    "webflow", "vercel", "linear", "mux", "stytch",
    "temporal", "dagster", "posthog", "cal-com",
    "render", "railway", "supabase", "neon",
    "prisma", "planetscale", "hasura", "cockroachlabs",
]

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("find_greenhouse")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "JobHunter/1.0"})

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def job_exists(conn, source, source_id):
    row = conn.execute(
        "SELECT 1 FROM jobs WHERE source = ? AND source_id = ?",
        (source, source_id),
    ).fetchone()
    return row is not None


def url_exists(conn, url):
    row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
    return row is not None


def insert_job(conn, job_dict):
    """Insert a job into the database. Returns True if inserted, False if duplicate."""
    source = job_dict.get("source", "greenhouse")
    source_id = job_dict.get("source_id", "")

    if job_exists(conn, source, source_id):
        return False
    if url_exists(conn, job_dict["url"]):
        return False

    job_id = hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT INTO jobs
           (id, source, source_id, title, company, url, location, salary,
            job_type, category, description, tags, date_posted, date_found,
            fit_score, fit_reason, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            source,
            source_id,
            job_dict.get("title", "Unknown"),
            job_dict.get("company", "Unknown"),
            job_dict["url"],
            job_dict.get("location", "Remote"),
            job_dict.get("salary"),
            job_dict.get("job_type"),
            job_dict.get("category", "engineering"),
            job_dict.get("description", ""),
            json.dumps(job_dict.get("tags", [])),
            job_dict.get("date_posted"),
            now,
            job_dict.get("fit_score", 0.0),
            job_dict.get("fit_reason", ""),
            "new",
        ),
    )
    conn.commit()
    return True


def log_search(conn, query, sources, result_count, new_jobs):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO search_history (query, sources, result_count, new_jobs, timestamp) VALUES (?,?,?,?,?)",
        (query, sources, result_count, new_jobs, now),
    )
    conn.commit()

# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

KEYWORD_PATTERNS = [
    re.compile(r'\bai\b', re.I),
    re.compile(r'\bartificial intelligence\b', re.I),
    re.compile(r'\bmachine learning\b', re.I),
    re.compile(r'\bml\b', re.I),
    re.compile(r'\bsoftware engineer', re.I),
    re.compile(r'\bbackend\b', re.I),
    re.compile(r'\bback-end\b', re.I),
    re.compile(r'\bfull.?stack\b', re.I),
    re.compile(r'\bdevops\b', re.I),
    re.compile(r'\bplatform engineer', re.I),
    re.compile(r'\binfrastructure engineer', re.I),
    re.compile(r'\bsre\b', re.I),
    re.compile(r'\bpython\b', re.I),
    re.compile(r'\bdata engineer', re.I),
]

LOCATION_PATTERNS = [
    re.compile(r'\bremote\b', re.I),
    re.compile(r'\bunited states\b', re.I),
    re.compile(r'\b(?:us|usa)\b', re.I),
    re.compile(r'\bchico\b', re.I),
    re.compile(r'\bcalifornia\b', re.I),
    re.compile(r'\banywhere\b', re.I),
]


def title_matches(title):
    return any(p.search(title) for p in KEYWORD_PATTERNS)


def location_matches(location):
    if not location:
        return True  # no location = possibly remote
    return any(p.search(location) for p in LOCATION_PATTERNS)


def score_job(title, location):
    """Simple heuristic fit score 0-100."""
    score = 0
    title_lower = title.lower()
    if re.search(r'\bai\b|\bartificial intelligence\b|\bmachine learning\b|\bml\b', title_lower):
        score += 40
    if re.search(r'\bpython\b', title_lower):
        score += 20
    if re.search(r'\bbackend\b|\bback-end\b', title_lower):
        score += 15
    if re.search(r'\bsoftware engineer\b', title_lower):
        score += 15
    if re.search(r'\bdevops\b|\bsre\b|\bplatform\b|\binfrastructure\b', title_lower):
        score += 15
    if re.search(r'\bfull.?stack\b', title_lower):
        score += 10
    if re.search(r'\bsenior\b|\bstaff\b|\blead\b', title_lower):
        score += 10
    loc = (location or "").lower()
    if "remote" in loc:
        score += 10
    return min(score, 100)

# ---------------------------------------------------------------------------
# Greenhouse board API
# ---------------------------------------------------------------------------

def search_greenhouse_board(board_token):
    """
    Query a Greenhouse board's public API for jobs.
    GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs
    """
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    found = []
    try:
        resp = SESSION.get(api_url, timeout=15)
        if resp.status_code != 200:
            log.debug("  Greenhouse board %s returned %s", board_token, resp.status_code)
            return found

        data = resp.json()
        jobs_list = data.get("jobs", [])
        log.debug("  Board %s: %d total jobs", board_token, len(jobs_list))

        for j in jobs_list:
            title = j.get("title", "")
            location_name = j.get("location", {}).get("name", "")

            if not title_matches(title):
                continue
            if not location_matches(location_name):
                continue

            job_url = j.get("absolute_url", "")
            if not job_url:
                job_url = f"https://boards.greenhouse.io/{board_token}/jobs/{j.get('id', '')}"

            found.append({
                "source": "greenhouse",
                "source_id": str(j.get("internal_job_id", j.get("id", ""))),
                "title": title,
                "company": board_token,
                "url": job_url,
                "location": location_name,
                "date_posted": j.get("updated_at", ""),
                "tags": ["greenhouse", board_token],
                "fit_score": score_job(title, location_name),
                "fit_reason": f"Keyword match from {board_token} board",
            })

    except Exception as e:
        log.debug("  Error fetching Greenhouse board %s: %s", board_token, e)

    return found

# ---------------------------------------------------------------------------
# Lever postings API
# ---------------------------------------------------------------------------

def search_lever_company(company_slug):
    """
    Query a Lever company's public postings API.
    GET https://api.lever.co/v0/postings/{company}?mode=json
    """
    api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    found = []
    try:
        resp = SESSION.get(api_url, timeout=15)
        if resp.status_code != 200:
            log.debug("  Lever company %s returned %s", company_slug, resp.status_code)
            return found

        postings = resp.json()
        if not isinstance(postings, list):
            return found

        log.debug("  Lever %s: %d total postings", company_slug, len(postings))

        for p in postings:
            title = p.get("text", "")
            cats = p.get("categories", {})
            location_name = cats.get("location", "")
            team = cats.get("team", "")
            commitment = cats.get("commitment", "")

            if not title_matches(title):
                continue
            if not location_matches(location_name):
                continue

            posting_url = p.get("hostedUrl", "")
            if not posting_url:
                posting_url = f"https://jobs.lever.co/{company_slug}/{p.get('id', '')}"

            found.append({
                "source": "lever",
                "source_id": p.get("id", ""),
                "title": title,
                "company": company_slug,
                "url": posting_url,
                "location": location_name,
                "job_type": commitment,
                "category": team,
                "date_posted": "",
                "tags": ["lever", company_slug],
                "fit_score": score_job(title, location_name),
                "fit_reason": f"Keyword match from {company_slug} Lever",
            })

    except Exception as e:
        log.debug("  Error fetching Lever company %s: %s", company_slug, e)

    return found

# ---------------------------------------------------------------------------
# Google search fallback for discovering more boards
# ---------------------------------------------------------------------------

def search_google_for_boards(keyword):
    """
    Search Google for Greenhouse/Lever job postings matching a keyword.
    This is a best-effort scrape of search results.
    Returns list of (url, title) tuples.
    """
    results = []
    queries = [
        f'site:boards.greenhouse.io "{keyword}" remote',
        f'site:job-boards.greenhouse.io "{keyword}" remote',
        f'site:jobs.lever.co "{keyword}" remote',
    ]
    for query in queries:
        try:
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=20"
            resp = SESSION.get(search_url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Extract actual URL from Google redirect
                if "/url?q=" in href:
                    href = href.split("/url?q=")[1].split("&")[0]
                if "greenhouse.io" in href or "lever.co" in href:
                    title_text = a.get_text(strip=True)
                    results.append((href, title_text))
        except Exception as e:
            log.debug("  Google search error for '%s': %s", query, e)

    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("Find New Greenhouse & Lever Jobs")
    log.info("DB: %s", DB_PATH)
    log.info("Keywords: %s", ", ".join(SEARCH_KEYWORDS))
    log.info("=" * 60)

    conn = get_db()
    total_found = 0
    total_new = 0

    # --- Phase 1: Greenhouse Boards API ---
    log.info("")
    log.info("PHASE 1: Scanning %d Greenhouse boards...", len(GREENHOUSE_BOARDS))
    for board in GREENHOUSE_BOARDS:
        jobs = search_greenhouse_board(board)
        if jobs:
            log.info("  [%s] Found %d matching jobs", board, len(jobs))
            for j in jobs:
                total_found += 1
                if insert_job(conn, j):
                    total_new += 1
                    log.info("    NEW: %s - %s (%s) [score=%s]",
                             j["title"], j["company"], j["location"], j["fit_score"])
                else:
                    log.debug("    DUP: %s - %s", j["title"], j["company"])

    log_search(conn, "greenhouse_boards", "greenhouse", total_found, total_new)

    # --- Phase 2: Lever Postings API ---
    log.info("")
    log.info("PHASE 2: Scanning %d Lever companies...", len(LEVER_COMPANIES))
    lever_found = 0
    lever_new = 0
    for company in LEVER_COMPANIES:
        jobs = search_lever_company(company)
        if jobs:
            log.info("  [%s] Found %d matching jobs", company, len(jobs))
            for j in jobs:
                lever_found += 1
                total_found += 1
                if insert_job(conn, j):
                    lever_new += 1
                    total_new += 1
                    log.info("    NEW: %s - %s (%s) [score=%s]",
                             j["title"], j["company"], j["location"], j["fit_score"])
                else:
                    log.debug("    DUP: %s - %s", j["title"], j["company"])

    log_search(conn, "lever_companies", "lever", lever_found, lever_new)

    # --- Phase 3: Google search fallback ---
    log.info("")
    log.info("PHASE 3: Google search for additional postings...")
    google_found = 0
    google_new = 0
    for keyword in SEARCH_KEYWORDS:
        results = search_google_for_boards(keyword)
        for url, title in results:
            if not title:
                title = keyword
            # Parse source
            if "greenhouse.io" in url:
                source = "greenhouse"
                m = re.search(r'greenhouse\.io/([^/]+)/jobs/(\d+)', url)
                source_id = m.group(2) if m else hashlib.sha256(url.encode()).hexdigest()[:12]
                company = m.group(1) if m else "unknown"
            elif "lever.co" in url:
                source = "lever"
                m = re.search(r'lever\.co/([^/]+)/([0-9a-f-]+)', url)
                source_id = m.group(2) if m else hashlib.sha256(url.encode()).hexdigest()[:12]
                company = m.group(1) if m else "unknown"
            else:
                continue

            job_dict = {
                "source": source,
                "source_id": source_id,
                "title": title,
                "company": company,
                "url": url,
                "location": "Remote",
                "tags": [source, "google_search", keyword],
                "fit_score": score_job(title, "Remote"),
                "fit_reason": f"Google search: {keyword}",
            }
            google_found += 1
            total_found += 1
            if insert_job(conn, job_dict):
                google_new += 1
                total_new += 1
                log.info("    NEW (Google): %s - %s [%s]", title, company, url[:80])

    log_search(conn, "google_greenhouse_lever", "google", google_found, google_new)

    # --- Summary ---
    log.info("")
    log.info("=" * 60)
    log.info("SEARCH COMPLETE")
    log.info("  Total found:  %d", total_found)
    log.info("  New inserted: %d", total_new)
    log.info("  Duplicates:   %d", total_found - total_new)
    log.info("=" * 60)

    # Print all new jobs for review
    if total_new > 0:
        log.info("")
        log.info("NEW JOBS READY FOR REVIEW:")
        rows = conn.execute(
            """SELECT title, company, url, location, fit_score, source
               FROM jobs WHERE status = 'new'
                 AND (url LIKE '%greenhouse.io%' OR url LIKE '%lever.co%')
               ORDER BY fit_score DESC"""
        ).fetchall()
        for r in rows:
            print(f"  [{r['fit_score']:5.1f}] {r['title']} @ {r['company']} ({r['location']}) [{r['source']}]")
            print(f"         {r['url']}")

    conn.close()


if __name__ == "__main__":
    main()
