"""
jsearch_defense_hardware_scrape.py
=====================================
Scrapes defense/hardware/government jobs via JSearch RapidAPI (Indeed + more).
No Cloudflare issues. Inserts directly into jobs.db.

Queries: Honeywell, ERC, firmware, embedded, PCB, hardware test,
         government SW, cleared SW, Booz Allen, Peraton
"""
import sys
import hashlib
import json
import random
import re
import sqlite3
import time
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
    import requests

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
JSEARCH_KEY = "845423ab1emshdc9d0de9746fcdbp175051jsnde0ca0fd970f"
JSEARCH_HOST = "jsearch.p.rapidapi.com"

SEARCH_QUERIES = [
    "Honeywell engineer",
    "ERC engineer",
    "firmware engineer remote",
    "embedded systems engineer remote",
    "PCB design engineer",
    "hardware test engineer",
    "government software engineer remote",
    "cleared software engineer remote",
    "Booz Allen Hamilton engineer",
    "Peraton engineer",
]

TITLE_KEYWORDS = {
    "firmware": 25, "embedded": 25, "fpga": 25, "rtos": 25,
    "pcb": 20, "hardware": 20, "asic": 20, "verilog": 20, "vhdl": 20,
    "cleared": 15, "clearance": 15, "ts/sci": 20, "secret": 10,
    "defense": 15, "dod": 15, "government": 10, "federal": 10,
    "honeywell": 15, "booz": 15, "peraton": 15, "leidos": 15,
    "saic": 15, "caci": 15, "raytheon": 15, "northrop": 15,
    "python": 8, "c++": 8, "rust": 10, "automation": 10,
    "remote": 10, "engineer": 5, "developer": 5,
    "ai ": 10, "ml ": 10, "machine learning": 12,
    "sensor": 10, "signal": 10, "rf ": 15, "radio": 10,
    "test engineer": 12, "verification": 10,
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
            score -= 15
    if "remote" in text:
        score += 10
    return max(0, min(100, score))


def extract_jk(url):
    m = re.search(r'jk=([a-f0-9]+)', url)
    return m.group(1) if m else hashlib.sha256(url.encode()).hexdigest()[:16]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


def insert_jobs_db(jobs):
    if not jobs:
        return 0, 0
    conn = get_db()
    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        url = job["url"]
        jk = job["job_key"]
        jid = hashlib.sha256(url.encode()).hexdigest()[:12]
        try:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE url = ? OR source_id = ?",
                (url, jk)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  salary, description, date_found, fit_score, status)
                VALUES (?, 'indeed', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """, (
                jid, jk, job["title"], job["company"],
                url, job.get("location", ""), job.get("salary", ""),
                job.get("description", "")[:1000],
                now, job["fit_score"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as e:
            print(f"  DB error: {e}")
    conn.commit()
    conn.close()
    return inserted, skipped


def fetch_jsearch(query, num_pages=2, max_retries=3):
    """Fetch jobs from JSearch API."""
    all_jobs = []
    headers = {
        "X-RapidAPI-Key": JSEARCH_KEY,
        "X-RapidAPI-Host": JSEARCH_HOST,
    }
    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "date_posted": "week",
            "remote_jobs_only": "false",
        }
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    f"https://{JSEARCH_HOST}/search",
                    headers=headers,
                    params=params,
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    all_jobs.extend(data)
                    break
                elif resp.status_code == 429:
                    print(f"  Rate limited (429), waiting 30s...")
                    time.sleep(30)
                elif resp.status_code == 403:
                    print(f"  403 Forbidden — API key may be exhausted")
                    return None
                else:
                    print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
                    break
            except Exception as e:
                print(f"  Error on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 8))
        time.sleep(random.uniform(1, 3))
    return all_jobs


def parse_jsearch_jobs(raw_jobs, query_label):
    """Convert JSearch API results to our job dict format."""
    jobs = []
    for j in raw_jobs:
        title = j.get("job_title", "Unknown")
        company = j.get("employer_name", "Unknown")
        apply_url = j.get("job_apply_link") or j.get("job_google_link", "")
        location_city = j.get("job_city", "")
        location_state = j.get("job_state", "")
        location = f"{location_city}, {location_state}".strip(", ")
        if j.get("job_is_remote"):
            location = "Remote" if not location else f"Remote / {location}"
        description = (j.get("job_description") or "")[:800]
        salary_min = j.get("job_min_salary")
        salary_max = j.get("job_max_salary")
        salary = ""
        if salary_min and salary_max:
            salary = f"${salary_min:,.0f} - ${salary_max:,.0f}"
        elif salary_min:
            salary = f"${salary_min:,.0f}+"

        if not apply_url:
            continue

        jk = j.get("job_id") or extract_jk(apply_url)
        fit = score_job(title, description)

        jobs.append({
            "title": title,
            "company": company,
            "url": apply_url,
            "location": location,
            "description": description,
            "salary": salary,
            "job_key": jk[:50],  # truncate if needed
            "fit_score": fit,
            "query": query_label,
        })
    return jobs


def main():
    print(f"=== JSEARCH DEFENSE/HARDWARE/GOVERNMENT SCRAPE ===")
    print(f"Queries: {len(SEARCH_QUERIES)} | API: JSearch (RapidAPI) | Date: last 7 days")
    print(f"DB: {DB_PATH}\n")

    all_jobs = []
    total_found = 0
    total_inserted = 0
    total_skipped = 0

    for qi, query in enumerate(SEARCH_QUERIES):
        print(f"[{qi+1}/{len(SEARCH_QUERIES)}] Query: '{query}'")

        raw = fetch_jsearch(query, num_pages=2)
        if raw is None:
            print(f"  SKIP — API returned error")
            time.sleep(random.uniform(3, 8))
            continue

        jobs = parse_jsearch_jobs(raw, query)
        total_found += len(jobs)
        all_jobs.extend(jobs)

        inserted, skipped = insert_jobs_db(jobs)
        total_inserted += inserted
        total_skipped += skipped

        viable = sum(1 for j in jobs if j["fit_score"] >= 40)
        print(f"  Found: {len(jobs)} | New: {inserted} | Dupes: {skipped} | Viable(40+): {viable}")
        if jobs:
            for j in sorted(jobs, key=lambda x: -x["fit_score"])[:3]:
                print(f"    [{j['fit_score']:3d}] {j['title']} @ {j['company']} ({j['location']})")
            if len(jobs) > 3:
                print(f"    ... and {len(jobs)-3} more")

        if qi < len(SEARCH_QUERIES) - 1:
            delay = random.uniform(3, 8)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Save full job list to JSON
    out_path = r"J:\job-hunter-mcp\scripts\swarm\indeed_defense_jobs.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_jobs)} jobs to {out_path}")

    print(f"\n{'='*60}")
    print(f"SCRAPE COMPLETE")
    print(f"  Total jobs found across all queries : {total_found}")
    print(f"  New jobs inserted into DB           : {total_inserted}")
    print(f"  Duplicate/skipped                   : {total_skipped}")
    print(f"  Output JSON                         : {out_path}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
