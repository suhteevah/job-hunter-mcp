import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
print(f"Total applied: {c.fetchone()[0]}")
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")
