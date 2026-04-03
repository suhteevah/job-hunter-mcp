"""
insert_indeed_deep.py
Read JSON from scripts/swarm/logs/indeed_deep_20260402.json
Insert into SQLite jobs.db with source='indeed', status='new'
"""
import sys, json, sqlite3, hashlib, os
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

JSON_PATH = r"J:\job-hunter-mcp\scripts\swarm\logs\indeed_deep_20260402.json"
DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

def make_id(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def main():
    print(f"Reading {JSON_PATH}...")
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total records in JSON: {len(data)}")

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            source TEXT,
            status TEXT DEFAULT 'new',
            fit_score REAL DEFAULT 0,
            created_at TEXT,
            query TEXT
        )
    """)
    conn.commit()

    inserted = 0
    skipped = 0
    by_query = {}

    now = datetime.utcnow().isoformat()

    for job in data:
        url = job.get('url', '')
        if not url:
            continue
        job_id = make_id(url)
        title = job.get('title', '')
        company = job.get('company', '')
        location = job.get('location', '')
        source = 'indeed'
        status = 'new'
        fit_score = 0
        query = job.get('query', '')

        try:
            cur.execute("""
                INSERT OR IGNORE INTO jobs (id, title, company, location, url, source, status, fit_score, created_at, query)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, title, company, location, url, source, status, fit_score, now, query))
            if cur.rowcount > 0:
                inserted += 1
                by_query[query] = by_query.get(query, 0) + 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR inserting {url}: {e}")

    conn.commit()
    conn.close()

    print(f"\nInserted: {inserted}")
    print(f"Skipped (already exists): {skipped}")
    print(f"\nPer-query breakdown:")
    for q, count in sorted(by_query.items(), key=lambda x: -x[1]):
        print(f"  {q}: {count}")

if __name__ == '__main__':
    main()
