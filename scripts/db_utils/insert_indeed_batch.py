"""
insert_indeed_batch.py — Insert jobs from a JSON file into jobs.db
Usage: python insert_indeed_batch.py <path_to_jobs.json>

JSON format:
[
  {
    "title": "...",
    "company": "...",
    "url": "...",
    "location": "...",
    "description": "...",
    "job_key": "...",
    "fit_score": 0
  },
  ...
]
"""
import sys
import json
import sqlite3
import hashlib
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn

def insert_jobs(jobs):
    conn = get_db()
    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        url = job.get("url", "")
        jk = job.get("job_key", hashlib.sha256(url.encode()).hexdigest()[:12])
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
                jid, jk,
                job.get("title", "Unknown"),
                job.get("company", "Unknown"),
                url,
                job.get("location", ""),
                job.get("salary", ""),
                job.get("description", "")[:1000],
                now,
                job.get("fit_score", 0),
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as e:
            print(f"  DB error on '{job.get('title')}': {e}")
    conn.commit()
    conn.close()
    return inserted, skipped

def main():
    if len(sys.argv) < 2:
        print("Usage: python insert_indeed_batch.py <jobs.json>")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        jobs = json.load(f)
    print(f"Loaded {len(jobs)} jobs from {path}")
    inserted, skipped = insert_jobs(jobs)
    print(f"Inserted: {inserted} | Skipped (dupes): {skipped}")

if __name__ == "__main__":
    main()
