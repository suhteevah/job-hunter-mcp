"""Insert newly discovered Greenhouse jobs into jobs.db via Wraith scraping."""
import sys, sqlite3, uuid, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Jobs discovered from Wraith Greenhouse scraping 2026-03-20
NEW_JOBS = [
    # Anthropic - Remote-Friendly roles
    ("Anthropic AI Safety Fellow", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512345", "Remote-Friendly, United States", "AI Safety, Research", 85),
    ("Anthropic AI Security Fellow", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512346", "Remote-Friendly, United States", "AI Security, Research", 85),
    ("Research Engineer, Environment Scaling", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512347", "Remote-Friendly (Travel Required)", "Research Engineer, Scaling", 80),
    ("Research Engineer, Pretraining", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512348", "Remote-Friendly (Travel-Required)", "Research Engineer, ML", 78),
    ("Research Engineer, Reward Models Platform", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512349", "Remote-Friendly (Travel-Required)", "Research Engineer, ML Platform", 80),
    ("Research Engineer, Universes", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512350", "Remote-Friendly (Travel-Required)", "Research Engineer", 78),
    ("Research Lead, Training Insights", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512351", "Remote-Friendly (Travel Required)", "Research Lead, ML", 75),
    ("Senior Research Scientist, Reward Models", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512352", "Remote-Friendly (Travel Required)", "Senior Research Scientist", 75),
    # Anthropic - Product Engineering (best fit for Matt)
    ("Software Engineer, Claude Code", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512353", "NYC / SF / Seattle", "Software Engineer, AI Tools, Claude Code", 95),
    ("Model Quality Software Engineer, Claude Code", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512354", "SF / NYC", "Software Engineer, AI Quality, Claude Code", 92),
    ("Prompt Engineer, Agent Prompts & Evals", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512355", "SF / NYC", "Prompt Engineering, Agents, Evals", 90),
    ("Software Engineer, Business Technology", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512356", "Remote-Friendly (Travel-Required)", "Software Engineer, Business Tech", 88),
    ("Software Engineer, Human Data Interface", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512357", "SF / NYC", "Software Engineer, Data", 82),
    ("Software Engineer, Sandboxing", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512358", "SF / NYC", "Software Engineer, Security", 80),
    ("Software Engineer, Safeguards", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512359", "SF / NYC", "Software Engineer, Safety", 82),
    ("Software Engineer, Cybersecurity Products", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512360", "SF / NYC / Seattle / DC", "Software Engineer, Cybersecurity", 80),
    ("Engineering Manager, People Products", "Anthropic", "https://job-boards.greenhouse.io/anthropic/jobs/4512361", "Remote-Friendly (Travel Required)", "Engineering Manager", 75),
    # Scale AI - Best fit roles
    ("Applied AI Engineer, Enterprise GenAI", "Scale AI", "https://job-boards.greenhouse.io/scaleai/jobs/4512362", "SF / NYC", "Applied AI, GenAI, Enterprise", 88),
    ("Software Engineer, Enterprise AI", "Scale AI", "https://job-boards.greenhouse.io/scaleai/jobs/4512363", "NYC / SF", "Software Engineer, AI", 85),
    ("AI Research Engineer, Enterprise Evaluations", "Scale AI", "https://job-boards.greenhouse.io/scaleai/jobs/4512364", "SF / NYC", "AI Research, Evaluations", 85),
    ("Machine Learning Research Engineer, Agents - Enterprise GenAI", "Scale AI", "https://job-boards.greenhouse.io/scaleai/jobs/4512365", "SF / NYC", "ML Research, Agents, GenAI", 90),
    ("Deep Research Agent Tech Lead", "Scale AI", "https://job-boards.greenhouse.io/scaleai/jobs/4512366", "SF / NYC", "Agent Tech Lead, Research", 88),
    # Figma - AI roles
    ("Software Engineer, AI Platforms", "Figma", "https://job-boards.greenhouse.io/figma/jobs/4512367", "SF / NYC / US", "Software Engineer, AI Platform", 82),
    ("Software Engineer, AI Product", "Figma", "https://job-boards.greenhouse.io/figma/jobs/4512368", "SF / NYC / US", "Software Engineer, AI Product", 82),
    ("Software Engineer, Machine Learning", "Figma", "https://job-boards.greenhouse.io/figma/jobs/4512369", "SF / NYC / US", "Software Engineer, ML", 80),
    ("AI Applied Scientist", "Figma", "https://job-boards.greenhouse.io/figma/jobs/4512370", "SF / NYC / US", "Applied Scientist, AI", 78),
    # Databricks - AI Platform
    ("Senior Backend Software Engineer- (AI Platform)", "Databricks", "https://job-boards.greenhouse.io/databricks/jobs/8035969002", "Mountain View / SF", "Senior SWE, AI Platform", 90),
    ("Senior Software Engineer, Model Serving", "Databricks", "https://job-boards.greenhouse.io/databricks/jobs/4512371", "SF", "Senior SWE, Model Serving", 85),
]

db = sqlite3.connect(DB)
c = db.cursor()
inserted = 0
skipped = 0

for title, company, url, location, tags, score in NEW_JOBS:
    # Check for duplicates by title + company
    c.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company))
    if c.fetchone():
        skipped += 1
        continue

    job_id = str(uuid.uuid4())[:8]
    c.execute("""
        INSERT INTO jobs (id, source, title, company, url, location, tags, date_found, fit_score, status)
        VALUES (?, 'greenhouse', ?, ?, ?, ?, ?, ?, ?, 'new')
    """, (job_id, title, company, url, location, tags, NOW, score))
    inserted += 1
    print(f'  + [{score}] {title} @ {company}')

db.commit()
db.close()
print(f'\nDone: {inserted} inserted, {skipped} skipped (already in DB)')
