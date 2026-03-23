import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()

# Add OpenAI job to DB and mark applied (it was found via wraith search, not in DB yet)
c.execute("""INSERT OR IGNORE INTO jobs (id, title, company, url, source, status, fit_score, notes)
    VALUES ('openai-ai-success-eng', 'AI Success Engineer - US Remote', 'OpenAI',
    'https://jobs.ashbyhq.com/openai/ea339283-7650-4b50-9d24-08d143af260a',
    'wraith-search', 'applied', 95, 'Ashby apply 2026-03-18. Found via wraith search.')""")
print(f'OpenAI insert: {c.rowcount}')
db.commit()

c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
print('\nSTATUS COUNTS:')
for r in c.fetchall():
    print(f'  {(r[0] or "new"):10s}: {r[1]}')
db.close()
