"""
Harvest jobs from Greenhouse API for top AI companies.
Filter for engineering/AI roles, score them, insert into jobs.db.
"""
import sys, sqlite3, uuid, datetime, json, urllib.request, urllib.error, re, html
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Companies with Greenhouse boards
COMPANIES = {
    'anthropic': 'Anthropic',
    'scaleai': 'Scale AI',
    'figma': 'Figma',
    'databricks': 'Databricks',
    'reddit': 'Reddit',
    'twilio': 'Twilio',
    'stripe': 'Stripe',
    'discord': 'Discord',
    'gitlab': 'GitLab',
    'gusto': 'Gusto',
    'cloudflare': 'Cloudflare',
    'elastic': 'Elastic',
    'hashicorp': 'HashiCorp',
    'cockroachlabs': 'Cockroach Labs',
    'samsara': 'Samsara',
    'pagerduty': 'PagerDuty',
    'datadog': 'Datadog',
    'brex': 'Brex',
}

# Keywords that indicate a good fit for Matt
POSITIVE_KEYWORDS = [
    'ai engineer', 'ml engineer', 'machine learning', 'llm', 'genai', 'gen ai',
    'ai platform', 'ai infrastructure', 'agent', 'agentic', 'automation',
    'software engineer', 'backend engineer', 'full stack', 'fullstack',
    'python', 'rust', 'typescript', 'devops', 'sre', 'infrastructure',
    'platform engineer', 'mcp', 'model context', 'prompt engineer',
    'qa automation', 'test automation', 'sdet', 'quality engineer',
    'data engineer', 'api', 'developer tools', 'dev tools', 'sdk',
    'claude', 'chatbot', 'nlp', 'natural language',
]

# Keywords that indicate NOT a good fit
NEGATIVE_KEYWORDS = [
    'intern', 'internship', 'new grad', 'phd required', 'director',
    'vp ', 'vice president', 'chief', 'head of', 'counsel', 'lawyer',
    'accountant', 'accounting', 'finance ', 'recruiter', 'recruiting',
    'sales', 'account executive', 'marketing', 'communications',
    'design ', 'product design', 'graphic', 'ux research',
    'policy', 'government', 'legal', 'tax ', 'payroll',
    'london', 'dublin', 'berlin', 'tokyo', 'india', 'singapore',
    'australia', 'korea', 'brazil', 'mexico', 'argentina', 'uruguay',
    'switzerland', 'denmark', 'netherlands', 'germany', 'uk',
    'canada', ', uk', ', ch', ', ie',
]

# US locations we'd consider
US_LOCATIONS = ['remote', 'united states', 'san francisco', 'new york', 'seattle',
                'mountain view', 'california', 'washington', 'arizona', 'phoenix',
                'chico', 'palo alto', 'menlo park']


def score_job(title, location, content_text=''):
    """Score a job 0-100 based on fit for Matt."""
    title_lower = title.lower()
    loc_lower = (location or '').lower()
    content_lower = content_text.lower()

    # Must be US-based or remote
    is_us = any(loc in loc_lower for loc in US_LOCATIONS)
    if not is_us and loc_lower:
        return 0  # Skip non-US roles

    score = 50  # Base score

    # Title-based scoring
    for kw in POSITIVE_KEYWORDS:
        if kw in title_lower:
            score += 8
    for kw in NEGATIVE_KEYWORDS[:12]:  # Role-type negatives
        if kw in title_lower:
            score -= 30

    # Content-based scoring
    for kw in ['mcp', 'model context protocol', 'agent', 'agentic', 'llm',
               'browser automation', 'automation', 'python', 'rust',
               'typescript', 'api', 'sdk']:
        if kw in content_lower:
            score += 3

    # Remote bonus
    if 'remote' in loc_lower:
        score += 10

    # Senior/Staff title bonus
    if 'senior' in title_lower or 'staff' in title_lower or 'sr.' in title_lower:
        score += 5

    return min(100, max(0, score))


def strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]  # First 500 chars for scoring


def fetch_greenhouse_jobs(slug, company_name):
    """Fetch all jobs from Greenhouse API for a company."""
    url = f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            jobs = data.get('jobs', [])
            print(f'  {company_name}: {len(jobs)} total jobs found')
            return jobs
    except Exception as e:
        print(f'  {company_name}: FAILED - {e}')
        return []


def main():
    db = sqlite3.connect(DB)
    c = db.cursor()
    total_inserted = 0
    total_skipped = 0
    total_filtered = 0

    for slug, company_name in COMPANIES.items():
        print(f'\n--- {company_name} ({slug}) ---')
        jobs = fetch_greenhouse_jobs(slug, company_name)

        for job in jobs:
            title = job.get('title', '')
            job_id = job.get('id', '')
            abs_url = job.get('absolute_url', '')
            location = job.get('location', {}).get('name', '') if isinstance(job.get('location'), dict) else ''

            # Quick content extract for scoring
            content_text = strip_html(job.get('content', '')) if 'content' in job else ''

            # Score the job
            score = score_job(title, location, content_text)

            if score < 55:
                total_filtered += 1
                continue

            # Check for duplicates
            c.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company_name))
            if c.fetchone():
                total_skipped += 1
                continue

            # Also check by URL
            if abs_url:
                c.execute("SELECT id FROM jobs WHERE url = ?", (abs_url,))
                if c.fetchone():
                    total_skipped += 1
                    continue

            # Insert
            uid = str(uuid.uuid4())[:8]
            c.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location,
                                  date_found, fit_score, status, description)
                VALUES (?, 'greenhouse', ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """, (uid, str(job_id), title, company_name, abs_url, location,
                  NOW, score, content_text[:2000] if content_text else None))
            total_inserted += 1
            print(f'  + [{score}] {title} @ {company_name} ({location})')

    db.commit()
    db.close()

    print(f'\n=== HARVEST COMPLETE ===')
    print(f'Inserted: {total_inserted}')
    print(f'Skipped (duplicate): {total_skipped}')
    print(f'Filtered (low score): {total_filtered}')


if __name__ == '__main__':
    main()
