import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db_path = os.path.expanduser('~/.job-hunter-mcp/jobs.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Update LeoTech
c.execute("UPDATE jobs SET status='applied', notes='Lever apply 2026-03-18. Full form + resume + 5 bullet points.' WHERE url LIKE '%LEOTechnologies%' OR title LIKE '%LeoTech%'")
print(f'LeoTech: {c.rowcount} rows updated')

conn.commit()

# Show status counts
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
print('\n=== STATUS COUNTS ===')
for r in c.fetchall():
    print(f'  {(r[0] or "new"):10s}: {r[1]}')

conn.close()
