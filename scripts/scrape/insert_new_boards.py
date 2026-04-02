#!/usr/bin/env python
"""
insert_new_boards.py
Reads the JSON file from more_boards_20260401.json and inserts into SQLite DB.
Uses the real schema: id, source, source_id, title, company, url, location,
date_found, fit_score, status, description

Usage:
    J:\\job-hunter-mcp\\.venv\\Scripts\\python.exe insert_new_boards.py
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import json
import uuid
import re
import html as html_module
import logging
from datetime import datetime

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
INPUT_JSON = r"J:\job-hunter-mcp\scripts\swarm\logs\more_boards_20260401.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ---------------------------------------------------------------------------
# Keywords for scoring
# ---------------------------------------------------------------------------
POSITIVE_KEYWORDS = [
    'ai engineer', 'ml engineer', 'machine learning', 'llm', 'genai', 'gen ai',
    'ai platform', 'ai infrastructure', 'agent', 'agentic', 'automation',
    'software engineer', 'backend engineer', 'full stack', 'fullstack',
    'python', 'rust', 'typescript', 'devops', 'sre', 'infrastructure',
    'platform engineer', 'mcp', 'model context', 'prompt engineer',
    'qa automation', 'test automation', 'sdet', 'quality engineer',
    'data engineer', 'api', 'developer tools', 'dev tools', 'sdk',
    'claude', 'chatbot', 'nlp', 'natural language', 'senior', 'staff',
]

NEGATIVE_KEYWORDS = [
    'intern', 'internship', 'new grad', 'phd required', 'director',
    'vp ', 'vice president', 'chief', 'head of', 'counsel', 'lawyer',
    'accountant', 'accounting', 'recruiter', 'recruiting',
    'account executive', 'marketing', 'communications',
    'graphic design', 'ux research',
    'policy', 'government', 'legal', 'tax ', 'payroll',
]

def score_job(title, location, description=''):
    title_lower = (title or '').lower()
    loc_lower = (location or '').lower()
    desc_lower = (description or '').lower()

    score = 50

    # Remote bonus
    if 'remote' in loc_lower or not loc_lower:
        score += 10

    for kw in POSITIVE_KEYWORDS:
        if kw in title_lower:
            score += 6
        elif kw in desc_lower:
            score += 2

    for kw in NEGATIVE_KEYWORDS:
        if kw in title_lower:
            score -= 25

    return min(100, max(0, score))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info(f"Reading {INPUT_JSON}")
    with open(INPUT_JSON, 'r', encoding='utf-8', errors='replace') as f:
        jobs = json.load(f)

    log.info(f"Loaded {len(jobs)} jobs from JSON")

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    by_source = {}

    for j in jobs:
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        url = (j.get("url") or "").strip()
        location = (j.get("location") or "Remote").strip()
        source = j.get("source", "unknown")
        description = (j.get("description") or "").strip()

        if not title or len(title) < 3:
            skipped += 1
            continue

        # Skip obvious non-jobs from HN
        if source == "hn_hiring" and len(title) > 200:
            skipped += 1
            continue

        # Dedup by URL first
        if url:
            cur.execute("SELECT id FROM jobs WHERE url = ?", (url,))
            if cur.fetchone():
                skipped += 1
                continue

        # Dedup by title + company
        cur.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company))
        if cur.fetchone():
            skipped += 1
            continue

        score = score_job(title, location, description)
        job_id = str(uuid.uuid4())[:8]

        try:
            cur.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  date_found, fit_score, status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """, (job_id, source, url[:200] if url else "", title[:500],
                  company[:300], url[:1000], location[:200],
                  NOW, score, description[:3000] if description else None))
            inserted += 1
            by_source[source] = by_source.get(source, 0) + 1
        except Exception as e:
            log.warning(f"Insert error for '{title}': {e}")
            skipped += 1

    conn.commit()
    conn.close()

    log.info(f"\n{'='*50}")
    log.info(f"INSERTION COMPLETE")
    log.info(f"  Inserted: {inserted}")
    log.info(f"  Skipped/dupe: {skipped}")
    log.info(f"\nBy source:")
    for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
        log.info(f"  {src}: {cnt}")
    log.info(f"{'='*50}")

if __name__ == "__main__":
    main()
