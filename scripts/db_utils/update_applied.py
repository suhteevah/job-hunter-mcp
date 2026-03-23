import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()
job_id = sys.argv[1]
c.execute("UPDATE jobs SET status='applied', applied_date='2026-03-18' WHERE id=?", (job_id,))
print(f'Updated {c.rowcount} rows for job {job_id}')
conn.commit()
conn.close()
