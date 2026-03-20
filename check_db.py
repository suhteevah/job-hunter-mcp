import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM jobs')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
applied = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'applied' AND fit_score >= 60")
viable = c.fetchone()[0]
print(f'Total: {total} | Applied: {applied} | Viable unapplied (score>=60): {viable}')
print('\nTop 15 unapplied (score >= 60):')
c.execute("SELECT id, title, company, fit_score, url FROM jobs WHERE status != 'applied' AND fit_score >= 60 ORDER BY fit_score DESC LIMIT 15")
for r in c.fetchall():
    url = (r[4] or 'no url')[:90]
    print(f'  [{r[3]}] {r[1]} @ {r[2]} — {url}')
print('\nDistinct statuses:')
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')
