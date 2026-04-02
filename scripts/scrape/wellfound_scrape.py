"""Scrape Wellfound (AngelList Talent) job search pages for tech roles and insert into jobs.db."""
import sys, sqlite3, hashlib, datetime, time, random, re, html
import urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

BASE_URL = 'https://wellfound.com'

ROLE_PAGES = [
    '/role/r/software-engineer',
    '/role/r/machine-learning-engineer',
    '/role/r/devops-engineer',
    '/role/r/backend-engineer',
    '/role/r/ai-engineer',
]

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/123.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

POSITIVE_KEYWORDS = [
    'engineer', 'developer', 'architect', 'machine learning', 'ai', 'ml',
    'backend', 'full stack', 'fullstack', 'platform', 'infrastructure',
    'devops', 'sre', 'data', 'python', 'automation', 'cloud', 'security',
]

NEG_KEYWORDS = [
    'intern', 'director', 'vp ', 'vice president', 'chief', 'head of',
    'counsel', 'attorney', 'accountant', 'recruiter', 'sales',
    'marketing', 'communications', 'designer', 'product design',
]


def make_id(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


def score_job(title):
    tl = title.lower()
    score = 55  # wellfound tends to be startup tech — start higher
    for kw in POSITIVE_KEYWORDS:
        if kw in tl:
            score += 6
    for kw in NEG_KEYWORDS:
        if kw in tl:
            score -= 25
    if 'senior' in tl or 'staff' in tl or 'lead' in tl:
        score += 5
    return min(100, max(0, score))


def fetch_page(path):
    url = BASE_URL + path
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_encoding = resp.headers.get('Content-Encoding', '')
            raw = resp.read()
            if content_encoding == 'gzip':
                import gzip
                raw = gzip.decompress(raw)
            elif content_encoding == 'br':
                # brotli not in stdlib; fall back gracefully
                try:
                    import brotli
                    raw = brotli.decompress(raw)
                except ImportError:
                    pass  # attempt utf-8 decode anyway
            return raw.decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        print('  HTTP {}: {}'.format(e.code, url))
        return ''
    except Exception as e:
        print('  FETCH ERROR {}: {}'.format(url, str(e)[:80]))
        return ''


# ---------------------------------------------------------------------------
# HTML parsing — Wellfound renders job cards with data attributes and
# recognisable class patterns.  We use regex since stdlib has no HTML parser
# that handles modern malformed markup well at the detail level we need.
# ---------------------------------------------------------------------------

def unescape(text):
    return html.unescape(text) if text else text


def extract_jobs_from_html(page_html, role_path):
    """
    Extract job listings from a Wellfound role page.
    Wellfound embeds job data in the page's __NEXT_DATA__ JSON blob,
    and also in individual job-card divs.  We try the JSON blob first,
    then fall back to regex over the HTML.
    """
    jobs = []

    # --- Strategy 1: parse __NEXT_DATA__ JSON blob ---
    next_data_match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        page_html, re.DOTALL
    )
    if next_data_match:
        try:
            import json
            blob = json.loads(next_data_match.group(1))
            # Walk the props tree looking for job listings
            jobs_from_json = _extract_from_next_data(blob, role_path)
            if jobs_from_json:
                print('    JSON strategy: {} jobs'.format(len(jobs_from_json)))
                return jobs_from_json
        except Exception as e:
            print('    JSON parse error: {}'.format(str(e)[:60]))

    # --- Strategy 2: regex over rendered HTML card elements ---
    # Job cards typically contain a link to /jobs/<id> and company name nearby
    # Pattern: <a href="/jobs/SLUG-at-COMPANY...">Title</a>
    pattern = re.compile(
        r'href=["\'](?P<url>/jobs/[^"\'?\s]+)["\'][^>]*>(?P<title>[^<]{3,120})</a',
        re.IGNORECASE
    )
    company_pattern = re.compile(
        r'data-company=["\']([^"\']+)["\']|'
        r'class=["\'][^"\']*company[^"\']*["\'][^>]*>([^<]{2,80})</(?:span|div|a|p)',
        re.IGNORECASE
    )

    seen_urls = set()
    for m in pattern.finditer(page_html):
        raw_url = m.group('url')
        if raw_url in seen_urls:
            continue
        seen_urls.add(raw_url)

        title = unescape(m.group('title')).strip()
        if len(title) < 3 or len(title) > 120:
            continue
        # Filter obviously non-title text
        if any(c in title for c in ['<', '>', '{', '}']):
            continue

        full_url = BASE_URL + raw_url

        # Try to extract company name from surrounding context (±500 chars)
        start = max(0, m.start() - 500)
        end = min(len(page_html), m.end() + 500)
        context = page_html[start:end]

        company = 'Unknown'
        cm = company_pattern.search(context)
        if cm:
            company = unescape(cm.group(1) or cm.group(2) or 'Unknown').strip()

        # Derive company from URL slug if still unknown: /jobs/role-at-CompanyName
        if company == 'Unknown':
            slug_match = re.search(r'-at-([^/?#]+)$', raw_url)
            if slug_match:
                company = slug_match.group(1).replace('-', ' ').title()

        jobs.append({
            'title': title,
            'company': company,
            'url': full_url,
        })

    print('    HTML strategy: {} jobs'.format(len(jobs)))
    return jobs


