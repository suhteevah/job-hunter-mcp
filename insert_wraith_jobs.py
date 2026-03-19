import sqlite3, os, sys, uuid
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
now = datetime.now().isoformat()

jobs = [
    ('Tempo Full-Stack Engineer (Remote)', 'Tempo', 'https://jobs.ashbyhq.com/Tempo/374cb123'),
    ('Software Engineer Growth', 'Render', 'https://jobs.ashbyhq.com/render/62ea10c7'),
    ('SWE Agentic (Remote/Contract)', 'Verve/Jun Group', 'https://job-boards.greenhouse.io/jungroup/jobs/8409411002'),
    ('Software Engineer Full-Stack', 'Runpod', 'https://job-boards.greenhouse.io/runpod/jobs/4785681008'),
    ('Engineering Manager (Remote US)', 'Openly', 'https://job-boards.greenhouse.io/openly/jobs/4661473005'),
    ('Sr SRE/DevOps Engineer', 'BRINC', 'https://jobs.ashbyhq.com/brinc/2a5785f0'),
    ('Site Reliability Engineer', 'Anagram', 'https://jobs.ashbyhq.com/Anagram/72bc0471'),
    ('SWE SRE/DevOps', 'Voxel', 'https://jobs.ashbyhq.com/Voxel/ac78aadf'),
    ('Sr Full-Stack Engineer (Remote)', 'Open Energy Transition', 'https://job-boards.greenhouse.io/openenergytransition/jobs/4769628101'),
    ('Sr Full Stack Engineer Engagement', 'Rocket Money', 'https://job-boards.greenhouse.io/truebill/jobs/7668385003'),
    ('Sr/Staff SRE', 'Oscilar', 'https://jobs.ashbyhq.com/oscilar/41bf0f36'),
    ('U.S. Senior DevOps Engineer', 'Jump', 'https://jobs.ashbyhq.com/jump-app/b53f05ce'),
    ('Sr SWE Applied AI (Remote)', 'TLDR', 'https://jobs.ashbyhq.com/tldr.tech/3b21aaf8'),
    ('Full Stack AI Engineer (Remote)', 'Infinity', 'https://jobs.ashbyhq.com/infinity-constellation/30fac65e'),
]

count = 0
for title, company, url in jobs:
    jid = str(uuid.uuid4())[:16]
    try:
        c.execute("""INSERT INTO jobs (id, title, company, url, source, fit_score, status, notes, date_found)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (jid, title, company, url, 'wraith-search', 80, 'applied', 'Applied 2026-03-18', now))
        count += 1
    except Exception as e:
        pass

db.commit()
print(f'Inserted {count} new jobs')
c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
print(f'Total applied: {c.fetchone()[0]}')
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
for r in c.fetchall():
    print(f'  {(r[0] or "new"):10s}: {r[1]}')
db.close()
