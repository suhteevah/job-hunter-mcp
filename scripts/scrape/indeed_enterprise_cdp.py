"""
indeed_enterprise_cdp.py
========================
Scrape Indeed for enterprise/defense company jobs via logged-in Chrome CDP.
Targets: Honeywell, Boeing, Lockheed, Northrop, GD, L3Harris, MITRE, Booz Allen.

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe indeed_enterprise_cdp.py

Requires: Chrome running with --remote-debugging-port=9222, logged into Indeed.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
CDP_URL = "http://localhost:9222"

SEARCH_QUERIES = [
    # Honeywell
    ("Honeywell software engineer", "remote"),
    ("Honeywell firmware engineer", ""),
    ("Honeywell test engineer", ""),
    ("Honeywell embedded software", ""),
    ("Honeywell PCB test engineer", ""),
    # Defense / Aerospace
    ("Boeing software engineer", "remote"),
    ("Lockheed Martin software engineer", "remote"),
    ("Northrop Grumman software engineer", "remote"),
    ("General Dynamics software engineer", ""),
    ("L3Harris software engineer", ""),
    ("MITRE software engineer", ""),
    ("Booz Allen Hamilton software engineer", ""),
    # More defense
    ("Raytheon software engineer", "remote"),
    ("SAIC software engineer", "remote"),
    ("Leidos software engineer", "remote"),
    ("CACI software engineer", "remote"),
    ("ManTech software engineer", "remote"),
    ("Peraton software engineer", "remote"),
]

TITLE_KEYWORDS = {
    "software engineer": 25, "software developer": 20,
    "firmware": 30, "embedded": 30, "pcb": 25, "test engineer": 20,
    "ai ": 20, "machine learning": 25, "llm": 25, "ml ": 20,
    "python": 10, "backend": 10, "full stack": 10,
    "infrastructure": 8, "platform": 8, "devops": 8,
    "cloud": 8, "systems": 5, "automation": 15,
    "rust": 15, "cleared": 10, "ts/sci": 10, "defense": 10,
    "hardware": 20, "test fixture": 20, "soldering": 25,
}
NEGATIVE_KEYWORDS = ["manager", "director", "sales", "marketing", "recruiter", "intern", "vp "]


def score_job(title, description=""):
    text = (title + " " + description).lower()
    score = 30
    for kw, pts in TITLE_KEYWORDS.items():
        if kw in text:
            score += pts
    for kw in NEGATIVE_KEYWORDS:
        if kw in title.lower():
            score -= 20
    if "remote" in text:
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
        "SELECT 1 FROM jobs WHERE source='indeed' AND source_id=?", (sid,)
    ).fetchone() is not None


def insert_job(conn, jd):
    if url_exists(conn, jd["url"]):
        return False
    if source_id_exists(conn, jd["source_id"]):
        return False
    job_id = hashlib.sha256(("indeed:" + jd["source_id"]).encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, source_id, title, company, url, location,
           salary, job_type, category, description, tags, date_posted, date_found,
           fit_score, fit_reason, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (job_id, "indeed", jd["source_id"], jd["title"], jd["company"],
         jd["url"], jd["location"], None, None, "engineering",
         jd.get("description", ""), json.dumps(["indeed", "enterprise", "defense"]),
         None, now, jd.get("fit_score", 0), jd.get("fit_reason", ""), "new")
    )
    conn.commit()
    return True


def parse_jobs_from_page(page):
    """Extract job listings from current Indeed page using JS evaluation."""
    jobs = []
    try:
        # Extract job cards via JS
        cards = page.evaluate("""
            () => {
                const jobs = [];
                // Try modern Indeed job card selectors
                const cards = document.querySelectorAll('[data-jk], .job_seen_beacon, .tapItem');
                cards.forEach(card => {
                    const jk = card.getAttribute('data-jk') || card.getAttribute('data-mobtk') || '';
                    const titleEl = card.querySelector('.jobTitle span, [class*="jobTitle"] span, h2 span');
                    const companyEl = card.querySelector('[data-testid="company-name"], .companyName span, [class*="companyName"]');
                    const locationEl = card.querySelector('[data-testid="text-location"], .companyLocation, [class*="companyLocation"]');
                    if (jk && titleEl) {
                        jobs.push({
                            jk: jk,
                            title: titleEl.innerText || titleEl.textContent || '',
                            company: companyEl ? (companyEl.innerText || companyEl.textContent || '') : '',
                            location: locationEl ? (locationEl.innerText || locationEl.textContent || '') : '',
                        });
                    }
                });
                return jobs;
            }
        """)
        for c in (cards or []):
            jk = c.get("jk", "").strip()
            title = c.get("title", "").strip()
            company = c.get("company", "").strip()
            location = c.get("location", "").strip()
            if jk and title:
                jobs.append({
                    "source_id": jk,
                    "title": title,
                    "company": company,
                    "url": f"https://www.indeed.com/viewjob?jk={jk}",
                    "location": location,
                    "fit_score": score_job(title, ""),
                    "fit_reason": f"Indeed enterprise/defense CDP scrape",
                })
    except Exception as e:
        print(f"  JS eval error: {e}")
    return jobs


def scrape_query(page, conn, query, location, max_pages=3):
    """Scrape Indeed for a query, up to max_pages pages."""
    import urllib.parse
    q_enc = urllib.parse.quote_plus(query)
    l_enc = urllib.parse.quote_plus(location) if location else ""
    base = f"https://www.indeed.com/jobs?q={q_enc}"
    if l_enc:
        base += f"&l={l_enc}"
    base += "&filter=0&sort=date"

    inserted = 0
    skipped = 0

    for page_num in range(max_pages):
        url = base if page_num == 0 else f"{base}&start={page_num * 10}"
        print(f"  Page {page_num + 1}: {url[:90]}")

        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(random.uniform(1.5, 3.0))

            # Check for login wall
            cur_url = page.url
            if "secure.indeed.com/auth" in cur_url or "login" in cur_url.lower():
                print("  !! Login wall detected — skipping")
                break

            # Check for captcha
            if page.locator("text=Are you a robot").count() > 0:
                print("  !! CAPTCHA detected — skipping query")
                time.sleep(10)
                break

            jobs = parse_jobs_from_page(page)
            print(f"  Found {len(jobs)} jobs on page {page_num + 1}")

            if not jobs:
                print("  No jobs found, stopping pagination")
                break

            for jd in jobs:
                if insert_job(conn, jd):
                    inserted += 1
                    print(f"    + {jd['source_id']} | {jd['title'][:50]} @ {jd['company']} | score={jd['fit_score']}")
                else:
                    skipped += 1

        except Exception as e:
            print(f"  Page error: {e}")
            break

        time.sleep(random.uniform(2.0, 4.0))

    return inserted, skipped


def main():
    print("=" * 70)
    print("INDEED ENTERPRISE/DEFENSE SCRAPE via Chrome CDP")
    print(f"Queries: {len(SEARCH_QUERIES)}")
    print("=" * 70)

    conn = get_db()
    total_inserted = 0
    total_skipped = 0

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            print(f"Connected to Chrome CDP")
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome CDP at {CDP_URL}: {e}")
            print("Make sure Chrome is running with --remote-debugging-port=9222")
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        # Check if logged into Indeed
        try:
            page.goto("https://www.indeed.com", timeout=15000, wait_until="domcontentloaded")
            time.sleep(2)
            cur_url = page.url
            print(f"Indeed page loaded: {cur_url[:80]}")

            # Check login status
            logged_in = page.evaluate("""
                () => {
                    // Look for user menu or sign-out link indicating logged in
                    return document.querySelector('[data-testid="user-profile-menu"], .gnav-LoggedIn, [aria-label="Account menu"]') !== null;
                }
            """)
            if logged_in:
                print("Confirmed: Logged into Indeed")
            else:
                print("WARNING: May not be logged in — proceeding anyway")
        except Exception as e:
            print(f"Indeed home check error: {e}")

        for query, location in SEARCH_QUERIES:
            print(f"\nSearching: '{query}' in '{location or 'all'}'")
            try:
                ins, skp = scrape_query(page, conn, query, location, max_pages=3)
                total_inserted += ins
                total_skipped += skp
                print(f"  Result: +{ins} inserted, {skp} duplicates")
            except Exception as e:
                print(f"  Query failed: {e}")

            time.sleep(random.uniform(3, 6))

        browser.close()

    conn.close()

    print("")
    print("=" * 70)
    print("INDEED ENTERPRISE SCRAPE COMPLETE")
    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped:  {total_skipped}")
    print("=" * 70)


if __name__ == "__main__":
    main()
