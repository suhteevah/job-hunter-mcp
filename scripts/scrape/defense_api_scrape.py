"""Scrape defense contractors via their Radancy/Phenom APIs directly (no browser needed).
The Wraith hydrators found these API endpoints — we can call them with plain HTTP."""
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

# Radancy API pattern: GET /search-jobs/results?keyword=X&page=N
# Headers: X-Requested-With: XMLHttpRequest
RADANCY_SITES = {
    'boeing': {
        'base': 'https://jobs.boeing.com',
        'search': '/search-jobs/results',
        'queries': ['software engineer', 'firmware engineer', 'AI engineer', 'devops engineer',
                    'cybersecurity engineer', 'embedded engineer', 'cloud engineer', 'data engineer',
                    'python developer', 'automation engineer', 'test engineer'],
    },
    'l3harris': {
        'base': 'https://careers.l3harris.com',
        'search': '/en/search-jobs/results',
        'queries': ['software engineer', 'firmware engineer', 'embedded engineer',
                    'cybersecurity engineer', 'systems engineer', 'AI engineer'],
    },
    'lockheed': {
        'base': 'https://www.lockheedmartinjobs.com',
        'search': '/search-jobs/results',
        'queries': ['software engineer', 'firmware engineer', 'AI engineer',
                    'cybersecurity engineer', 'cloud engineer', 'embedded engineer'],
    },
}

# Phenom API pattern: POST /widgets with JSON body
PHENOM_SITES = {
    'mitre': {
        'base': 'https://careers.mitre.org',
        'queries': ['software engineer', 'cybersecurity engineer', 'AI engineer',
                    'data engineer', 'cloud engineer', 'systems engineer'],
    },
}

def radancy_scrape(company, config):
    """Scrape a Radancy site via its XHR API."""
    base = config['base']
    search = config['search']
    all_jobs = []
    seen_urls = set()

    for query in config['queries']:
        page = 1
        while page <= 20:  # Max 20 pages per query
            url = f"{base}{search}?keyword={urllib.request.quote(query)}&page={page}"
            req = urllib.request.Request(url, headers={
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/html, */*',
                'Referer': base,
            })

            try:
                resp = urllib.request.urlopen(req, timeout=30)
                content = resp.read().decode('utf-8', errors='replace')

                # Try JSON first
                try:
                    data = json.loads(content)
                    html = data.get('results', data.get('html', content))
                except json.JSONDecodeError:
                    html = content

                # Parse jobs from HTML
                # Pattern: <a href="/job/...">Title</a> <span>Location</span>
                job_links = re.findall(r'href="(/[^"]*?/job/[^"]+)"[^>]*>([^<]+)</a>', html)
                if not job_links:
                    # Alternative pattern
                    job_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>', html)

                if not job_links:
                    break

                new_count = 0
                for href, title in job_links:
                    title = title.strip()
                    if not title or 'Save' in title or len(title) < 5:
                        continue
                    job_url = base + href if href.startswith('/') else href
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Extract location from nearby text
                    loc_match = re.search(re.escape(title) + r'</span>\s*<span[^>]*>([^<]+)</span>', html)
                    location = loc_match.group(1).strip() if loc_match else ''

                    all_jobs.append({
                        'title': title,
                        'company': company.title(),
                        'url': job_url,
                        'location': location,
                        'source': company,
                    })
                    new_count += 1

                print(f"  [{company}] '{query}' page {page}: {new_count} new jobs")

                if new_count == 0:
                    break
                page += 1
                time.sleep(random.uniform(1, 3))

            except urllib.error.HTTPError as e:
                print(f"  [{company}] '{query}' page {page}: HTTP {e.code}")
                break
            except Exception as e:
                print(f"  [{company}] '{query}' page {page}: {e}")
                break

        time.sleep(random.uniform(2, 4))

    return all_jobs


def main():
    print("=== DEFENSE CONTRACTOR API SCRAPE ===\n")

    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=60000")

    total_inserted = 0

    # Radancy sites
    for company, config in RADANCY_SITES.items():
        print(f"\n--- {company.upper()} (Radancy API) ---")
        jobs = radancy_scrape(company, config)
        print(f"  Total found: {len(jobs)}")

        inserted = 0
        for j in jobs:
            jid = hashlib.md5(j['url'].encode()).hexdigest()[:16]
            try:
                db.execute("""INSERT OR IGNORE INTO jobs
                    (id, source, source_id, title, company, url, location, date_found, status, fit_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', 0)""",
                    (jid, j['source'], jid, j['title'], j['company'], j['url'],
                     j['location'], datetime.now(timezone.utc).isoformat()))
                inserted += 1
            except sqlite3.IntegrityError:
                pass
        db.commit()
        total_inserted += inserted
        print(f"  Inserted: {inserted}")

    print(f"\n=== DONE ===")
    print(f"Total inserted: {total_inserted}")
    print(f"Total DB: {db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")

if __name__ == "__main__":
    main()
