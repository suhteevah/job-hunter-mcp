import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM jobs WHERE fit_score = 0 OR fit_score IS NULL')
print(f"Zero/NULL scores: {c.fetchone()[0]}")
c.execute('SELECT COUNT(*) FROM jobs WHERE fit_score > 0')
print(f"Scored > 0: {c.fetchone()[0]}")
# Check if the Ashby swarm has been marking things applied
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
print(f"Applied: {c.fetchone()[0]}")
# Check a specific Mistral Applied AI job
c.execute("SELECT fit_score, fit_reason FROM jobs WHERE title LIKE 'Applied AI Engineer%' AND LOWER(company) = 'mistral' LIMIT 3")
for r in c.fetchall():
    print(f"  Mistral Applied AI: score={r[0]}, reason={r[1]}")
