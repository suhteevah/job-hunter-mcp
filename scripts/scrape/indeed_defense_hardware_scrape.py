"""
indeed_defense_hardware_scrape.py
===================================
Scrapes Indeed RSS for government, defense, and hardware engineering jobs.
Uses RSS endpoint (no Cloudflare, no auth needed).
Inserts results into SQLite DB via insert_indeed_batch.py pattern.

Queries target: Honeywell, ERC, firmware, embedded, PCB, hardware test,
                government SW, cleared SW, Booz Allen, Peraton
"""
import sys
import hashlib
import json
import random
import re
import sqlite3
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# The 10 queries from the task (converted to RSS-compatible q= params)
SEARCH_QUERIES = [
    ("Honeywell+engineer",                  "Honeywell engineer"),
    ("ERC+engineer",                        "ERC engineer"),
    ("firmware+engineer+remote",            "firmware engineer remote"),
    ("embedded+systems+engineer+remote",    "embedded systems engineer remote"),
    ("PCB+design+engineer",                 "PCB design engineer"),
    ("hardware+test+engineer",              "hardware test engineer"),
    ("government+software+engineer+remote", "government software engineer remote"),
    ("cleared+software+engineer+remote",    "cleared software engineer remote"),
    ("Booz+Allen+engineer",                 "Booz Allen engineer"),
    ("Peraton+engineer",                    "Peraton engineer"),
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
                job.get("description", ""),
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


def parse_rss(content, label):
    jobs = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return jobs

    channel = root.find('channel')
    if channel is None:
        return jobs

    for item in channel.findall('item'):
        title_el = item.find('title')
        link_el = item.find('link')
        desc_el = item.find('description')

        title = title_el.text.strip() if title_el is not None and title_el.text else "Unknown"
        url = link_el.text.strip() if link_el is not None and link_el.text else ""
        description_raw = desc_el.text or "" if desc_el is not None else ""
        description = re.sub(r'<[^>]+>', ' ', description_raw).strip()[:800]

        # Indeed RSS title format: "Job Title - Company - Location"
        parts = [p.strip() for p in title.split(' - ')]
        if len(parts) >= 3:
            job_title = parts[0]
            company = parts[1]
            location = parts[2]
        elif len(parts) == 2:
            job_title = parts[0]
            company = parts[1]
            location = ""
        else:
            job_title = title
            company = "Unknown"
            location = ""

        if not url:
            continue

        jk = extract_jk(url)
        fit = score_job(job_title, description)

        jobs.append({
            "title": job_title,
            "company": company,
            "url": url,
            "location": location,
            "description": description,
            "job_key": jk,
            "fit_score": fit,
            "query": label,
        })

    return jobs


def fetch_rss(query_param, label, max_retries=3):
    url = f"https://www.indeed.com/rss?q={query_param}&sort=date&fromage=7&filter=0&limit=50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    print(f"  Fetching: {url}")
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                return content
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} on attempt {attempt+1}")
            if e.code in (403, 429):
                print(f"  Rate limited or blocked, backing off...")
                time.sleep(random.uniform(15, 25))
            elif attempt < max_retries - 1:
                time.sleep(random.uniform(5, 12))
        except Exception as e:
            print(f"  Error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(5, 12))
    return None


def main():
    print(f"=== INDEED DEFENSE/HARDWARE/GOVERNMENT SCRAPE ===")
    print(f"Queries: {len(SEARCH_QUERIES)} | Date filter: last 7 days")
    print(f"DB: {DB_PATH}\n")

    all_jobs = []
    total_found = 0
    total_inserted = 0
    total_skipped = 0

    for qi, (q_param, q_label) in enumerate(SEARCH_QUERIES):
        print(f"[{qi+1}/{len(SEARCH_QUERIES)}] Query: '{q_label}'")

        content = fetch_rss(q_param, q_label)
        if content is None:
            print(f"  SKIP — no content returned")
            time.sleep(random.uniform(3, 8))
            continue

        jobs = parse_rss(content, q_label)
        total_found += len(jobs)
        all_jobs.extend(jobs)

        inserted, skipped = insert_jobs_db(jobs)
        total_inserted += inserted
        total_skipped += skipped

        viable = sum(1 for j in jobs if j["fit_score"] >= 40)
        print(f"  Found: {len(jobs)} | New: {inserted} | Dupes: {skipped} | Viable(40+): {viable}")
        if jobs:
            for j in jobs[:3]:
                print(f"    - [{j['fit_score']:3d}] {j['title']} @ {j['company']} ({j['location']})")
            if len(jobs) > 3:
                print(f"    ... and {len(jobs)-3} more")

        if qi < len(SEARCH_QUERIES) - 1:
            delay = random.uniform(3, 8)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Save full job list to JSON for reference
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


if __name__ == "__main__":
    main()
