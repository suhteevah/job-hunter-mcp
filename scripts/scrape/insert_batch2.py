import sqlite3, os, sys, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
now = datetime.now().isoformat()

jobs = [
    ('Cloud Infrastructure Engineer', 'Farsight AI'),
    ('Staff Software Engineer Backend', 'Sleeper'),
    ('Sr Full-Stack Engineer (Remote)', 'Open Energy Transition'),
    ('Sr Full Stack Engineer Engagement', 'Rocket Money'),
    ('SWE Agentic (Remote/Contract)', 'Verve/Jun Group'),
    ('Software Engineer Full-Stack', 'Runpod'),
    ('Engineering Manager (Remote US)', 'Openly'),
    ('Sr SRE/DevOps Engineer', 'BRINC'),
    ('Site Reliability Engineer', 'Anagram'),
    ('SWE SRE/DevOps', 'Voxel'),
    ('Full-Stack Engineer (Remote)', 'Tempo'),
    ('Software Engineer Growth', 'Render'),
]

count = 0
for title, company in jobs:
    jid = str(uuid.uuid4())[:16]
    try:
        c.execute("""INSERT INTO jobs (id, title, company, url, source, fit_score, status, notes, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (jid, title, company, 'wraith-discovered', 'wraith+playwright', 80, 'applied', 'Applied 2026-03-18', now))
        count += 1
    except: pass

db.commit()
print(f'Inserted {count} more jobs')
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
print(f'Total applied: {c.fetchone()[0]}')
db.close()
