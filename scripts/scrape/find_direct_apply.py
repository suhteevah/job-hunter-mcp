import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()

# Find jobs with direct-apply URLs
c.execute("""SELECT fit_score, title, company, url, source FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    AND (url LIKE '%lever%' OR url LIKE '%greenhouse%' OR url LIKE '%upwork.com%'
         OR url LIKE '%indeed.com%' OR url LIKE '%dice.com%')
    ORDER BY fit_score DESC""")
rows = c.fetchall()
print(f'DIRECT-APPLY JOBS ({len(rows)} found):')
for r in rows:
    print(f'  {r[0]:5.0f} | {(r[1] or "")[:55]:55s} | {(r[2] or "")[:20]} | {r[3][:100]}')

print()
# Find non-flexionis jobs (flexionis is pure aggregator, skip)
c.execute("""SELECT fit_score, title, company, url, source FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    AND url NOT LIKE '%flexionis%' AND url NOT LIKE '%arbeitnow%'
    ORDER BY fit_score DESC LIMIT 20""")
rows2 = c.fetchall()
print(f'NON-AGGREGATOR JOBS ({len(rows2)} found):')
for r in rows2:
    print(f'  {r[0]:5.0f} | {(r[1] or "")[:55]:55s} | {(r[2] or "")[:20]} | {r[3][:100]}')

db.close()
