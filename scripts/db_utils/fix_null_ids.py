import sys, sqlite3, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA busy_timeout=60000')

null_ids = db.execute("SELECT rowid, source, url, title FROM jobs WHERE id IS NULL").fetchall()
print(f"Fixing {len(null_ids)} NULL IDs...")
fixed = 0
dupes = 0
for rowid, source, url, title in null_ids:
    new_id = hashlib.md5(f"{source}:{url}:{rowid}".encode()).hexdigest()[:16]
    try:
        db.execute('UPDATE jobs SET id = ? WHERE rowid = ?', (new_id, rowid))
        fixed += 1
    except sqlite3.IntegrityError:
        dupes += 1
db.commit()
print(f"Fixed: {fixed}, Dupes skipped: {dupes}")

# Verify scores
ready = db.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
print(f"\nReady to apply by source:")
total = 0
for r in ready:
    print(f"  {r[0]}: {r[1]}")
    total += r[1]
print(f"  TOTAL: {total}")
