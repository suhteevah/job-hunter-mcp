import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()
c.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
print('=== STATUS COUNTS ===')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')
c.execute("SELECT title, company, fit_score, url FROM jobs WHERE status='new' AND fit_score >= 50 ORDER BY fit_score DESC LIMIT 20")
print('\n=== TOP NEW JOBS (score>=50) ===')
for row in c.fetchall():
    print(f'  [{row[2]}] {row[0]} @ {row[1]}')
    print(f'    {row[3][:120] if row[3] else "N/A"}')
conn.close()
