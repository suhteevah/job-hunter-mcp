import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db', timeout=60)
db.execute('PRAGMA busy_timeout=60000')
c = db.cursor()
c.execute("UPDATE jobs SET status='new' WHERE source='lever' AND status='apply_failed' AND fit_score >= 60")
count = c.rowcount
db.commit()
print(f"Reset {count} lever apply_failed jobs back to new")
c.execute("SELECT COUNT(*) FROM jobs WHERE source='lever' AND fit_score >= 60 AND status='new'")
print(f"Lever jobs ready: {c.fetchone()[0]}")
