import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute("SELECT title, fit_score, status, source FROM jobs WHERE LOWER(company) LIKE '%mistral%' ORDER BY fit_score DESC LIMIT 30")
for r in c.fetchall():
    print(f"{r[1]} | {r[2]} | {r[3]} | {r[0][:70]}")
