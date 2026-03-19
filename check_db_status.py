import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Lever/Greenhouse jobs not yet applied
c.execute("""
    SELECT id, title, company, url, source, status
    FROM jobs
    WHERE status != 'applied'
    AND (url LIKE '%lever%' OR url LIKE '%greenhouse%')
    LIMIT 20
""")
rows = c.fetchall()
print(f'=== Lever/Greenhouse jobs not applied ({len(rows)}) ===')
for r in rows:
    print(f'  [{r[0]}] {r[1]} @ {r[2]} | status={r[5]} | {r[3][:90]}')

# Jobs with fit_score
c.execute("""
    SELECT id, title, company, url, source, fit_score, status
    FROM jobs
    WHERE status != 'applied'
    AND fit_score IS NOT NULL
    AND fit_score >= 60
    ORDER BY fit_score DESC
    LIMIT 20
""")
rows2 = c.fetchall()
print(f'\n=== High fit_score jobs not applied ({len(rows2)}) ===')
for r in rows2:
    print(f'  [{r[0]}] {r[1]} @ {r[2]} | fit={r[5]} | {r[3][:90]}')

# Any jobs with apply-friendly URLs (not arbeitnow)
c.execute("""
    SELECT id, title, company, url, source, status
    FROM jobs
    WHERE status != 'applied'
    AND url NOT LIKE '%arbeitnow%'
    AND url NOT LIKE '%linkedin%'
    AND (url LIKE '%lever%' OR url LIKE '%greenhouse%' OR url LIKE '%indeed%'
         OR url LIKE '%upwork%' OR url LIKE '%workday%' OR url LIKE '%icims%'
         OR url LIKE '%smartrecruiters%' OR url LIKE '%ashbyhq%' OR url LIKE '%bamboohr%'
         OR url LIKE '%myworkday%' OR url LIKE '%jobs.lever%' OR url LIKE '%boards.greenhouse%')
    LIMIT 30
""")
rows3 = c.fetchall()
print(f'\n=== ATS-hosted jobs not applied ({len(rows3)}) ===')
for r in rows3:
    print(f'  [{r[0]}] {r[1]} @ {r[2]} | status={r[5]} | {r[3][:90]}')

# Check the handoff targets
c.execute("SELECT id, title, company, url, status FROM jobs WHERE title LIKE '%LLM%Eval%' OR company LIKE '%LEO%' OR company LIKE '%Allergan%'")
rows4 = c.fetchall()
print(f'\n=== HANDOFF targets ===')
for r in rows4:
    print(f'  [{r[0]}] {r[1]} @ {r[2]} | status={r[4]} | {str(r[3])[:90]}')

conn.close()
