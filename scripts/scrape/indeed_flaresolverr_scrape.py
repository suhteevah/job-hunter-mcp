"""
Indeed FlareSolverr Scraper
============================
Uses FlareSolverr (running on localhost:8191) to bypass Indeed's Cloudflare
protection and scrape job listings.

FlareSolverr maintains a browser session so cookies persist between requests.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import random
import re
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
FLARESOLVERR_URL = "http://localhost:8191/v1"

SEARCH_QUERIES = [
    "AI+engineer+remote",
    "LLM+engineer+remote",
    "machine+learning+engineer+remote",
    "python+developer+AI+remote",
    "devops+engineer+remote",
    "automation+engineer+remote",
    "defense+software+engineer+remote",
    "CACI+software+engineer",
    "Leidos+software+engineer",
    "SAIC+software+engineer",
]

TITLE_KEYWORDS = {
    "ai ": 20, "ml ": 20, "machine learning": 25, "llm": 25,
    "data scientist": 15, "data engineer": 15, "nlp": 20,
    "genai": 25, "gen ai": 25, "generative ai": 25,
    "python": 10, "backend": 10, "full stack": 10, "fullstack": 10,
    "infrastructure": 8, "platform": 8, "devops": 8, "sre": 8,
    "cloud": 8, "systems": 5, "automation": 10,
    "rust": 15, "agent": 15, "mcp": 20,
    "cleared": 5, "ts/sci": 5, "defense": 5,
}
NEGATIVE_KEYWORDS = ["manager", "director", "sales", "marketing", "recruiter", "intern"]
SESSION_ID = f"indeed-scrape-{int(time.time())}"


def score_job(title, description=""):
    text = (title + " " + description).lower()
    score = 30
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in text:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in title.lower():
            score -= 15
    if "remote" in text:
        score += 10
    return max(0, min(100, score))


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def insert_jobs(jobs):
    if not jobs:
        return 0
    conn = get_db()
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        jid = hashlib.sha256(job["url"].encode()).hexdigest()[:12]
        try:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ? OR source_id = ?",
                (job["url"], job["job_key"])
            ).fetchone()
            if existing:
                continue
            conn.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  salary, description, date_found, fit_score, status)
                VALUES (?, 'indeed', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                jid, job["job_key"], job["title"], job["company"],
                job["url"], job.get("location", ""), job.get("salary", ""),
                job.get("description", ""),
                now, job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f"  DB error: {e}")
    conn.commit()
    conn.close()
    return inserted


def parse_job_cards(html):
    """Parse job cards from Indeed HTML."""
    jobs = []
    seen = set()

    for match in re.finditer(r'id="jobTitle-([a-f0-9]+)"[^>]*>([^<]+)<', html):
        jk = match.group(1)
        if jk in seen:
            continue
        seen.add(jk)
        title = match.group(2).strip().replace('&amp;', '&').replace('&#x27;', "'").replace('&#39;', "'")

        start = max(0, match.start() - 500)
        end = min(len(html), match.end() + 3000)
        card = html[start:end]

        company_m = re.search(r'data-testid="company-name"[^>]*>([^<]+)<', card)
        company = company_m.group(1).strip() if company_m else "Unknown"

        loc_m = re.search(r'data-testid="text-location"[^>]*>\s*<span>([^<]+)<', card)
        location = loc_m.group(1).strip() if loc_m else ""

        salary_m = re.search(r'data-testid="attribute_snippet_testid"[^>]*>([^<]*\$[^<]+)<', card)
        salary = salary_m.group(1).strip() if salary_m else ""

        snippet_m = re.search(r'<div[^>]*class="[^"]*css-[^"]*"[^>]*><ul[^>]*>(.*?)</ul>', card, re.DOTALL)
        snippet = ""
        if snippet_m:
            snippet = re.sub(r'<[^>]+>', ' ', snippet_m.group(1)).strip()[:500]

        url = f"https://www.indeed.com/viewjob?jk={jk}"
        fit = score_job(title, snippet)

        jobs.append({
            "title": title, "company": company, "url": url,
            "location": location, "salary": salary,
            "job_key": jk, "description": snippet, "fit_score": fit,
        })

    return jobs


def flaresolverr_get(url, session_id=None, timeout=90000):
    """Fetch a URL via FlareSolverr. Returns (html, cookies) or (None, None)."""
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": timeout,
    }
    if session_id:
        payload["session"] = session_id

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        FLARESOLVERR_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout//1000 + 10) as resp:
            result = json.loads(resp.read().decode('utf-8', errors='replace'))
            if result.get("status") == "ok":
                solution = result.get("solution", {})
                html = solution.get("response", "")
                cookies = solution.get("cookies", [])
                return html, cookies
            else:
                print(f"  FlareSolverr error: {result.get('message', 'unknown')}")
                return None, None
    except Exception as e:
        print(f"  FlareSolverr request error: {e}")
        return None, None


def flaresolverr_session_create(session_id):
    """Create a persistent FlareSolverr session."""
    payload = {"cmd": "sessions.create", "session": session_id}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        FLARESOLVERR_URL, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8', errors='replace'))
            return result.get("status") == "ok"
    except Exception as e:
        print(f"  Session create error: {e}")
        return False


def flaresolverr_session_destroy(session_id):
    """Destroy a FlareSolverr session."""
    payload = {"cmd": "sessions.destroy", "session": session_id}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        FLARESOLVERR_URL, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception:
        pass


def main():
    print(f"=== INDEED FLARESOLVERR SCRAPE — {len(SEARCH_QUERIES)} queries ===")
    print(f"FlareSolverr: {FLARESOLVERR_URL}")
    print(f"Session: {SESSION_ID}\n")

    # Create a persistent session for cookie reuse
    print("Creating FlareSolverr session...")
    if flaresolverr_session_create(SESSION_ID):
        print("  Session created OK")
    else:
        print("  Session create failed, proceeding without session persistence")

    # Warm up session on Indeed homepage
    print("\nWarming up on Indeed homepage...")
    html, cookies = flaresolverr_get("https://www.indeed.com", session_id=SESSION_ID, timeout=90000)
    if html:
        # Quick check for block
        if "Just a moment" in html or "Request Blocked" in html:
            print("  Homepage still blocked — FlareSolverr may need more time")
        else:
            print(f"  Homepage loaded OK ({len(html)} chars)")
    else:
        print("  Homepage load failed")

    time.sleep(random.uniform(3, 6))

    total_found = 0
    total_inserted = 0

    for qi, query in enumerate(SEARCH_QUERIES):
        print(f"\n[{qi+1}/{len(SEARCH_QUERIES)}] Query: {query.replace('+', ' ')}")

        url = f"https://www.indeed.com/jobs?q={query}&sort=date&fromage=3&filter=0"

        pre_delay = random.uniform(3, 8)
        print(f"  Waiting {pre_delay:.1f}s (rate limit delay)...")
        time.sleep(pre_delay)

        html, cookies = flaresolverr_get(url, session_id=SESSION_ID, timeout=90000)

        if html is None:
            print(f"  SKIP: no response from FlareSolverr")
            continue

        # Check for block pages
        if "Just a moment" in html or "Request Blocked" in html or "blocked" in html.lower()[:500]:
            print(f"  BLOCKED: Cloudflare challenge not solved")
            # Wait longer and retry once
            print(f"  Retrying after 20s...")
            time.sleep(20)
            html, cookies = flaresolverr_get(url, session_id=SESSION_ID, timeout=120000)
            if html is None or "Just a moment" in html:
                print(f"  Still blocked, skipping")
                continue

        jobs = parse_job_cards(html)
        total_found += len(jobs)

        inserted = insert_jobs(jobs)
        total_inserted += inserted

        viable = sum(1 for j in jobs if j["fit_score"] >= 40)
        print(f"  Found: {len(jobs)}, New: {inserted}, Viable: {viable}")

        if len(jobs) == 0:
            # Try to diagnose - show first 200 chars of page
            preview = re.sub(r'<[^>]+>', ' ', html[:1000]).strip()[:200]
            print(f"  Page preview: {preview}")

    # Cleanup session
    flaresolverr_session_destroy(SESSION_ID)

    print(f"\n{'='*60}")
    print(f"INDEED FLARESOLVERR SCRAPE COMPLETE")
    print(f"  Total jobs found: {total_found}")
    print(f"  New jobs inserted: {total_inserted}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
