import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
conn = sqlite3.connect('C:/Users/Matt/.job-hunter-mcp/jobs.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM jobs")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE source='indeed' AND status='new'")
indeed_new = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE source='indeed'")
indeed_total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new'")
viable = c.fetchone()[0]
print(f"Total jobs in DB: {total}")
print(f"Indeed jobs (all): {indeed_total}")
print(f"Indeed new status: {indeed_new}")
print(f"Viable new (score>=60): {viable}")
conn.close()
