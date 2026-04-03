"""Scrape defense contractors via Wraith native hydrators + extract_markdown.
Boeing, L3Harris, Lockheed, MITRE — all use Radancy/Phenom hydrators."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import re
import sqlite3
import time
import random
import json
from datetime import datetime, timezone
sys.path.insert(0, r"J:\job-hunter-mcp\scripts\swarm")
from wraith_mcp_client import WraithMCPClient

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

SITES = [
    {
        'name': 'boeing', 'company': 'Boeing',
        'base': 'https://jobs.boeing.com',
        'url_template': 'https://jobs.boeing.com/search?keyword={query}&page={page}',
        'queries': ['software engineer', 'firmware engineer', 'AI engineer',
                    'devops engineer', 'cybersecurity engineer', 'embedded engineer',
                    'cloud engineer', 'data engineer', 'python', 'automation engineer',
                    'test engineer', 'network engineer'],
        'max_pages': 5,
    },
    {
        'name': 'l3harris', 'company': 'L3Harris',
        'base': 'https://careers.l3harris.com',
        'url_template': 'https://careers.l3harris.com/en/search-jobs?keyword={query}&page={page}',
        'queries': ['software engineer', 'firmware engineer', 'embedded engineer',
                    'cybersecurity engineer', 'systems engineer', 'AI engineer',
                    'test engineer', 'devops engineer'],
        'max_pages': 5,
    },
    {
        'name': 'lockheed', 'company': 'Lockheed Martin',
        'base': 'https://www.lockheedmartinjobs.com',
        'url_template': 'https://www.lockheedmartinjobs.com/search?keyword={query}&page={page}',
        'queries': ['software engineer', 'firmware engineer', 'AI engineer',
                    'cybersecurity engineer', 'cloud engineer', 'embedded engineer',
                    'systems engineer', 'test engineer'],
        'max_pages': 5,
    },
    {
        'name': 'mitre', 'company': 'MITRE',
        'base': 'https://careers.mitre.org',
        'url_template': 'https://careers.mitre.org/us/en/search-results?keywords={query}&from={offset}&s=1',
        'queries': ['software engineer', 'cybersecurity engineer', 'AI engineer',
                    'data engineer', 'cloud engineer', 'systems engineer'],
        'max_pages': 3,
        'uses_offset': True,
        'per_page': 25,
    },
]

def parse_radancy_markdown(md, base_url):
    """Parse job listings from Radancy extract_markdown output."""
    jobs = []
    # Pattern: [Title](/job/city/slug/companyid/jobid) Location Date
    pattern = re.compile(r'\[([^\]]+)\]\((/job/[^\)]+)\)\s*([^\d]*?)\s*(\d{2}/\d{2}/\d{4})?')
    for m in pattern.finditer(md):
        title = m.group(1).strip()
        path = m.group(2).strip()
        location = m.group(3).strip().rstrip(' ')
        if 'Save' in title or len(title) < 5:
            continue
        url = base_url + path
        jobs.append({'title': title, 'url': url, 'location': location})
    return jobs

def parse_phenom_markdown(md, base_url):
    """Parse job listings from Phenom extract_markdown output."""
    jobs = []
    # Pattern: [Title](url) or similar markdown links
    pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
    for m in pattern.finditer(md):
        title = m.group(1).strip()
        url = m.group(2).strip()
        if 'Save' in title or len(title) < 5 or 'careers' not in url:
            continue
        jobs.append({'title': title, 'url': url, 'location': ''})
    return jobs

def main():
    print("=== DEFENSE CONTRACTOR WRAITH SCRAPE ===")
    wraith = WraithMCPClient()

    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=60000")

    grand_total = 0

    for site in SITES:
        name = site['name']
        company = site['company']
        base = site['base']
        print(f"\n{'='*60}")
        print(f"{company.upper()} ({name})")
        print(f"{'='*60}")

        seen_urls = set()
        site_total = 0

        for query in site['queries']:
            print(f"\n  Query: '{query}'")

            for page in range(1, site['max_pages'] + 1):
                if site.get('uses_offset'):
                    offset = (page - 1) * site.get('per_page', 25)
                    url = site['url_template'].format(query=query.replace(' ', '+'), offset=offset)
                else:
                    url = site['url_template'].format(query=query.replace(' ', '+'), page=page)

                delay = random.uniform(3, 6)
                time.sleep(delay)

                try:
                    snap = wraith.navigate(url)
                    md = wraith.call('extract_markdown', {})

                    if isinstance(md, dict):
                        md = md.get('text', md.get('markdown', str(md)))

                    if 'radancy' in name or name in ('boeing', 'l3harris', 'lockheed'):
                        jobs = parse_radancy_markdown(md, base)
                    else:
                        jobs = parse_phenom_markdown(md, base)

                    new_jobs = [j for j in jobs if j['url'] not in seen_urls]
                    for j in new_jobs:
                        seen_urls.add(j['url'])

                    print(f"    Page {page}: {len(new_jobs)} new jobs")

                    if len(new_jobs) == 0:
                        break

                    # Insert into DB
                    inserted = 0
                    for j in new_jobs:
                        jid = hashlib.md5(j['url'].encode()).hexdigest()[:16]
                        try:
                            db.execute("""INSERT OR IGNORE INTO jobs
                                (id, source, source_id, title, company, url, location,
                                 date_found, status, fit_score)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', 0)""",
                                (jid, name, jid, j['title'], company, j['url'],
                                 j['location'], datetime.now(timezone.utc).isoformat()))
                            inserted += 1
                        except sqlite3.IntegrityError:
                            pass
                    db.commit()
                    site_total += inserted

                except Exception as e:
                    print(f"    Page {page}: ERROR - {e}")
                    break

            time.sleep(random.uniform(2, 4))

        print(f"\n  {company} total inserted: {site_total}")
        grand_total += site_total

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL INSERTED: {grand_total}")
    print(f"Total DB: {db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
