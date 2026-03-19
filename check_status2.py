import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Check fit_score distribution
c.execute("SELECT fit_score, COUNT(*) FROM jobs WHERE status='new' GROUP BY fit_score ORDER BY fit_score DESC LIMIT 20")
print('=== FIT SCORE DISTRIBUTION (new) ===')
for row in c.fetchall():
    print(f'  score={row[0]}: {row[1]} jobs')

# Show top new jobs regardless of score
c.execute("SELECT title, company, fit_score, url, source FROM jobs WHERE status='new' ORDER BY fit_score DESC, rowid DESC LIMIT 20")
print('\n=== TOP 20 NEW JOBS ===')
for row in c.fetchall():
    url = row[3][:100] if row[3] else 'N/A'
    print(f'  [{row[2]}] {row[0]} @ {row[1]} (src:{row[4]})')
    print(f'    {url}')

# Check what URLs look like for new jobs
c.execute("SELECT url FROM jobs WHERE status='new' LIMIT 5")
print('\n=== SAMPLE NEW JOB URLs ===')
for row in c.fetchall():
    print(f'  {row[0]}')

conn.close()
