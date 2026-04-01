import sys, sqlite3, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

HIGH_MATCH = {
    'ai engineer': 30, 'ml engineer': 30, 'machine learning engineer': 30,
    'agentic': 35, 'llm': 30, 'generative ai': 30, 'gen ai': 30,
    'ai/ml': 30, 'applied ai': 30, 'ai platform': 25,
    'automation engineer': 20, 'devops': 15, 'infrastructure': 15,
    'full stack': 15, 'backend': 15, 'python': 20,
    'software engineer': 10, 'sre': 10, 'platform engineer': 15,
    'data engineer': 10, 'senior': 5, 'staff': 5,
}
LOW_MATCH = {
    'manager': -20, 'director': -25, 'sales': -30, 'designer': -25,
    'product manager': -30, 'grafikdesigner': -40, 'vertrieb': -40,
    'werkstudent': -15, 'intern': -20, 'junior': -5,
}
REMOTE_KEYWORDS = {'remote', 'anywhere', 'distributed'}

def score_job(title, location, description):
    title_lower = (title or '').lower()
    loc_lower = (location or '').lower()
    desc_lower = (description or '').lower()
    base = 50
    for kw, boost in HIGH_MATCH.items():
        if kw in title_lower or kw in desc_lower[:200]:
            base += boost
    for kw, penalty in LOW_MATCH.items():
        if kw in title_lower:
            base += penalty
    if any(kw in loc_lower or kw in title_lower for kw in REMOTE_KEYWORDS):
        base += 10
    return max(0, min(100, base))

# Use a fresh connection with WAL and busy timeout
db = sqlite3.connect(DB_PATH, timeout=60)
db.execute('PRAGMA journal_mode=WAL')
db.execute('PRAGMA busy_timeout=60000')

unscored = db.execute('SELECT id, title, company, location, description FROM jobs WHERE fit_score = 0 OR fit_score IS NULL').fetchall()
print(f"Found {len(unscored)} unscored jobs")

# Score and update one at a time with immediate commit
scored_high = 0
scored_zero = 0
for jid, title, company, location, desc in unscored:
    score = score_job(title, location, desc)
    # For jobs that score 0, set to 1 so they don't get re-picked
    final_score = max(1, score)
    reason = f"auto-scored:{score}"

    retries = 0
    while retries < 10:
        try:
            db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE id = ?',
                      (final_score, reason, jid))
            db.commit()
            break
        except sqlite3.OperationalError as e:
            retries += 1
            print(f"  retry {retries}: {e}")
            time.sleep(2)

    if score >= 60:
        scored_high += 1
        print(f"  {score:3d} *** {company}: {title[:55]}")

print(f"\nDone. High-score (>=60): {scored_high}, Low-score: {len(unscored) - scored_high}")

# Verify
remaining = db.execute('SELECT COUNT(*) FROM jobs WHERE fit_score = 0 OR fit_score IS NULL').fetchone()[0]
print(f"Remaining unscored: {remaining}")

ready = db.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' GROUP BY source ORDER BY COUNT(*) DESC").fetchall()
print(f"\nReady to apply by source:")
total = 0
for r in ready:
    print(f"  {r[0]}: {r[1]}")
    total += r[1]
print(f"  TOTAL: {total}")
