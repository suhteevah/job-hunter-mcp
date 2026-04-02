"""Scrape Indeed via Wraith native engine + FlareSolverr. No Chrome needed."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import re
import sqlite3
import time
import random
from datetime import datetime, timezone
from wraith_mcp_client import WraithMCPClient

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

QUERIES = [
    "AI engineer remote",
    "machine learning engineer remote",
    "software engineer AI remote",
    "python developer remote",
    "backend engineer remote",
    "devops engineer remote",
    "automation engineer remote",
    "full stack engineer remote",
    "platform engineer remote",
    "SRE site reliability remote",
    "LLM engineer remote",
    "ML ops engineer remote",
    "cloud engineer remote",
    "infrastructure engineer remote",
    "rust developer remote",
]

def parse_indeed_snapshot(snapshot_text):
    """Parse Indeed job listings from Wraith snapshot text."""
    jobs = []
    lines = snapshot_text.split('\n')

    current_job = {}
    for line in lines:
        line = line.strip()
        # Look for job links with indeed viewjob URLs
        if '/viewjob?jk=' in line or '/rc/clk?jk=' in line:
            jk_match = re.search(r'jk=([a-f0-9]+)', line)
            if jk_match:
                if current_job.get('jk'):
                    jobs.append(current_job)
                current_job = {'jk': jk_match.group(1)}

        # Look for job title patterns
        if '[link]' in line and current_job.get('jk') and not current_job.get('title'):
            title = re.sub(r'\[link\]\s*', '', line).strip().strip('"')
            if title and len(title) > 5 and 'indeed' not in title.lower():
                current_job['title'] = title

        # Company name often follows title
        if current_job.get('title') and not current_job.get('company'):
            company = re.sub(r'\[.*?\]\s*', '', line).strip().strip('"')
            if company and len(company) > 2 and company != current_job['title']:
                current_job['company'] = company

    if current_job.get('jk'):
        jobs.append(current_job)

    return jobs


def insert_jobs(db, jobs):
    """Insert Indeed jobs into the database."""
    inserted = 0
    for job in jobs:
        jk = job.get('jk', '')
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        url = f"https://www.indeed.com/viewjob?jk={jk}"
        source_id = f"indeed-{jk}"
        job_id = hashlib.md5(f"indeed:{url}".encode()).hexdigest()[:16]

        try:
            db.execute("""INSERT OR IGNORE INTO jobs
                (id, source, source_id, title, company, url, location, date_found, status, fit_score)
                VALUES (?, 'indeed', ?, ?, ?, ?, 'Remote', ?, 'new', 0)""",
                (job_id, source_id, title, company, url,
                 datetime.now(timezone.utc).isoformat()))
            if db.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            pass

    db.commit()
    return inserted


def main():
    print("=== INDEED WRAITH SCRAPE ===")
    print(f"Queries: {len(QUERIES)}")

    wraith = WraithMCPClient()

    # Load cookies
    try:
        wraith.call("cookie_load", {"path": r"J:\job-hunter-mcp\scripts\swarm\indeed_cookies.json"})
        print("Cookies loaded")
    except Exception as e:
        print(f"Cookie load failed (continuing): {e}")

    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=60000")

    total_inserted = 0
    total_found = 0

    # Shuffle queries for anti-detection
    random.shuffle(QUERIES)

    for qi, query in enumerate(QUERIES):
        q_encoded = query.replace(' ', '+')

        for page in range(3):  # 3 pages per query
            start = page * 10
            url = f"https://www.indeed.com/jobs?q={q_encoded}&sort=date&fromage=3&filter=0&start={start}"

            print(f"\n[{qi+1}/{len(QUERIES)}] '{query}' page {page+1}...")

            # Random delay between requests (2-6 seconds)
            delay = random.uniform(2, 6)
            time.sleep(delay)

            try:
                result = wraith.navigate(url)

                if 'Security Check' in result or 'Just a moment' in result:
                    print(f"  CF challenge - FlareSolverr should escalate...")
                    time.sleep(3)
                    result = wraith.snapshot()

                if 'Security Check' in result:
                    print(f"  Still blocked, skipping page")
                    continue

                # Parse jobs from snapshot
                jobs = parse_indeed_snapshot(result)
                print(f"  Found {len(jobs)} jobs")
                total_found += len(jobs)

                if jobs:
                    inserted = insert_jobs(db, jobs)
                    total_inserted += inserted
                    print(f"  Inserted {inserted} new")

                if len(jobs) == 0:
                    print(f"  No jobs found, stopping pagination for this query")
                    break

            except Exception as e:
                print(f"  Error: {e}")
                continue

    print(f"\n=== DONE ===")
    print(f"Total found: {total_found}")
    print(f"Total new inserted: {total_inserted}")

    # Final count
    count = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"Total jobs in DB: {count}")


if __name__ == "__main__":
    main()
