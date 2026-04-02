import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
print('Total jobs:', conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0])
print('Viable new (>=60):', conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND fit_score >= 60").fetchone()[0])
print('By ATS source:')
for r in conn.execute("SELECT source, COUNT(*) FROM jobs WHERE source IN ('greenhouse','lever','ashby') GROUP BY source").fetchall():
    print(f'  {r[0]}: {r[1]}')
conn.close()
