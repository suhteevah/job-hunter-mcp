import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute('SELECT COUNT(*) FROM jobs')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
applied = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM jobs WHERE status != 'applied' AND fit_score >= 60")
viable = c.fetchone()[0]
print(f'Total: {total}, Applied: {applied}, Viable (score>=60, not applied): {viable}')

# Show top jobs with their apply URLs - need direct apply links
c.execute("""
    SELECT fit_score, title, company, url, source, status
    FROM jobs
    WHERE status != 'applied' AND fit_score >= 60
    ORDER BY fit_score DESC LIMIT 20
""")
print("\nTOP UNAPPLIED JOBS:")
for r in c.fetchall():
    print(f"  {r[0]:5.0f} | {(r[1] or '')[:55]:55s} | {(r[2] or '')[:20]:20s} | {(r[4] or '')[:15]} | {r[3]}")
db.close()
