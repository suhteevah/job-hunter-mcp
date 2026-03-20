"""Expanded Greenhouse + Ashby harvest - new companies not in existing harvesters."""
import sys, sqlite3, uuid, datetime, json, urllib.request, re, html
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# New Greenhouse companies NOT already in wraith_greenhouse_harvest.py
GREENHOUSE_NEW = {
    'airtable': 'Airtable',
    'notion': 'Notion',
    'vercel': 'Vercel',
    'netlify': 'Netlify',
    'snyk': 'Snyk',
    'grafana-labs': 'Grafana Labs',
    'mongodb': 'MongoDB',
    'confluent': 'Confluent',
    'planetscale': 'PlanetScale',
    'supabase': 'Supabase',
    'neon': 'Neon',
    'temporal-technologies': 'Temporal',
    'prefect': 'Prefect',
    'duckdb': 'DuckDB',
    'clickhouse': 'ClickHouse',
    'timescale': 'Timescale',
    'materialize': 'Materialize',
    'oxla': 'Oxla',
    'airbyte': 'Airbyte',
    'mux': 'Mux',
    'resend': 'Resend',
    'fly-io': 'Fly.io',
    'retool': 'Retool',
    'posthog': 'PostHog',
    'axiom-co': 'Axiom',
    'semgrep': 'Semgrep',
    'arize-ai': 'Arize AI',
    'weights-and-biases': 'Weights & Biases',
    'wandb': 'Weights & Biases',
    'huggingface': 'Hugging Face',
    'assemblyai': 'AssemblyAI',
    'replicate': 'Replicate',
    'modal-labs': 'Modal',
    'ramp': 'Ramp',
    'rippling': 'Rippling',
    'ironclad': 'Ironclad',
    'anduril': 'Anduril',
    'palantir': 'Palantir',
    'crusoe-energy': 'Crusoe Energy',
    'coreweave': 'CoreWeave',
    'lambdalabs': 'Lambda',
    'together-ai': 'Together AI',
    'regscale': 'RegScale',
    'drata': 'Drata',
    'vanta': 'Vanta',
    'lacework': 'Lacework',
    'chainguard': 'Chainguard',
    'tailscale': 'Tailscale',
    'zed-industries': 'Zed',
    'warp': 'Warp',
    'linear': 'Linear',
    'cal-com': 'Cal.com',
    'clerk': 'Clerk',
    'documenso': 'Documenso',
    'mintlify': 'Mintlify',
    'pieces-app': 'Pieces',
    'e2b': 'E2B',
    'browserbase': 'Browserbase',
    'zapier': 'Zapier',
    'make': 'Make',
    'n8n': 'n8n',
}

# New Ashby companies NOT already in harvest_ashby.py
ASHBY_NEW = {
    'openai': 'OpenAI',
    'midjourney': 'Midjourney',
    'anthropic': 'Anthropic',
    'jasper': 'Jasper',
    'adept': 'Adept',
    'character-ai': 'Character AI',
    'inflection': 'Inflection AI',
    'reka': 'Reka',
    'poolside': 'Poolside',
    'magic': 'Magic AI',
    'descript': 'Descript',
    'tome': 'Tome',
    'hex': 'Hex',
    'baseten': 'Baseten',
    'banana-dev': 'Banana',
    'beam': 'Beam',
    'render': 'Render',
    'fly': 'Fly.io',
    'railway': 'Railway',
    'sst': 'SST',
    'turso': 'Turso',
    'tigris-data': 'Tigris Data',
    'livekit': 'LiveKit',
    'daily-co': 'Daily',
    'miro': 'Miro',
    'loom': 'Loom',
    'vercel': 'Vercel',
    'gitpod': 'Gitpod',
    'coder': 'Coder',
    'stackblitz': 'StackBlitz',
    'val-town': 'Val Town',
    'nango': 'Nango',
    'merge-api': 'Merge',
    'unstructured': 'Unstructured',
    'chroma': 'Chroma',
    'qdrant': 'Qdrant',
    'marqo': 'Marqo',
    'vectara': 'Vectara',
    'anyscale': 'Anyscale',
    'modular': 'Modular',
    'sentry': 'Sentry',
    'axiom': 'Axiom',
    'logdna': 'LogDNA',
    'highlight-io': 'Highlight',
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
    'claude', 'chatbot', 'nlp', 'natural language',
]

NEGATIVE_KEYWORDS = [
    'intern', 'internship', 'director', 'vp ', 'vice president', 'chief',
    'head of', 'counsel', 'accountant', 'recruiter', 'sales',
    'account executive', 'marketing', 'communications', 'designer',
    'product design', 'graphic', 'ux research',
]

def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]

def score_job(title, location, content=''):
    title_lower = title.lower()
    loc_lower = (location or '').lower()
    content_lower = (content or '').lower()
    is_us = any(loc in loc_lower for loc in US_LOCATIONS)
    if not is_us and loc_lower:
        return 0
    score = 50
    for kw in POSITIVE_KEYWORDS:
        if kw in title_lower:
            score += 8
    for kw in NEGATIVE_KEYWORDS:
        if kw in title_lower:
            score -= 30
    for kw in ['mcp', 'model context protocol', 'agent', 'agentic', 'llm',
               'browser automation', 'automation', 'python', 'rust', 'typescript']:
        if kw in content_lower:
            score += 3
    if 'remote' in loc_lower:
        score += 10
    if 'senior' in title_lower or 'staff' in title_lower:
        score += 5
    return min(100, max(0, score))

def fetch_greenhouse(slug, company):
    url = 'https://boards-api.greenhouse.io/v1/boards/{}/jobs'.format(slug)
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

    print('=== GREENHOUSE (NEW COMPANIES) ===')
    for slug, company in GREENHOUSE_NEW.items():
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
            if score >= 65:
                print('  + [{}] {} @ {} ({})'.format(score, title, company, location))

    print('\n=== ASHBY (NEW COMPANIES) ===')
    for slug, company in ASHBY_NEW.items():
        jobs = fetch_ashby(slug, company)
        for job in jobs:
            title = job.get('title', '')
            job_id = job.get('id', '')
            location = job.get('location', '')
            if isinstance(location, dict):
                location = location.get('name', '')
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
            if score >= 65:
                print('  + [{}] {} @ {} ({})'.format(score, title, company, location))

    db.commit()
    db.close()
    print('\n=== EXPANDED HARVEST COMPLETE ===')
    print('Inserted: {}'.format(inserted))
    print('Skipped: {}'.format(skipped))
    print('Filtered: {}'.format(filtered))

if __name__ == '__main__':
    main()
