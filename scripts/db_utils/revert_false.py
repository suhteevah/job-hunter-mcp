import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()
c.execute("UPDATE jobs SET status='new' WHERE status='applied' AND notes LIKE '%manual follow-up%'")
print(f'Reverted {c.rowcount} false applied marks')
conn.commit()
c.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')
conn.close()
