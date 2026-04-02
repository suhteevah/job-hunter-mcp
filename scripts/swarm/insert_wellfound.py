import sys, json, sqlite3, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'J:\job-hunter-mcp\scripts\swarm\logs\wellfound_jobs_20260401.json') as f:
    jobs = json.load(f)

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=60000')

inserted = 0
skipped = 0
for j in jobs:
    jid = hashlib.md5(j['url'].encode()).hexdigest()[:16]
    try:
        cur = db.execute(
            'INSERT OR IGNORE INTO jobs (id, source, source_id, title, company, url, location, date_found, status, fit_score) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now"), "new", 0)',
            (jid, 'wellfound', jid, j['title'], j['company'], j['url'], j.get('location', 'Remote'))
        )
        if cur.rowcount > 0:
            inserted += 1
        else:
            skipped += 1
    except Exception as e:
        print(f'Error inserting {j["url"]}: {e}')

db.commit()
db.close()
print(f'Inserted {inserted} new Wellfound jobs ({skipped} already existed)')
