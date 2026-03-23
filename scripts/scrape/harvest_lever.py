"""Harvest jobs from Lever API for companies that use Lever."""
import sys, sqlite3, uuid, datetime, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Lever API: https://api.lever.co/v0/postings/{company}?mode=json
LEVER_COMPANIES = {
    'cloudflare': 'Cloudflare',
    'twitch': 'Twitch',
    'netlify': 'Netlify',
    'figma': 'Figma',
    'ramp': 'Ramp',
    'notion': 'Notion',
    'rippling': 'Rippling',
    'plaid': 'Plaid',
    'retool': 'Retool',
    'vercel': 'Vercel',
    'resend': 'Resend',
    'convex': 'Convex',
    'deno': 'Deno',
    'val-town': 'Val Town',
    'fly-io': 'Fly.io',
    'neon-inc': 'Neon',
    'upstash': 'Upstash',
    'singlestore': 'SingleStore',
    'cockroach-labs': 'Cockroach Labs',
    'weights-biases': 'Weights & Biases',
}

US_LOCATIONS = ['remote', 'united states', 'san francisco', 'new york', 'seattle',
                'mountain view', 'california', 'washington', 'arizona',
                'palo alto', 'los angeles', 'austin', 'chicago', 'boston',
                'denver', 'portland', 'us']

POSITIVE_KEYWORDS = [
    'ai engineer', 'ml engineer', 'machine learning', 'llm', 'genai',
    'ai platform', 'ai infrastructure', 'agent', 'agentic', 'automation',
    'software engineer', 'backend engineer', 'full stack', 'fullstack',
    'python', 'rust', 'typescript', 'devops', 'sre', 'infrastructure',
    'platform engineer', 'mcp', 'prompt engineer', 'qa automation',
    'test automation', 'sdet', 'data engineer', 'api', 'developer tools', 'sdk',
]

def score_job(title, location):
    title_lower = title.lower()
    loc_lower = (location or '').lower()
    is_us = any(loc in loc_lower for loc in US_LOCATIONS)
    if not is_us and loc_lower:
        return 0
    score = 50
    for kw in POSITIVE_KEYWORDS:
        if kw in title_lower:
            score += 8
    neg = ['intern', 'director', 'vp ', 'vice president', 'chief', 'head of',
           'counsel', 'accountant', 'recruiter', 'sales', 'account executive',
           'marketing', 'communications', 'designer', 'product design']
    for kw in neg:
        if kw in title_lower:
            score -= 30
    if 'remote' in loc_lower:
        score += 10
    if 'senior' in title_lower or 'staff' in title_lower:
        score += 5
    return min(100, max(0, score))

def fetch_lever(slug, company):
    url = 'https://api.lever.co/v0/postings/{}?mode=json'.format(slug)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            jobs = json.loads(resp.read().decode('utf-8'))
            print('  {}: {} jobs'.format(company, len(jobs)))
            return jobs
    except Exception as e:
        print('  {}: FAILED - {}'.format(company, str(e)[:60]))
        return []

def main():
    db = sqlite3.connect(DB)
    c = db.cursor()
    inserted = 0
    skipped = 0
    filtered = 0

    for slug, company in LEVER_COMPANIES.items():
        jobs = fetch_lever(slug, company)
        for job in jobs:
            title = job.get('text', '')
            job_id = job.get('id', '')
            location = ''
            cats = job.get('categories', {})
            if isinstance(cats, dict):
                location = cats.get('location', '')
            abs_url = job.get('hostedUrl', job.get('applyUrl', ''))

            score = score_job(title, location)
            if score < 55:
                filtered += 1
                continue
            c.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company))
            if c.fetchone():
                skipped += 1
                continue
            uid = str(uuid.uuid4())[:8]
            c.execute("""INSERT INTO jobs (id, source, source_id, title, company, url, location,
                          date_found, fit_score, status)
                          VALUES (?, 'lever', ?, ?, ?, ?, ?, ?, ?, 'new')""",
                      (uid, str(job_id), title, company, abs_url, location, NOW, score))
            inserted += 1
            if score >= 70:
                print('  + [{}] {} @ {} ({})'.format(score, title, company, location))

    db.commit()
    db.close()
    print('\n=== LEVER HARVEST ===')
    print('Inserted: {}'.format(inserted))
    print('Skipped: {}'.format(skipped))
    print('Filtered: {}'.format(filtered))

if __name__ == '__main__':
    main()
