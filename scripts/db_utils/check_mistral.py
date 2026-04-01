import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute("SELECT DISTINCT company FROM jobs WHERE LOWER(company) LIKE '%mistral%'")
companies = c.fetchall()
print(f"Mistral company names: {companies}")

c.execute("SELECT title, fit_score, status, source FROM jobs WHERE LOWER(company) LIKE '%mistral%' AND fit_score >= 60 ORDER BY fit_score DESC LIMIT 20")
for r in c.fetchall():
    print(f"{r[1]} | {r[2]} | {r[3]} | {r[0][:60]}")

# Also check lever jobs with high scores
c.execute("SELECT title, company, fit_score, status FROM jobs WHERE source='lever' AND fit_score >= 60 AND status='new' ORDER BY fit_score DESC LIMIT 20")
rows = c.fetchall()
print(f"\nLever score>=60 new: {len(rows)}")
for r in rows:
    print(f"  {r[2]} | {r[3]} | {r[1]} | {r[0][:50]}")
