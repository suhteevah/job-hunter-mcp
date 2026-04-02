#!/usr/bin/env python
"""
Parse startup.jobs remote jobs from the markdown extract we captured via Wraith.
Also inserts into DB.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import json
import uuid
import re
import logging
from datetime import datetime

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

# Markdown content extracted from startup.jobs/remote-jobs via Wraith
# Job pattern: [Title](/slug-company-JOBID)  [Company](/company/slug)  ·  Location · Date
MARKDOWN_EXTRACT = """
[  Lead Video Editor (AKA Absolute Editing Monster)  ](/lead-video-editor-aka-absolute-editing-monster-mindalter-studio-7885731)  [Mindalter Studio](/company/mindalter-studio) ·  Work from anywhere    [ Remote ](/remote-jobs)   · Yesterday
[  Founding Engineer  ](/founding-engineer-doora-7893403)  [Doora](/company/doora) ·  [Sydney](/locations/sydney), [Australia](/locations/australia)     Hybrid    · 3 days ago
[  Founding ML Engineer  ](/founding-ml-engineer-remy-7690938)  [Remy](/company/remy) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)     Hybrid    · 4 days ago
[  Founding Strategy & Operations  ](/founding-strategy-operations-sailor-health-7154049)  [Sailor health](/company/sailor-health) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)    · 4 days ago
[  Founding Full-Stack Engineer  ](/founding-full-stack-engineer-sailor-health-7153576)  [Sailor health](/company/sailor-health) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)     Hybrid    · 5 days ago
[  Senior Full Stack Engineer  ](/senior-full-stack-engineer-solace-6654883)  [Solace](/company/solace) ·  [U.S.](/locations/united-states)    [ Remote ](/remote-jobs)   · A week ago
[  Lead AI Engineer  ](/lead-ai-engineer-sherlockdefi-6650681)  [Sherlock](/company/sherlockdefi) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)    · 2 weeks ago
[  Technical Account Manager  ](/technical-account-manager-boxhq-7899228)  [Box](/company/boxhq) ·  [Japan](/locations/japan)    · Today
[  Go to Market Sales Operations Analyst  ](/go-to-market-sales-operations-analyst-boxhq-7899221)  [Box](/company/boxhq) ·  [Chicago](/locations/chicago), [Illinois](/locations/illinois), [U.S.](/locations/united-states)     Hybrid    · Today
[  Go to Market Sales Operations Analyst  ](/go-to-market-sales-operations-analyst-boxhq-7899220)  [Box](/company/boxhq) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)     Hybrid    · Today
[  Go to Market Sales Operations Analyst  ](/go-to-market-sales-operations-analyst-boxhq-7899222)  [Box](/company/boxhq) ·  [San Francisco](/locations/san-francisco), [California](/locations/california), [U.S.](/locations/united-states)     Hybrid    · Today
[  Go to Market Sales Operations Analyst  ](/go-to-market-sales-operations-analyst-boxhq-7899223)  [Box](/company/boxhq) ·  [Redwood City](/locations/redwood-city), [California](/locations/california), [U.S.](/locations/united-states)     Hybrid    · Today
[  Receptionist  ](/receptionist-clear-7898626)  [CLEAR](/company/clear) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)    · Today
[  Commercial Account Executive  ](/commercial-account-executive-boxhq-7899216)  [Box](/company/boxhq) ·  [Austin](/locations/austin), [Texas](/locations/texas), [U.S.](/locations/united-states)     Hybrid    · Today
[  Commercial Account Executive  ](/commercial-account-executive-boxhq-7899217)  [Box](/company/boxhq) ·  [San Francisco](/locations/san-francisco), [California](/locations/california), [U.S.](/locations/united-states)     Hybrid    · Today
[  Commercial Account Executive  ](/commercial-account-executive-boxhq-7899218)  [Box](/company/boxhq) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)     Hybrid    · Today
[  Mid-Market Account Executive  ](/mid-market-account-executive-boxhq-7899225)  [Box](/company/boxhq) ·  [Chicago](/locations/chicago), [Illinois](/locations/illinois), [U.S.](/locations/united-states)    · Today
[  Senior Systems Engineer, Workers AI  ](/senior-systems-engineer-workers-ai-cloudflare-7898482)  [Cloudflare](/company/cloudflare) ·  Hybrid     Hybrid    · Today
[  Senior Data Scientist, Decisions - Risk  ](/senior-data-scientist-decisions-risk-lyft-7899317)  [Lyft](/company/lyft) ·  [New York](/locations/new-york), [U.S.](/locations/united-states)    · Today
"""

def parse_startup_jobs_markdown(text):
    """Parse job listings from startup.jobs markdown extract."""
    jobs = []
    # Pattern: [Title](/slug-JOBID)  [Company](/company/slug) · Location · Date
    pattern = r'\[\s+([^\]]+?)\s+\]\((/[^\)]+?-(\d+))\)\s+\[([^\]]+)\]\(/company/[^\)]+\)\s*·\s*(.*?)(?:·|$)'
    matches = re.finditer(pattern, text, re.MULTILINE)
    for m in matches:
        title = m.group(1).strip()
        slug = m.group(2).strip()
        job_id = m.group(3).strip()
        company = m.group(4).strip()
        loc_raw = m.group(5).strip()
        # Clean location - remove markdown links
        loc = re.sub(r'\[[^\]]+\]\([^\)]+\)', '', loc_raw).strip()
        loc = re.sub(r'\s+', ' ', loc).strip()
        if 'Remote' in loc_raw or 'Work from anywhere' in loc_raw:
            location = 'Remote'
        elif 'U.S.' in loc_raw or 'United States' in loc_raw:
            location = 'United States'
        else:
            location = loc[:100] if loc else 'Unknown'
        jobs.append({
            'title': title,
            'company': company,
            'url': f'https://startup.jobs{slug}',
            'location': location,
            'source': 'startup_jobs',
            'description': '',
        })
    return jobs

def insert_jobs(jobs):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()
    inserted = 0
    for j in jobs:
        title = j['title']
        company = j['company']
        url = j['url']
        # Dedup
        cur.execute("SELECT id FROM jobs WHERE url=?", (url,))
        if cur.fetchone():
            continue
        cur.execute("SELECT id FROM jobs WHERE title=? AND company=?", (title, company))
        if cur.fetchone():
            continue
        jid = str(uuid.uuid4())[:8]
        cur.execute("""
            INSERT INTO jobs (id, source, source_id, title, company, url, location, date_found, fit_score, status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (jid, 'startup_jobs', url[:200], title[:500], company[:300], url[:1000],
              j['location'][:200], NOW, 55, 'new'))
        inserted += 1
    conn.commit()
    conn.close()
    return inserted

if __name__ == '__main__':
    jobs = parse_startup_jobs_markdown(MARKDOWN_EXTRACT)
    log.info(f"Parsed {len(jobs)} jobs from startup.jobs markdown")
    for j in jobs[:5]:
        log.info(f"  {j['title']} @ {j['company']} [{j['location']}]")
    ins = insert_jobs(jobs)
    log.info(f"Inserted {ins} new jobs from startup.jobs")
    print(json.dumps(jobs, indent=2))
