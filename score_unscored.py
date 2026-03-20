"""Quick scoring for unscored jobs based on title/company keyword matching."""
import sys, sqlite3

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# Keywords that boost score (matched against title)
HIGH_MATCH = {
    "ai engineer": 30, "ml engineer": 30, "machine learning engineer": 30,
    "agentic": 35, "llm": 30, "generative ai": 30, "gen ai": 30,
    "ai/ml": 30, "applied ai": 30, "ai platform": 25,
    "automation engineer": 20, "devops": 15, "infrastructure": 15,
    "full stack": 15, "backend": 15, "python": 20,
    "software engineer": 10, "sre": 10, "platform engineer": 15,
    "data engineer": 10, "senior": 5, "staff": 5,
}

# Keywords that reduce score
LOW_MATCH = {
    "manager": -20, "director": -25, "sales": -30, "designer": -25,
    "product manager": -30, "grafikdesigner": -40, "vertrieb": -40,
    "werkstudent": -15, "intern": -20, "junior": -5,
}

# Remote boost
REMOTE_KEYWORDS = {"remote", "anywhere", "distributed"}

def score_job(title, company, location, description):
    title_lower = (title or "").lower()
    loc_lower = (location or "").lower()
    desc_lower = (description or "").lower()

    base = 50  # Start at 50

    for kw, boost in HIGH_MATCH.items():
        if kw in title_lower or kw in desc_lower[:200]:
            base += boost

    for kw, penalty in LOW_MATCH.items():
        if kw in title_lower:
            base += penalty

    # Remote boost
    if any(kw in loc_lower or kw in title_lower for kw in REMOTE_KEYWORDS):
        base += 10

    # Cap at 100
    return max(0, min(100, base))

def main():
    db = sqlite3.connect(DB_PATH)
    unscored = db.execute('''
        SELECT id, title, company, location, description
        FROM jobs WHERE fit_score = 0
    ''').fetchall()

    print(f"Scoring {len(unscored)} unscored jobs...")
    updated = 0
    for jid, title, company, location, desc in unscored:
        score = score_job(title, company, location, desc)
        reason = f"auto-scored: title={title}"
        db.execute('UPDATE jobs SET fit_score = ?, fit_reason = ? WHERE id = ?',
                   (score, reason, jid))
        status = "***" if score >= 85 else "  " if score >= 60 else "  (low)"
        print(f"  {score:3.0f}pts {status} {title[:55]} @ {company}")
        updated += 1

    db.commit()
    print(f"\nScored {updated} jobs")

if __name__ == "__main__":
    main()
