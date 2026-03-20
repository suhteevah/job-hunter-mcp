"""Wave 2: Harvest more Greenhouse + Lever companies via API."""
import sys, sqlite3, uuid, datetime, json, urllib.request, re, html
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Wave 2 companies - AI-heavy, remote-friendly
GREENHOUSE_COMPANIES = {
    'palantir': 'Palantir',
    'aurora': 'Aurora',
    'nuro': 'Nuro',
    'cruise': 'Cruise',
    'ziprecruiter': 'ZipRecruiter',
    'weaviate': 'Weaviate',
    'pinecone': 'Pinecone',
    'langchain': 'LangChain',
    'perplexityai': 'Perplexity AI',
    'replit': 'Replit',
    'vercel': 'Vercel',
    'sourcegraph': 'Sourcegraph',
    'snyk': 'Snyk',
    'linear': 'Linear',
    'dbt-labs': 'dbt Labs',
    'supabase': 'Supabase',
    'temporal': 'Temporal',
    'clickhouse': 'ClickHouse',
    'fly': 'Fly.io',
    'planetscale': 'PlanetScale',
    'render': 'Render',
    'railway': 'Railway',
    'doppler': 'Doppler',
    'airbyte': 'Airbyte',
    'deepgram': 'Deepgram',
    'assemblyai': 'AssemblyAI',
    'elevenlabs': 'ElevenLabs',
    'runway': 'Runway',
    'midjourney': 'Midjourney',
    'stability': 'Stability AI',
    'together': 'Together AI',
    'fireworks': 'Fireworks AI',
    'modal': 'Modal',
    'anyscale': 'Anyscale',
    'weights-and-biases': 'Weights & Biases',
    'huggingface': 'Hugging Face',
    'deepmind': 'DeepMind',
}

US_LOCATIONS = ['remote', 'united states', 'san francisco', 'new york', 'seattle',
                'mountain view', 'california', 'washington', 'arizona', 'phoenix',
                'chico', 'palo alto', 'menlo park', 'los angeles', 'austin',
                'chicago', 'boston', 'denver', 'portland', 'us']

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

def score_job(title, location, content_text=''):
    title_lower = title.lower()
    loc_lower = (location or '').lower()
    content_lower = content_text.lower()
    is_us = any(loc in loc_lower for loc in US_LOCATIONS)
    if not is_us and loc_lower:
        return 0
    score = 50
    for kw in POSITIVE_KEYWORDS:
        if kw in title_lower:
            score += 8
    neg_title = ['intern', 'director', 'vp ', 'vice president', 'chief',
                 'head of', 'counsel', 'accountant', 'recruiter', 'sales',
                 'account executive', 'marketing', 'communications']
    for kw in neg_title:
        if kw in title_lower:
            score -= 30
    for kw in ['mcp', 'model context protocol', 'agent', 'agentic', 'llm',
               'browser automation', 'automation', 'python', 'rust', 'typescript', 'api', 'sdk']:
        if kw in content_lower:
            score += 3
    if 'remote' in loc_lower:
        score += 10
    if 'senior' in title_lower or 'staff' in title_lower or 'sr.' in title_lower:
        score += 5
    return min(100, max(0, score))

def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()[:500]

def fetch_greenhouse(slug, company):
    url = 'https://boards-api.greenhouse.io/v1/boards/{}/jobs'.format(slug)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
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

    for slug, company in GREENHOUSE_COMPANIES.items():
        jobs = fetch_greenhouse(slug, company)
        for job in jobs:
            title = job.get('title', '')
            job_id = job.get('id', '')
            abs_url = job.get('absolute_url', '')
            loc = job.get('location', {})
            location = loc.get('name', '') if isinstance(loc, dict) else ''
            content = strip_html(job.get('content', '')) if 'content' in job else ''
            score = score_job(title, location, content)
            if score < 55:
                filtered += 1
                continue
            c.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company))
            if c.fetchone():
                skipped += 1
                continue
            if abs_url:
                c.execute("SELECT id FROM jobs WHERE url = ?", (abs_url,))
                if c.fetchone():
                    skipped += 1
                    continue
            uid = str(uuid.uuid4())[:8]
            c.execute("""INSERT INTO jobs (id, source, source_id, title, company, url, location,
                          date_found, fit_score, status, description)
                          VALUES (?, 'greenhouse', ?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
                      (uid, str(job_id), title, company, abs_url, location, NOW, score,
                       content[:2000] if content else None))
            inserted += 1
            if score >= 70:
                print('  + [{}] {} @ {} ({})'.format(score, title, company, location))

    db.commit()
    db.close()
    print('\n=== WAVE 2 HARVEST ===')
    print('Inserted: {}'.format(inserted))
    print('Skipped: {}'.format(skipped))
    print('Filtered: {}'.format(filtered))

if __name__ == '__main__':
    main()
