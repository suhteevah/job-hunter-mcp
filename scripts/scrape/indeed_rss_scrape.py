"""
Indeed RSS Scraper
==================
Uses Indeed's public RSS feed (no auth, no Cloudflare) to scrape recent jobs.
RSS URL: https://www.indeed.com/rss?q=...&sort=date&fromage=3&filter=0

Inserts results into SQLite DB.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import random
import re
import sqlite3
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

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
    """Extract job key from Indeed URL."""
    m = re.search(r'jk=([a-f0-9]+)', url)
    return m.group(1) if m else hashlib.sha256(url.encode()).hexdigest()[:16]


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


def parse_rss(content):
    """Parse Indeed RSS XML and return list of job dicts."""
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
        author_el = item.find('author')

        title = title_el.text.strip() if title_el is not None and title_el.text else "Unknown"
        url = link_el.text.strip() if link_el is not None and link_el.text else ""
        description_raw = desc_el.text or "" if desc_el is not None else ""
        author = author_el.text.strip() if author_el is not None and author_el.text else ""

        # Clean HTML from description
        description = re.sub(r'<[^>]+>', ' ', description_raw).strip()[:500]

        # Extract company and location from title (format: "Title - Company - Location")
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
            company = author or "Unknown"
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
        })

    return jobs


def fetch_rss(query, max_retries=3):
    """Fetch Indeed RSS feed for a query. Returns parsed content or None."""
    url = f"https://www.indeed.com/rss?q={query}&sort=date&fromage=3&filter=0&limit=50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                return content
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} on attempt {attempt+1}")
            if e.code == 403:
                print(f"  403 Forbidden - RSS blocked for this query")
                return None
            if attempt < max_retries - 1:
                time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"  Error on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(5, 10))
    return None


def main():
    print(f"=== INDEED RSS SCRAPE — {len(SEARCH_QUERIES)} queries ===")
    print(f"Source: Indeed RSS feed (no auth required)")
    print(f"Date filter: last 3 days\n")

    total_found = 0
    total_inserted = 0

    for qi, query in enumerate(SEARCH_QUERIES):
        print(f"[{qi+1}/{len(SEARCH_QUERIES)}] Query: {query.replace('+', ' ')}")

        content = fetch_rss(query)
        if content is None:
            print(f"  SKIP (no content)")
            # Still wait before next query
            time.sleep(random.uniform(3, 8))
            continue

        jobs = parse_rss(content)
        total_found += len(jobs)

        inserted = insert_jobs(jobs)
        total_inserted += inserted

        viable = sum(1 for j in jobs if j["fit_score"] >= 40)
        print(f"  Found: {len(jobs)}, New inserted: {inserted}, Viable (40+): {viable}")

        # Random delay 3-8 seconds between queries (as instructed)
        delay = random.uniform(3, 8)
        print(f"  Waiting {delay:.1f}s before next query...")
        time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"INDEED RSS SCRAPE COMPLETE")
    print(f"  Total jobs found: {total_found}")
    print(f"  New jobs inserted: {total_inserted}")
    print(f"{'='*60}")
    return total_inserted


if __name__ == "__main__":
    main()
