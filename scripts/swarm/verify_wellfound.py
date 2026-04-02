import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
rows = db.execute("SELECT title, company, url, location FROM jobs WHERE source='wellfound' ORDER BY date_found DESC LIMIT 20").fetchall()
print(f"Total wellfound jobs: {len(rows)}")
for r in rows:
    print(f"  {r[0]} | {r[1]} | {r[3]}")
db.close()
