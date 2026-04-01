import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

c.execute('SELECT COUNT(*) FROM jobs')
print(f'Total: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
print(f'Applied: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM jobs WHERE status='apply_failed'")
print(f'Failed: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM jobs WHERE fit_score IS NULL OR fit_score = 0')
print(f'Unscored: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new'")
print(f'Ready (score>=60 new): {c.fetchone()[0]}')

c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY COUNT(*) DESC")
print('\nBy status:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

c.execute('SELECT source, COUNT(*) FROM jobs WHERE (fit_score IS NULL OR fit_score = 0) GROUP BY source ORDER BY COUNT(*) DESC')
print('\nUnscored by source:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

c.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC")
print('\nReady to apply (score>=60, new) by source:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

c.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC")
print('\nAll jobs by source:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')
