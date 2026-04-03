#!/usr/bin/env python3
"""Insert defense contractor jobs from JSON into SQLite DB."""
import sys
import json
import sqlite3
import os
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
JSON_PATH = r'J:\job-hunter-mcp\scripts\swarm\defense_jobs.json'

print(f"Loading jobs from {JSON_PATH}...")
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

jobs = data['jobs']
print(f"Loaded {len(jobs)} jobs")

print(f"Connecting to DB: {DB_PATH}")
conn = sqlite3.connect(DB_PATH, timeout=60)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=60000")
cur = conn.cursor()

# Check existing schema
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
if not cur.fetchone():
    print("ERROR: jobs table does not exist!")
    conn.close()
    sys.exit(1)

# Get column names
cur.execute("PRAGMA table_info(jobs)")
cols = [row[1] for row in cur.fetchall()]
print(f"Table columns: {cols}")

# Check for URL column name (might be 'url' or 'apply_url' or 'job_url')
url_col = None
for c in ['url', 'apply_url', 'job_url', 'link']:
    if c in cols:
        url_col = c
        break

if not url_col:
    print(f"ERROR: No URL column found. Columns: {cols}")
    conn.close()
    sys.exit(1)

print(f"Using URL column: {url_col}")

# Get title column
title_col = 'title' if 'title' in cols else 'job_title'
# Get company/source column
company_col = None
for c in ['company', 'source', 'employer']:
    if c in cols:
        company_col = c
        break

print(f"Title col: {title_col}, Company col: {company_col}")

inserted = 0
skipped = 0
errors = 0

now = datetime.now().isoformat()

for job in jobs:
    url = job.get('url', '')
    title = job.get('title', '')
    location = job.get('location', '')
    source = job.get('source', '')
    category = job.get('category', '')

    if not url:
        errors += 1
        continue

    # Check if URL already exists
    cur.execute(f"SELECT id FROM jobs WHERE {url_col} = ?", (url,))
    if cur.fetchone():
        skipped += 1
        continue

    # Build insert based on available columns
    insert_data = {}
    if title_col in cols:
        insert_data[title_col] = title
    if url_col in cols:
        insert_data[url_col] = url
    if 'location' in cols:
        insert_data['location'] = location
    # 'source' column = the source/board identifier (l3harris, lockheed, mitre)
    if 'source' in cols:
        insert_data['source'] = source
    if company_col and company_col != 'source':
        # company_col is 'company' - store the company name
        company_map = {'l3harris': 'L3Harris', 'lockheed': 'Lockheed Martin', 'mitre': 'MITRE'}
        insert_data[company_col] = company_map.get(source, source)
    if 'category' in cols:
        insert_data['category'] = category
    if 'status' in cols:
        insert_data['status'] = 'new'
    if 'created_at' in cols:
        insert_data['created_at'] = now
    if 'updated_at' in cols:
        insert_data['updated_at'] = now
    if 'scraped_at' in cols:
        insert_data['scraped_at'] = now
    if 'date_found' in cols:
        insert_data['date_found'] = now[:10]
    if 'score' in cols:
        insert_data['score'] = None
    if 'applied' in cols:
        insert_data['applied'] = 0
    if 'platform' in cols:
        insert_data['platform'] = source
    if 'board' in cols:
        insert_data['board'] = source

    cols_str = ', '.join(insert_data.keys())
    placeholders = ', '.join(['?' for _ in insert_data])
    values = list(insert_data.values())

    try:
        cur.execute(f"INSERT INTO jobs ({cols_str}) VALUES ({placeholders})", values)
        inserted += 1
    except sqlite3.Error as e:
        print(f"  Error inserting {title}: {e}")
        errors += 1

conn.commit()
conn.close()

print(f"\nInsert complete:")
print(f"  Inserted: {inserted}")
print(f"  Skipped (duplicate): {skipped}")
print(f"  Errors: {errors}")
print(f"\nPer source:")
for src in ['l3harris', 'lockheed', 'mitre']:
    src_jobs = [j for j in jobs if j['source'] == src]
    print(f"  {src}: {len(src_jobs)} total in JSON")
