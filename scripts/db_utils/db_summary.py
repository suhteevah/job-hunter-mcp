import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM jobs')
print('Total jobs:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
print('Applied:', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'applied' AND fit_score >= 60")
print('Viable unapplied (60+):', c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'applied' AND fit_score >= 75")
print('High-value unapplied (75+):', c.fetchone()[0])
print('\nBy source:')
c.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC")
for r in c.fetchall():
    print('  {}: {}'.format(r[0], r[1]))
print('\nTop 10 high-value unapplied:')
c.execute("""SELECT title, company, fit_score, location FROM jobs
             WHERE status != 'applied' AND fit_score >= 75
             ORDER BY fit_score DESC LIMIT 10""")
for r in c.fetchall():
    print('  [{}] {} @ {} ({})'.format(r[2], r[0], r[1], r[3] or '?'))
