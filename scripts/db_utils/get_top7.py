import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Top 7 unapplied jobs, prefer Lever/Greenhouse, then others
c.execute("""
    SELECT id, title, company, url, source, fit_score
    FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    ORDER BY
        CASE
            WHEN url LIKE '%lever.co%' THEN 0
            WHEN url LIKE '%greenhouse%' THEN 1
            WHEN url LIKE '%ashbyhq%' THEN 2
            WHEN url LIKE '%indeed.com%' THEN 3
            ELSE 4
        END,
        fit_score DESC
    LIMIT 7
""")

rows = c.fetchall()
for r in rows:
    id, title, company, url, source, score = r
    print(f"ID:{id} | Score:{score} | {company} | {title[:60]}")
    print(f"  URL: {url}")
    print()

conn.close()
