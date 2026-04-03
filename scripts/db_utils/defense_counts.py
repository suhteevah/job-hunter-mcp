import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()
for src in ['boeing', 'l3harris', 'lockheed', 'mitre', 'honeywell']:
    c.execute('SELECT COUNT(*) FROM jobs WHERE source=?', (src,))
    print(f'{src}: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM jobs')
print(f'Total DB: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
print(f'Applied: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new'")
print(f'Ready to apply (>=60): {c.fetchone()[0]}')
