import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute("SELECT title, url FROM jobs WHERE LOWER(company) = 'mistral' AND fit_score >= 60 ORDER BY fit_score DESC LIMIT 10")
for r in c.fetchall():
    print(f"{r[0][:50]} | {r[1]}")
