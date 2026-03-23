import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
total = c.fetchone()[0]
print(f"Total applied in DB: {total}")
print(f"Remaining to 100: {100 - total}")
conn.close()
