"""Insert jobs from more_boards JSON file, handling column mismatches."""
import sys, json, sqlite3, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'J:\job-hunter-mcp\scripts\swarm\logs\more_boards_20260401.json', encoding='utf-8', errors='replace') as f:
    jobs = json.load(f)

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=60000')

inserted = 0
dupes = 0
for j in jobs:
    url = j.get('url', '')
    if not url:
        continue
    jid = hashlib.md5(url.encode()).hexdigest()[:16]
    source = j.get('source', 'unknown')
    title = j.get('title', 'Unknown')
    company = j.get('company', 'Unknown')
    location = j.get('location', 'Remote')

    try:
        db.execute("""INSERT OR IGNORE INTO jobs
            (id, source, source_id, title, company, url, location, date_found, status, fit_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), 'new', 0)""",
            (jid, source, jid, title, company, url, location))
        if db.total_changes:
            inserted += 1
        else:
            dupes += 1
    except sqlite3.IntegrityError:
        dupes += 1

db.commit()
print(f"Inserted: {inserted}, Dupes: {dupes}, Total in file: {len(jobs)}")

# Count by source
for src in set(j.get('source', 'unknown') for j in jobs):
    count = sum(1 for j in jobs if j.get('source') == src)
    print(f"  {src}: {count} in file")

print(f"\nTotal DB: {db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")