def _extract_from_next_data(blob, role_path):
    """Recursively search the Next.js data blob for job listing objects."""
    jobs = []
    _walk_json(blob, jobs)
    return jobs


def _walk_json(node, jobs, depth=0):
    """Walk arbitrary JSON looking for objects that look like job listings."""
    if depth > 12:
        return
    if isinstance(node, dict):
        # Heuristic: a job object will have title + slug/url + company fields
        title = node.get('title') or node.get('jobTitle') or node.get('name')
        url = (node.get('url') or node.get('slug') or
               node.get('applyUrl') or node.get('jobUrl') or '')
        company_node = node.get('company') or node.get('startup') or {}
        if isinstance(company_node, dict):
            company = (company_node.get('name') or
                       company_node.get('companyName') or '')
        else:
            company = str(company_node) if company_node else ''

        if title and isinstance(title, str) and len(title) > 3:
            if not url or not url.startswith('http'):
                slug = node.get('slug') or node.get('id') or ''
                if slug:
                    url = '{}/jobs/{}'.format(BASE_URL, slug)
                else:
                    url = ''
            if url and company:
                jobs.append({
                    'title': str(title).strip(),
                    'company': str(company).strip(),
                    'url': url if url.startswith('http') else BASE_URL + url,
                    'location': node.get('locationNames') or node.get('remote') or 'Remote',
                    'salary': node.get('compensation') or node.get('salary'),
                    'description': node.get('description') or node.get('jobDescription'),
                })
                return  # don't recurse into a job node we already captured

        for v in node.values():
            _walk_json(v, jobs, depth + 1)

    elif isinstance(node, list):
        for item in node:
            _walk_json(item, jobs, depth + 1)


def main():
    db = sqlite3.connect(DB)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout=60000')
    c = db.cursor()

    total_found = 0
    inserted = 0
    skipped = 0
    filtered = 0
    seen_ids = set()

    for role_path in ROLE_PAGES:
        print('Fetching {}{} ...'.format(BASE_URL, role_path))
        page_html = fetch_page(role_path)

        if not page_html:
            print('  No content returned, skipping.')
        else:
            jobs = extract_jobs_from_html(page_html, role_path)
            total_found += len(jobs)

            for job in jobs:
                title = job.get('title', '').strip()
                company = job.get('company', 'Unknown').strip()
                url = job.get('url', '').strip()

                if not title or not url:
                    continue

                job_id = make_id(url)
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                score = score_job(title)
                if score < 45:
                    filtered += 1
                    continue

                # Location normalisation
                loc_raw = job.get('location')
                if isinstance(loc_raw, list):
                    location = ', '.join(str(x) for x in loc_raw if x)
                elif isinstance(loc_raw, bool):
                    location = 'Remote' if loc_raw else 'Unknown'
                elif loc_raw:
                    location = str(loc_raw).strip()
                else:
                    location = 'Remote'

                salary = str(job.get('salary', '') or '').strip() or None
                description = str(job.get('description', '') or '').strip() or None
                if description:
                    description = description[:4000]

                c.execute('SELECT id FROM jobs WHERE id = ?', (job_id,))
                if c.fetchone():
                    skipped += 1
                    continue

                c.execute("""
                    INSERT INTO jobs
                        (id, source, source_id, title, company, url, location,
                         salary, category, description,
                         date_found, fit_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, 'wellfound', job_id,
                    title, company, url, location,
                    salary, 'startup',
                    description,
                    NOW, float(score), 'new',
                ))
                inserted += 1

        db.commit()

        # Polite random delay between page requests (2-5 seconds)
        delay = random.uniform(2.0, 5.0)
        print('  Sleeping {:.1f}s before next request...'.format(delay))
        time.sleep(delay)

    db.close()

    print()
    print('=== Wellfound Scrape Complete ===')
    print('  Total parsed      : {}'.format(total_found))
    print('  Score-filtered out: {}'.format(filtered))
    print('  Already in DB     : {}'.format(skipped))
    print('  Newly inserted    : {}'.format(inserted))


if __name__ == '__main__':
    main()
