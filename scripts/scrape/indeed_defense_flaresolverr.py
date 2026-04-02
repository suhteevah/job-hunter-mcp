"""Scrape Indeed for defense/hardware/gov jobs via FlareSolverr (CF bypass)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
import random
import urllib.request
import urllib.error
from datetime import datetime, timezone

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
FLARESOLVERR_URL = "http://localhost:8191/v1"

QUERIES = [
    "Honeywell engineer remote",
    "ERC engineer",
    "firmware engineer remote",
    "embedded systems engineer remote",
    "PCB design engineer",
    "hardware test engineer remote",
    "government software engineer remote",
    "cleared software engineer remote",
    "Booz Allen engineer",
    "Peraton engineer",
    "ManTech software engineer",
    "Raytheon software engineer",
    "Lockheed Martin software engineer",
    "Northrop Grumman engineer",
    "MITRE engineer",
]

def flaresolverr_get(url):
    """Use FlareSolverr to bypass Cloudflare and get page HTML."""
    payload = json.dumps({
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 30000
    }).encode('utf-8')

    req = urllib.request.Request(
        FLARESOLVERR_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        resp = urllib.request.urlopen(req, timeout=45)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get("status") == "ok":
            return data.get("solution", {}).get("response", "")
        else:
            print(f"  FlareSolverr error: {data.get('message', 'unknown')}")
            return ""
    except Exception as e:
        print(f"  FlareSolverr request failed: {e}")
        return ""

def parse_indeed_html(html):
    """Parse job listings from Indeed HTML."""
    jobs = []
    # Find job cards with jk parameter
    jk_pattern = re.compile(r'data-jk="([a-f0-9]+)"')
    title_pattern = re.compile(r'<h2[^>]*class="[^"]*jobTitle[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>', re.DOTALL)
    company_pattern = re.compile(r'data-testid="company-name"[^>]*>([^<]+)<')

    # Alternative: look for viewjob links
    viewjob_pattern = re.compile(r'/viewjob\?jk=([a-f0-9]+)')

    jks = set(jk_pattern.findall(html))
    jks.update(viewjob_pattern.findall(html))

    # Try to pair with titles/companies from nearby context
    titles = title_pattern.findall(html)
    companies = company_pattern.findall(html)

    for i, jk in enumerate(jks):
        job = {
            'jk': jk,
            'title': titles[i].strip() if i < len(titles) else 'Unknown',
            'company': companies[i].strip() if i < len(companies) else 'Unknown',
        }
        jobs.append(job)

    return jobs

def main():
    print(f"=== INDEED DEFENSE/HARDWARE/GOV SCRAPE (FlareSolverr) ===")
    print(f"Queries: {len(QUERIES)}")

    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=60000")

    # Verify FlareSolverr is running
    try:
        test = urllib.request.urlopen("http://localhost:8191/", timeout=5)
        print("FlareSolverr: OK")
    except:
        print("WARNING: FlareSolverr may not be running on localhost:8191")

    total_found = 0
    total_inserted = 0
    random.shuffle(QUERIES)

    for qi, query in enumerate(QUERIES):
        q_encoded = query.replace(' ', '+')
        url = f"https://www.indeed.com/jobs?q={q_encoded}&sort=date&fromage=7&filter=0"

        print(f"\n[{qi+1}/{len(QUERIES)}] '{query}'...")

        # Random delay
        delay = random.uniform(4, 10)
        time.sleep(delay)

        html = flaresolverr_get(url)
        if not html or 'Security Check' in html:
            print(f"  Blocked or empty")
            continue

        jobs = parse_indeed_html(html)
        print(f"  Found {len(jobs)} jobs")
        total_found += len(jobs)

        inserted = 0
        for job in jobs:
            jk = job['jk']
            job_url = f"https://www.indeed.com/viewjob?jk={jk}"
            job_id = hashlib.md5(f"indeed:{job_url}".encode()).hexdigest()[:16]
            source_id = f"indeed-{jk}"

            try:
                db.execute("""INSERT OR IGNORE INTO jobs
                    (id, source, source_id, title, company, url, location, date_found, status, fit_score)
                    VALUES (?, 'indeed', ?, ?, ?, ?, 'Remote', ?, 'new', 0)""",
                    (job_id, source_id, job['title'], job['company'], job_url,
                     datetime.now(timezone.utc).isoformat()))
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        db.commit()
        total_inserted += inserted
        print(f"  Inserted {inserted} new")

    print(f"\n=== DONE ===")
    print(f"Total found: {total_found}")
    print(f"Total inserted: {total_inserted}")
    print(f"Total jobs in DB: {db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")

if __name__ == "__main__":
    main()
