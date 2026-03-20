import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
rows = conn.execute("""
    SELECT id, company, title, fit_score, url, source
    FROM jobs
    WHERE status NOT IN ('applied', 'rejected', 'expired')
    AND fit_score >= 60
    AND (url LIKE '%greenhouse%' OR url LIKE '%lever%')
    ORDER BY fit_score DESC
    LIMIT 30
""").fetchall()
print(f"{'ID':>8} | {'Source':12s} | {'Score':>5} | {'Company':30s} | {'Title':50s} | URL")
print("-" * 180)
for r in rows:
    print(f"{r[0]:>8} | {r[5]:12s} | {r[3]:>5.0f} | {r[1][:30]:30s} | {r[2][:50]:50s} | {r[4][:80]}")
print(f"\nTotal: {len(rows)} targets")
conn.close()
