"""Harvest jobs from Ashby API for AI-native companies."""
import sys, sqlite3, uuid, datetime, json, urllib.request, re, html
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

ASHBY_COMPANIES = {
    'perplexity': 'Perplexity AI',
    'elevenlabs': 'ElevenLabs',
    'together-ai': 'Together AI',
    'anyscale': 'Anyscale',
    'fireworks-ai': 'Fireworks AI',
    'langchain': 'LangChain',
    'pinecone': 'Pinecone',
    'weaviate': 'Weaviate',
    'replit': 'Replit',
    'linear': 'Linear',
    'supabase': 'Supabase',
    'deepgram': 'Deepgram',
    'runway': 'Runway',
    'stability-ai': 'Stability AI',
    'modal-labs': 'Modal',
    'sourcegraph': 'Sourcegraph',
    'dbt-labs': 'dbt Labs',
    'huggingface': 'Hugging Face',
    'cursor': 'Cursor',
    'codeium': 'Codeium',
    'tabnine': 'Tabnine',
    'cohere': 'Cohere',
    'mistral': 'Mistral AI',
    'groq': 'Groq',
    'cerebras': 'Cerebras',
    'mem': 'Mem',
    'dust-tt': 'Dust',
    'glean': 'Glean',
    'hebbia': 'Hebbia',
    'harvey': 'Harvey AI',
}

US_LOCATIONS = ['remote', 'united states', 'san francisco', 'new york', 'seattle',
                'mountain view', 'california', 'washington', 'arizona', 'us',
                'palo alto', 'menlo park', 'los angeles', 'austin', 'chicago',
                'boston', 'denver', 'portland', 'anywhere']

POSITIVE_KEYWORDS = [
    'ai engineer', 'ml engineer', 'machine learning', 'llm', 'genai', 'gen ai',
    'ai platform', 'ai infrastructure', 'agent', 'agentic', 'automation',
    'software engineer', 'backend engineer', 'full stack', 'fullstack',
    'python', 'rust', 'typescript', 'devops', 'sre', 'infrastructure',
    'platform engineer', 'mcp', 'model context', 'prompt engineer',
    'qa automation', 'test automation', 'sdet', 'quality engineer',
    'data engineer', 'api', 'developer tools', 'dev tools', 'sdk',
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

def fetch_ashby(slug, company):
    url = 'https://api.ashbyhq.com/posting-api/job-board/{}'.format(slug)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            jobs = data.get('jobs', [])
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

    for slug, company in ASHBY_COMPANIES.items():
        jobs = fetch_ashby(slug, company)
        for job in jobs:
            title = job.get('title', '')
            job_id = job.get('id', '')
            location = job.get('location', '')
            if isinstance(location, dict):
                location = location.get('name', '')
            # Build Ashby apply URL
            abs_url = 'https://jobs.ashbyhq.com/{}/{}'.format(slug, job_id)

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
                          VALUES (?, 'ashby', ?, ?, ?, ?, ?, ?, ?, 'new')""",
                      (uid, str(job_id), title, company, abs_url, location, NOW, score))
            inserted += 1
            if score >= 70:
                print('  + [{}] {} @ {} ({})'.format(score, title, company, location))

    db.commit()
    db.close()
    print('\n=== ASHBY HARVEST ===')
    print('Inserted: {}'.format(inserted))
    print('Skipped: {}'.format(skipped))
    print('Filtered: {}'.format(filtered))

if __name__ == '__main__':
    main()
