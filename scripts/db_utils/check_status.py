import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Counts
c.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
print('=== STATUS COUNTS ===')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Recent applied
c.execute("SELECT title, company, url FROM jobs WHERE status='applied' ORDER BY rowid DESC LIMIT 5")
print('\n=== RECENT APPLICATIONS ===')
for row in c.fetchall():
    print(f'  {row[0]} @ {row[1]}')
    print(f'    {row[2][:120] if row[2] else "N/A"}')

# Top unapplied
c.execute("SELECT title, company, fit_score, url FROM jobs WHERE status='new' AND fit_score >= 60 ORDER BY fit_score DESC LIMIT 15")
print('\n=== TOP UNAPPLIED (fit_score>=60) ===')
for row in c.fetchall():
    print(f'  [{row[2]}] {row[0]} @ {row[1]}')
    print(f'    {row[3][:150] if row[3] else "N/A"}')

# Lever
c.execute("SELECT title, company, fit_score, url FROM jobs WHERE status='new' AND url LIKE '%lever%' ORDER BY fit_score DESC LIMIT 5")
print('\n=== LEVER (priority) ===')
for row in c.fetchall():
    print(f'  [{row[2]}] {row[0]} @ {row[1]} -> {row[3]}')

# Greenhouse
c.execute("SELECT title, company, fit_score, url FROM jobs WHERE status='new' AND url LIKE '%greenhouse%' ORDER BY fit_score DESC LIMIT 5")
print('\n=== GREENHOUSE (priority) ===')
for row in c.fetchall():
    print(f'  [{row[2]}] {row[0]} @ {row[1]} -> {row[3]}')

# Total new with URLs that aren't batch markers
c.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND url NOT LIKE 'batch%' AND url IS NOT NULL AND url != ''")
print(f'\n=== NEW JOBS WITH REAL URLs: {c.fetchone()[0]} ===')

conn.close()
