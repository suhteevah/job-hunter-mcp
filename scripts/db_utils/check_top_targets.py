import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

# Updated stats
c.execute('SELECT COUNT(*) FROM jobs')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
applied = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'applied' AND fit_score >= 60")
viable = c.fetchone()[0]
print(f'=== DB STATS ===')
print(f'Total: {total} | Applied: {applied} | Viable unapplied (score>=60): {viable}')

# Top 25 unapplied by score - the apply targets
print(f'\n=== TOP 25 APPLY TARGETS ===')
c.execute("""
    SELECT title, company, fit_score, url, location, source
    FROM jobs WHERE status != 'applied' AND fit_score >= 65
    ORDER BY fit_score DESC LIMIT 25
""")
for i, r in enumerate(c.fetchall(), 1):
    url_short = (r[3] or 'no url')[:70]
    print(f'{i:2}. [{r[2]}] {r[0]}')
    print(f'    @ {r[1]} | {r[4] or "?"} | {r[5]} | {url_short}')

# Count by company for new greenhouse finds
print(f'\n=== NEW GREENHOUSE FINDS BY COMPANY ===')
c.execute("""
    SELECT company, COUNT(*), ROUND(AVG(fit_score),1)
    FROM jobs WHERE source = 'greenhouse' AND status = 'new'
    GROUP BY company ORDER BY COUNT(*) DESC
""")
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} jobs (avg score: {r[2]})')
