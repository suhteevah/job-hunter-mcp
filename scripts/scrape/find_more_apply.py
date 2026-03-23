import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()

# Find jobs with direct-apply platforms (not aggregators)
c.execute("""SELECT fit_score, title, company, url FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    AND (url LIKE '%ashby%' OR url LIKE '%lever%' OR url LIKE '%greenhouse%'
         OR url LIKE '%workable%' OR url LIKE '%bamboohr%' OR url LIKE '%smartrecruiters%'
         OR url LIKE '%recruitee%' OR url LIKE '%breezy%' OR url LIKE '%apply%')
    AND url NOT LIKE '%flexionis%'
    ORDER BY fit_score DESC LIMIT 15""")
rows = c.fetchall()
print(f'DIRECT ATS JOBS ({len(rows)} found):')
for r in rows:
    print(f'  {r[0]:5.0f} | {(r[1] or "")[:55]:55s} | {(r[2] or "")[:20]} | {r[3][:100]}')

# Also find jobs with company career page URLs
print()
c.execute("""SELECT fit_score, title, company, url FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    AND url NOT LIKE '%flexionis%' AND url NOT LIKE '%arbeitnow%'
    AND url NOT LIKE '%indeed%' AND url NOT LIKE '%dice.com%'
    AND url NOT LIKE '%linkedin%' AND url NOT LIKE '%snagajob%'
    AND url NOT LIKE '%remote.co%' AND url NOT LIKE '%dailyremote%'
    AND url NOT LIKE '%remoterocketship%' AND url NOT LIKE '%jobright%'
    AND url NOT LIKE '%jobleads%' AND url NOT LIKE '%hiredock%'
    AND url NOT LIKE '%jobgether%' AND url NOT LIKE '%solana%'
    ORDER BY fit_score DESC LIMIT 10""")
rows2 = c.fetchall()
print(f'OTHER DIRECT JOBS ({len(rows2)} found):')
for r in rows2:
    print(f'  {r[0]:5.0f} | {(r[1] or "")[:55]:55s} | {(r[2] or "")[:20]} | {r[3][:100]}')

db.close()
