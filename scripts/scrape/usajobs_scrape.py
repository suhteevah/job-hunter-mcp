"""Scrape USAJobs public REST API for tech/engineering roles and insert into jobs.db."""
import sys, sqlite3, json, hashlib, datetime, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'
NOW = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

USAJOBS_API = 'https://data.usajobs.gov/api/search'
USER_EMAIL = 'ridgecellrepair@gmail.com'
API_KEY = '+E/sq3/7l1LZuKLtLj5NXVciBHEFUmOKc4J2FvJxZ2k='

SEARCHES = [
    {'Keyword': 'software engineer',      'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'AI engineer',            'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'machine learning',       'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'devops engineer',        'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'data engineer',          'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'automation engineer',    'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'python developer',       'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'cybersecurity engineer', 'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'cloud engineer',         'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'IT specialist',          'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'systems administrator',  'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'firmware engineer',      'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'embedded engineer',      'ResultsPerPage': '500', 'DatePosted': '7'},
    {'Keyword': 'network engineer',       'ResultsPerPage': '500', 'DatePosted': '7'},
]

POSITIVE_KEYWORDS = [
    'software engineer', 'ai engineer', 'machine learning', 'devops', 'data engineer',
    'automation', 'python', 'cybersecurity', 'cloud', 'infrastructure', 'platform',
    'backend', 'full stack', 'fullstack', 'sre', 'systems engineer', 'it specialist',
    'developer', 'programmer', 'analyst', 'architect',
]

NEG_KEYWORDS = [
    'intern', 'director', 'vp ', 'vice president', 'chief', 'head of',
    'counsel', 'attorney', 'accountant', 'recruiter', 'sales',
    'marketing', 'communications', 'designer', 'product design',
    'nurse', 'medical', 'dental', 'doctor', 'physician',
]


def make_id(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


def score_job(title):
    tl = title.lower()
    score = 50
    for kw in POSITIVE_KEYWORDS:
        if kw in tl:
            score += 7
    for kw in NEG_KEYWORDS:
        if kw in tl:
            score -= 25
    if 'senior' in tl or 'staff' in tl or 'lead' in tl:
        score += 5
    return min(100, max(0, score))


def fetch_usajobs(params):
    qs = urllib.parse.urlencode(params)
    url = '{}?{}'.format(USAJOBS_API, qs)
    headers = {
        'User-Agent': USER_EMAIL,
        'Authorization-Key': API_KEY,
        'Host': 'data.usajobs.gov',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = (data.get('SearchResult', {})
                         .get('SearchResultItems', []))
            print('  Keyword={!r}: {} results'.format(params.get('Keyword'), len(items)))
            return items
    except Exception as e:
        print('  Keyword={!r}: FAILED - {}'.format(params.get('Keyword'), str(e)[:80]))
        return []


def parse_salary(remuneration_list):
    if not remuneration_list:
        return None
    r = remuneration_list[0]
    lo = r.get('MinimumRange', '')
    hi = r.get('MaximumRange', '')
    rate = r.get('RateIntervalCode', '')
    if lo and hi:
        return '${} - ${} {}'.format(lo, hi, rate).strip()
    if lo:
        return '${} {}'.format(lo, rate).strip()
    return None


def parse_location(position_locations):
    if not position_locations:
        return 'Remote'
    locs = [pl.get('LocationName', '') for pl in position_locations if pl.get('LocationName')]
    return ', '.join(locs[:2]) if locs else 'Remote'


def main():
    db = sqlite3.connect(DB)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout=60000')
    c = db.cursor()

    total_found = 0
    inserted = 0
    skipped = 0
    filtered = 0

    seen_ids = set()  # dedup within this run

    for params in SEARCHES:
        items = fetch_usajobs(params)
        time.sleep(1)  # be polite

        for item in items:
            d = item.get('MatchedObjectDescriptor', {})

            title = d.get('PositionTitle', '').strip()
            if not title:
                continue

            org = d.get('OrganizationName', 'US Government').strip()
            url = d.get('PositionURI', '').strip()
            if not url:
                continue

            job_id = make_id(url)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            total_found += 1

            score = score_job(title)
            if score < 45:
                filtered += 1
                continue

            location = parse_location(d.get('PositionLocation', []))
            salary = parse_salary(d.get('PositionRemuneration', []))

            details = d.get('UserArea', {}).get('Details', {})
            duties_list = details.get('MajorDuties', [])
            if isinstance(duties_list, list):
                duties = ' '.join(duties_list)
            else:
                duties = str(duties_list)
            qual_summary = d.get('QualificationSummary', '')
            description = '{}\n\n{}'.format(qual_summary, duties).strip()

            date_posted = d.get('PublicationStartDate', '')
            if date_posted:
                date_posted = date_posted[:10]

            job_type_list = d.get('PositionSchedule', [])
            job_type = job_type_list[0].get('Name', '') if job_type_list else None

            # Check for existing record
            c.execute('SELECT id FROM jobs WHERE id = ?', (job_id,))
            if c.fetchone():
                skipped += 1
                continue

            c.execute("""
                INSERT INTO jobs
                    (id, source, source_id, title, company, url, location,
                     salary, job_type, category, description,
                     date_posted, date_found, fit_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, 'usajobs', job_id,
                title, org, url, location,
                salary, job_type, 'government',
                description[:4000] if description else None,
                date_posted, NOW,
                float(score), 'new',
            ))
            inserted += 1

        db.commit()

    db.close()

    print()
    print('=== USAJobs Scrape Complete ===')
    print('  Total API results : {}'.format(total_found))
    print('  Score-filtered out: {}'.format(filtered))
    print('  Already in DB     : {}'.format(skipped))
    print('  Newly inserted    : {}'.format(inserted))


if __name__ == '__main__':
    main()
