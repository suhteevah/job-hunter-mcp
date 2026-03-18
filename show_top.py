import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute("SELECT fit_score, title, company, url, source FROM jobs WHERE status != 'applied' ORDER BY fit_score DESC LIMIT 15")
print("SCORE | TITLE | COMPANY | URL")
for r in c.fetchall():
    score = r[0]
    title = (r[1] or "")[:50]
    company = (r[2] or "")[:20]
    url = (r[3] or "")[:80]
    print(f"  {score:5.0f} | {title:50s} | {company:20s} | {url}")
db.close()
