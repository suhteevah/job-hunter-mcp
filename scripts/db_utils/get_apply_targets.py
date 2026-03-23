"""Get top Greenhouse apply targets with direct apply URLs."""
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

# Pure Greenhouse URLs (job-boards.greenhouse.io) - can apply via Playwright
print('=== PURE GREENHOUSE TARGETS (Playwright-ready) ===')
c.execute("""
    SELECT title, company, fit_score, url, source_id
    FROM jobs
    WHERE status != 'applied'
    AND fit_score >= 60
    AND url LIKE '%greenhouse.io%'
    ORDER BY fit_score DESC LIMIT 30
""")
for i, r in enumerate(c.fetchall(), 1):
    print(f'{i:2}. [{r[2]}] {r[0]} @ {r[1]}')
    print(f'    URL: {r[3]}')
    print(f'    ID: {r[4]}')

# Custom portal targets (need Chrome)
print('\n=== CUSTOM PORTAL TARGETS (need Chrome) ===')
c.execute("""
    SELECT title, company, fit_score, url
    FROM jobs
    WHERE status != 'applied'
    AND fit_score >= 80
    AND source = 'greenhouse'
    AND url NOT LIKE '%greenhouse.io%'
    ORDER BY fit_score DESC LIMIT 15
""")
for i, r in enumerate(c.fetchall(), 1):
    print(f'{i:2}. [{r[2]}] {r[0]} @ {r[1]}')
    print(f'    URL: {r[3]}')

# Non-greenhouse high-value targets
print('\n=== NON-GREENHOUSE HIGH-VALUE (JSearch/other) ===')
c.execute("""
    SELECT title, company, fit_score, url
    FROM jobs
    WHERE status != 'applied'
    AND fit_score >= 90
    AND source != 'greenhouse'
    ORDER BY fit_score DESC LIMIT 15
""")
for i, r in enumerate(c.fetchall(), 1):
    print(f'{i:2}. [{r[2]}] {r[0]} @ {r[1]}')
    print(f'    URL: {r[3][:80]}')
