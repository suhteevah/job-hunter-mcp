#!/usr/bin/env python
"""
scrape_builtin.py
Scrapes BuiltIn.com remote jobs using their public API endpoint.
BuiltIn uses a REST API that returns JSON data.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import json
import uuid
import re
import logging
import time
import random
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://builtin.com/jobs/remote",
}

def fetch_builtin_api(page=1, per_page=100, title="engineer"):
    """Try BuiltIn's internal API"""
    import urllib.parse
    # BuiltIn uses a Drupal/custom backend - try various endpoints
    urls = [
        f"https://builtin.com/en/api/job/remote?title={urllib.parse.quote(title)}&page={page}&items_per_page={per_page}",
        f"https://builtin.com/api/v1/jobs?remote=true&title={urllib.parse.quote(title)}&page={page}&per_page={per_page}",
        f"https://builtin.com/jsonapi/node/job?filter%5Bremote%5D=1&page%5Boffset%5D={(page-1)*per_page}&page%5Blimit%5D={per_page}",
    ]
    for url in urls:
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode('utf-8', errors='replace'))
                return data, url
        except Exception as e:
            log.debug(f"  API try failed: {url}: {e}")
    return None, None

def fetch_builtin_html(page=1, title="engineer"):
    """Fetch BuiltIn HTML page and parse jobs from it"""
    import urllib.parse
    url = f"https://builtin.com/jobs/remote?title={urllib.parse.quote(title)}&page={page}"
    try:
        req = Request(url, headers={**HEADERS, "Accept": "text/html,*/*"})
        with urlopen(req, timeout=20) as r:
            html = r.read().decode('utf-8', errors='replace')
            return html, url
    except Exception as e:
        log.warning(f"Failed fetching BuiltIn page {page}: {e}")
        return None, url

def parse_builtin_html(html):
    """Parse job listings from BuiltIn HTML"""
    jobs = []
    if not html:
        return jobs

    # Look for JSON-LD data
    ld_matches = re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld.strip())
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'JobPosting':
                        jobs.append({
                            'title': item.get('title', ''),
                            'company': item.get('hiringOrganization', {}).get('name', '') if isinstance(item.get('hiringOrganization'), dict) else '',
                            'url': item.get('url', ''),
                            'location': 'Remote',
                            'source': 'builtin',
                            'description': item.get('description', '')[:2000],
                        })
            elif isinstance(data, dict) and data.get('@type') == 'JobPosting':
                jobs.append({
                    'title': data.get('title', ''),
                    'company': data.get('hiringOrganization', {}).get('name', '') if isinstance(data.get('hiringOrganization'), dict) else '',
                    'url': data.get('url', ''),
                    'location': 'Remote',
                    'source': 'builtin',
                    'description': data.get('description', '')[:2000],
                })
        except:
            pass

    if jobs:
        return jobs

    # Pattern: ## [Job Title](/job/slug/ID)
    job_pattern = r'##\s+\[([^\]]+)\]\(/job/([^/\)]+)/(\d+)\)'
    company_pattern = r'\[([^\]]+)\]\(/company/([^\)]+)\)'

    # Find all jobs with surrounding context
    job_matches = list(re.finditer(job_pattern, html))
    for m in job_matches:
        title = m.group(1).strip()
        slug = m.group(2).strip()
        job_id = m.group(3).strip()
        job_url = f"https://builtin.com/job/{slug}/{job_id}"

        # Look for company name nearby (within 500 chars before)
        start = max(0, m.start() - 500)
        context = html[start:m.start()]
        company_m = list(re.finditer(company_pattern, context))
        company = company_m[-1].group(1).strip() if company_m else "BuiltIn"

        # Look for location nearby (within 200 chars after)
        after = html[m.end():m.end()+300]
        loc = "Remote"
        if 'Remote' in after:
            loc = 'Remote'
        elif 'United States' in after:
            loc = 'United States'

        jobs.append({
            'title': title,
            'company': company,
            'url': job_url,
            'location': loc,
            'source': 'builtin',
            'description': '',
        })

    return jobs

def insert_jobs(jobs, conn=None):
    close_after = conn is None
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()
    inserted = 0
    for j in jobs:
        title = (j.get('title') or '').strip()
        company = (j.get('company') or '').strip()
        url = (j.get('url') or '').strip()
        if not title or len(title) < 3:
            continue
        if url:
            cur.execute("SELECT id FROM jobs WHERE url=?", (url,))
            if cur.fetchone():
                continue
        cur.execute("SELECT id FROM jobs WHERE title=? AND company=?", (title, company))
        if cur.fetchone():
            continue
        jid = str(uuid.uuid4())[:8]
        try:
            cur.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location, date_found, fit_score, status, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (jid, 'builtin', url[:200], title[:500], company[:300], url[:1000],
                  j.get('location', 'Remote')[:200], NOW, 55, 'new',
                  (j.get('description') or '')[:3000]))
            inserted += 1
        except Exception as e:
            log.warning(f"Insert error: {e}")
    conn.commit()
    if close_after:
        conn.close()
    return inserted

def main():
    total_jobs = []
    total_inserted = 0
    queries = ["engineer", "developer", "python", "devops", "data scientist", "machine learning"]

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")

    for q in queries:
        log.info(f"BuiltIn query: '{q}'")
        for page in range(1, 6):  # 5 pages per query
            html, url = fetch_builtin_html(page=page, title=q)
            if not html:
                break
            jobs = parse_builtin_html(html)
            if not jobs:
                log.info(f"  Page {page}: no jobs parsed, stopping")
                break
            log.info(f"  Page {page}: {len(jobs)} jobs parsed")
            ins = insert_jobs(jobs, conn)
            total_inserted += ins
            total_jobs.extend(jobs)
            if len(jobs) < 10:
                break
            time.sleep(random.uniform(2, 4))

    conn.close()
    log.info(f"\nBuiltIn total collected: {len(total_jobs)}, inserted: {total_inserted}")
    return total_jobs

if __name__ == '__main__':
    main()
