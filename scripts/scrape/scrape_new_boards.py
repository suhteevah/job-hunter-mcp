#!/usr/bin/env python3
"""
Scrape new remote job boards: RemoteOK, WeWorkRemotely, Himalayas, Jobicy, Remotive, Arc
and insert into jobs.db
"""
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import re
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'

TECH_KEYWORDS = [
    'software', 'engineer', 'developer', 'devops', 'python', 'javascript',
    'typescript', 'react', 'node', 'backend', 'frontend', 'fullstack',
    'full-stack', 'full stack', 'cloud', 'aws', 'azure', 'kubernetes',
    'docker', 'terraform', 'sre', 'site reliability', 'data engineer',
    'machine learning', 'ai ', ' ai,', 'ml ', 'automation', 'infrastructure',
    'golang', 'rust', 'java', 'scala', 'ruby', 'rails', 'django',
    'fastapi', 'api', 'microservice', 'linux', 'platform', 'sysadmin',
    'systems', 'security engineer', 'product engineer', 'staff engineer',
    'principal engineer', 'architect', 'data science', 'devops',
    'operations', 'reliability', 'engineering', 'programmer', 'coding',
]

def is_tech_job(title, tags=None):
    text = title.lower()
    if tags:
        if isinstance(tags, list):
            text += ' ' + ' '.join(str(t).lower() for t in tags)
        else:
            text += ' ' + str(tags).lower()
    return any(kw in text for kw in TECH_KEYWORDS)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn

def ensure_columns(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
    if 'source' not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN source TEXT")
    if 'salary_min' not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN salary_min INTEGER")
    if 'salary_max' not in cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN salary_max INTEGER")
    conn.commit()

def job_exists(conn, url):
    row = conn.execute("SELECT id FROM jobs WHERE url=?", (url,)).fetchone()
    return row is not None

def insert_job(conn, title, company, url, location, source, salary_min=None, salary_max=None):
    if job_exists(conn, url):
        return False
    conn.execute("""
        INSERT INTO jobs (title, company, url, location, source, salary_min, salary_max, date_found, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
    """, (title, company, url, location, source, salary_min, salary_max, datetime.now().isoformat()))
    return True

def fetch_url(url, timeout=30):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

# ============================================================
# SOURCE 1: RemoteOK JSON API
# ============================================================
def scrape_remoteok(conn):
    print("\n=== RemoteOK API ===")
    count = 0
    data = fetch_url("https://remoteok.com/api")
    if not data:
        return 0
    try:
        jobs = json.loads(data)
        if isinstance(jobs, list) and len(jobs) > 1:
            jobs = jobs[1:]  # skip legal notice (first item)
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = job.get('position', '')
            company = job.get('company', '')
            url = job.get('url', '') or job.get('apply_url', '')
            location = job.get('location', 'Remote') or 'Remote'
            tags = job.get('tags', [])
            salary_min = job.get('salary_min') or None
            salary_max = job.get('salary_max') or None
            if not title or not url:
                continue
            if not is_tech_job(title, tags):
                continue
            if salary_min == 0:
                salary_min = None
            if salary_max == 0:
                salary_max = None
            if insert_job(conn, title, company, url, location, 'remoteok', salary_min, salary_max):
                count += 1
                print(f"  + {title} @ {company}")
        conn.commit()
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
    print(f"  Total new from RemoteOK: {count}")
    return count

# ============================================================
# SOURCE 2: WeWorkRemotely - from scraped snapshot data
# ============================================================
def parse_wwr_from_snapshot(conn):
    print("\n=== We Work Remotely (snapshot) ===")
    count = 0

    wwr_jobs = [
        # Full-Stack Programming
        ("Senior Software Engineer", "WALTER", "/remote-jobs/walter-senior-software-engineer"),
        ("Software Engineer", "Cortes 23", "/remote-jobs/cortes-23-software-engineer-4"),
        ("Full-Stack PHP Developer", "OnTheGoSystems", "/remote-jobs/onthegosystems-full-stack-php-developer-1"),
        ("Software engineer", "Sticker Mule", "/remote-jobs/sticker-mule-software-engineer-2"),
        ("Full-Stack Engineering Lead", "Rare Days", "/remote-jobs/rare-days-full-stack-engineering-lead"),
        ("Principal Product Lead MarTech AI", "Bounteous", "/remote-jobs/bounteous-principal-product-lead-martech-ai"),
        ("Staff Software Engineer", "EngagedMD", "/remote-jobs/engagedmd-staff-software-engineer"),
        ("(Senior) AI Solutions Engineer", "Aktor AI", "/remote-jobs/aktor-ai-senior-ai-solutions-engineer"),
        ("Full-Stack Developer (Junior)", "LeadUp AI", "/remote-jobs/leadup-ai-full-stack-developer-junior"),
        ("Staff product engineer (fullstack)", "Moxie", "/remote-jobs/moxie-staff-product-engineer-fullstack-ic-4"),
        ("Full Stack Developer / Senior Full Stack / Lead", "CRUX", "/remote-jobs/crux-full-stack-developer-senior-full-stack-lead"),
        ("Senior Full-Stack Developer (AI-Assisted Development)", "Creatunity Llc", "/remote-jobs/creatunity-llc-senior-full-stack-developer-ai-assisted-development-remote"),
        ("Senior Software Engineer", "Stellar AI", "/remote-jobs/stellar-ai-senior-software-engineer"),
        ("Product Engineering Operations Director", "Vee Technologiesorporated", "/remote-jobs/vee-technologiesorporated-product-engineering-operations-director"),
        ("Senior Software Engineer", "Mangomint", "/remote-jobs/mangomint-senior-software-engineer"),
        ("Senior Software Engineer", "Strange Loop Labs", "/remote-jobs/strange-loop-labs-senior-software-engineer"),
        ("Full-Stack Developer", "ELECTE S.R.L.", "/remote-jobs/electe-s-r-l-full-stack-developer"),
        ("Software Engineer, Business Experience", "CodeSignal", "/remote-jobs/codesignal-software-engineer-business-experience-1"),
        (".NET Full Stack Developer (Power Platform)", "European Dynamics", "/remote-jobs/european-dynamics-net-full-stack-developer-power-platform-specialization"),
        ("Full Stack Engineer", "Ivy Tech", "/remote-jobs/ivy-tech-full-stack-engineer"),
        ("Senior Full Stack Developer (Java)", "Agentic Dream", "/remote-jobs/agentic-dream-senior-full-stack-developer-java"),
        ("Senior Independent Software Developer ($90-$170/hr)", "A.Team", "/remote-jobs/a-team-senior-independent-software-developer-90-170-hr"),
        ("PHL - Full-Stack Developer", "Tidal", "/remote-jobs/tidal-phl-full-stack-developer"),
        ("Full Stack Developer mit Erfahrung in Shopware 6 - 100% remote", "Mrp My Recruitment Partners", "/remote-jobs/mrp-my-recruitment-partners-full-stack-developer-mit-erfahrung-in-shopware-6-all-genders-2"),
        ("Web3 Full Stack Developer", "Hyphen Connect Limited", "/remote-jobs/hyphen-connect-limited-web3-full-stack-developer-1"),
        ("Full Stack Developer (gn)", "Contentserv", "/remote-jobs/contentserv-full-stack-developer-gn"),
        ("Full Stack Developer (Low-Code, Bubble.io)", "Hector Kitchen", "/remote-jobs/hector-kitchen-full-stack-developer-low-code-bubble-io"),
        ("Full Stack Developer (PHP, Laravel, WordPress & JavaScript)", "Bold & Epic Craft Llc", "/remote-jobs/bold-epic-craft-llc-full-stack-developer-php-laravel-wordpress-javascript"),
        ("Senior/Staff Product Engineer (Full Stack)", "Epilot", "/remote-jobs/epilot-senior-staff-product-engineer-full-stack-m-f-d"),
        ("Senior Full-Stack Engineer - Product", "Railway", "/remote-jobs/railway-senior-full-stack-engineer-product"),
        ("Senior Shopify Developer (Remote + Flexible)", "Storetasker", "/remote-jobs/storetasker-senior-shopify-developer-remote-flexible-3"),
        ("Senior React Full-stack Developer", "Lemon.io", "/remote-jobs/lemon-io-senior-react-full-stack-developer-3"),
        # DevOps / Sysadmin
        ("Information Security Engineer, Product", "Aptos", "/remote-jobs/aptos-information-security-engineer-product"),
        ("Senior DevOps Engineer", "Intetics", "/remote-jobs/intetics-1025-senior-devops-engineer"),
        ("Product Security Manager, Secure Design", "Digitalocean", "/remote-jobs/digitalocean-product-security-manager-secure-design"),
        ("Senior Staff DevOps Engineer - MetaMask", "Consensys", "/remote-jobs/consensys-senior-staff-devops-engineer-metamask"),
        ("Sr. DevOps AWS Cloud Engineer", "H1", "/remote-jobs/h1-sr-devops-aws-cloud-engineer"),
        ("(f2pool) DevOps Engineer", "Stakefish", "/remote-jobs/stakefish-f2pool-devops-engineer"),
        ("AI Product Builder", "Abnormal", "/remote-jobs/abnormal-ai-product-builder"),
        ("Senior Software Engineer II - Product Security", "Confluent", "/remote-jobs/confluent-senior-software-engineer-ii-product-security"),
        ("Azure DevOps Engineer", "Digital Forms", "/remote-jobs/digital-forms-azure-devops-engineer"),
        ("DevOps Engineer (Remote/Thessaloniki)", "European Dynamics", "/remote-jobs/european-dynamics-devops-engineer-remote-thessaloniki"),
        ("Backend/DevOps Engineer", "Nick Ai", "/remote-jobs/nick-ai-backend-devops-engineer"),
        ("Full Stack Developer (Python/Django/Next.js/Kubernetes)", "Rhino Partners", "/remote-jobs/rhino-partners-full-stack-developer-python-django-next-js-kubernetes-remote"),
        ("M0 Labs - DevOps Engineer", "Decircle", "/remote-jobs/decircle-m0-labs-devops-engineer"),
        ("TeamLead DevOps", "Akinox Solutions", "/remote-jobs/akinox-solutions-teamlead-devops"),
        ("Security Engineer in Product Security", "Jetbrains", "/remote-jobs/jetbrains-security-engineer-in-product-security"),
        ("Sr. DevOps Go Developer", "Thaloz", "/remote-jobs/thaloz-he-sr-devops-go-developer-171"),
        ("SR Data Engineer/DevOps", "Coderio", "/remote-jobs/coderio-sr-data-engineer-devops"),
        ("Senior Azure DevOps Engineer", "Tasq Staffing Solutions", "/remote-jobs/tasq-staffing-solutions-senior-azure-devops-engineer-remote-midshift"),
        ("Software Development Coach (Domain-Driven Design, Go)", "Skiller Whale", "/remote-jobs/skiller-whale-software-development-coach-flexible-domain-driven-design-go-others"),
        ("Cloud Engineer (Ruby/DevOps) 100% remote", "Newsmatics", "/remote-jobs/newsmatics-cloud-engineer-ruby-devops-100-remote"),
        ("DevOps Team Leader", "Fetcherr", "/remote-jobs/fetcherr-devops-team-leader"),
        ("Lead DevOps Engineer (100% Remote)", "Tether Operations Limited", "/remote-jobs/tether-operations-limited-lead-devops-engineer-100-remote"),
        ("DevOps/SRE", "Selector Software", "/remote-jobs/selector-software-devops-sre"),
        ("DevOps & QA Automation Engineer (Remote)", "Remotestar", "/remote-jobs/remotestar-devops-qa-automation-engineer-remote"),
        ("Senior DevOps Engineer (with Go/Python)", "Corva", "/remote-jobs/corva-senior-devops-engineer-with-go-python-development-experience"),
        ("Lead DevOps Engineer - AWS", "Confidential", "/remote-jobs/confidential-lead-devops-engineer-aws"),
        ("Senior Cloud Consultant - DevOps (4-Days-Week)", "Auvaria", "/remote-jobs/auvaria-senior-cloud-consultant-devops-f-m-d-4-days-week-en"),
        ("Cloud Engineer (DevOps)", "Trafilea", "/remote-jobs/trafilea-cloud-engineer-devops"),
        ("Linux Administrator (DevOps team)", "Syrve", "/remote-jobs/syrve-linux-administrator-devops-team"),
        ("DevOps Engineer - Open Application", "Truelogic", "/remote-jobs/truelogic-devops-engineer-open-application"),
        ("Middle DevOps Engineer", "Aida Recruitment", "/remote-jobs/aida-recruitment-middle-devops-engineer"),
        ("Security Engineer, Product Security", "Chainlink Labs", "/remote-jobs/chainlink-labs-security-engineer-product-security"),
        ("Senior Linux Systems Administrator & DevOps Engineer", "Bcw", "/remote-jobs/bcw-senior-linux-systems-administrator-devops-engineer-remote"),
        ("Senior DevOps Engineer (Remote)", "CashJar.com", "/remote-jobs/cashjar-com-senior-devops-engineer-remote-for-outsidehire"),
        ("Python Backend & DevOps (Full-Remoto)", "Se Parte De Nuestro Equipo", "/remote-jobs/se-parte-de-nuestro-equipo-se-vos-python-backend-devops-full-remoto"),
        ("Cloud Specialist DevOps", "Escala 24x7", "/remote-jobs/escala-24x7-careers-cloud-specialist-devops"),
        ("Ingenieur DevOps (OpenStack Cloud)", "Vexxhost", "/remote-jobs/vexxhost-ingenieur-e-de-openstack-cloud-devops"),
    ]

    base = "https://weworkremotely.com"
    for title, company, slug in wwr_jobs:
        full_url = f"{base}{slug}"
        if insert_job(conn, title, company, full_url, 'Remote', 'weworkremotely'):
            count += 1
            print(f"  + {title} @ {company}")

    conn.commit()
    print(f"  Total new from WeWorkRemotely: {count}")
    return count

# ============================================================
# SOURCE 3: Himalayas API
# ============================================================
def scrape_himalayas(conn):
    print("\n=== Himalayas API ===")
    count = 0

    endpoints = [
        "https://himalayas.app/jobs/api?limit=50&categories=software-engineering",
        "https://himalayas.app/jobs/api?limit=50&categories=devops",
        "https://himalayas.app/jobs/api?limit=50&categories=cloud-computing",
        "https://himalayas.app/jobs/api?limit=50&categories=data-engineering",
    ]

    for url in endpoints:
        print(f"  Fetching: {url}")
        data = fetch_url(url)
        if not data:
            continue
        try:
            parsed = json.loads(data)
            jobs = parsed.get('jobs', [])
            print(f"    Got {len(jobs)} jobs (total: {parsed.get('totalCount', '?')})")
            for job in jobs:
                title = job.get('title', '')
                company = job.get('companyName', '')
                apply_url = job.get('applicationLink', '') or job.get('guid', '')
                restrictions = job.get('locationRestrictions', [])
                if restrictions:
                    location = f"Remote - {', '.join(str(r) for r in restrictions[:2])}"
                else:
                    location = 'Remote'
                salary_min = job.get('minSalary')
                salary_max = job.get('maxSalary')
                cats = job.get('categories', [])
                if not title or not apply_url:
                    continue
                if not is_tech_job(title, cats):
                    continue
                if insert_job(conn, title, company, apply_url, location, 'himalayas', salary_min, salary_max):
                    count += 1
                    print(f"    + {title} @ {company}")
        except json.JSONDecodeError as e:
            print(f"    JSON error: {e}")
        time.sleep(1)

    conn.commit()
    print(f"  Total new from Himalayas: {count}")
    return count

# ============================================================
# SOURCE 4: Jobicy API
# ============================================================
def scrape_jobicy(conn):
    print("\n=== Jobicy API ===")
    count = 0

    tags = ['devops', 'python', 'javascript', 'cloud', 'engineer', 'backend', 'api', 'golang', 'rust']

    for tag in tags:
        url = f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}"
        print(f"  Fetching tag={tag}")
        data = fetch_url(url)
        if not data:
            continue
        try:
            parsed = json.loads(data)
            jobs = parsed.get('jobs', [])
            cnt = parsed.get('jobCount', 0)
            print(f"    Got {cnt} jobs")
            for job in jobs:
                title = job.get('jobTitle', '')
                company = job.get('companyName', '')
                url_j = job.get('url', '')
                geo = job.get('jobGeo', 'Remote') or 'Remote'
                location = f"Remote - {geo}"
                salary_min = job.get('salaryMin') or None
                salary_max = job.get('salaryMax') or None
                industry = job.get('jobIndustry', [])
                if not title or not url_j:
                    continue
                if not is_tech_job(title, industry):
                    continue
                if salary_min == 0:
                    salary_min = None
                if salary_max == 0:
                    salary_max = None
                if insert_job(conn, title, company, url_j, location, 'jobicy', salary_min, salary_max):
                    count += 1
                    print(f"    + {title} @ {company}")
        except json.JSONDecodeError as e:
            print(f"    JSON error: {e}")
        time.sleep(0.5)

    conn.commit()
    print(f"  Total new from Jobicy: {count}")
    return count

# ============================================================
# SOURCE 5: Remotive API (public, no auth needed)
# ============================================================
def scrape_remotive(conn):
    print("\n=== Remotive API ===")
    count = 0

    categories = ['software-dev', 'devops-sysadmin', 'data', 'qa']

    for cat in categories:
        url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=100"
        print(f"  Fetching category={cat}")
        data = fetch_url(url)
        if not data:
            continue
        try:
            parsed = json.loads(data)
            jobs = parsed.get('jobs', [])
            print(f"    Got {len(jobs)} jobs")
            for job in jobs:
                title = job.get('title', '')
                company = job.get('company_name', '')
                url_j = job.get('url', '')
                geo = job.get('candidate_required_location', '') or 'Remote'
                tags = job.get('tags', [])
                if not title or not url_j:
                    continue
                if not is_tech_job(title, tags):
                    continue
                if insert_job(conn, title, company, url_j, geo, 'remotive'):
                    count += 1
                    print(f"    + {title} @ {company}")
        except json.JSONDecodeError as e:
            print(f"    JSON error: {e}")
        time.sleep(0.5)

    conn.commit()
    print(f"  Total new from Remotive: {count}")
    return count

# ============================================================
# SOURCE 6: Arc.dev (from snapshot + try scraping)
# ============================================================
def parse_arc_from_snapshot(conn):
    print("\n=== Arc.dev (snapshot + API) ===")
    count = 0

    # Jobs visible from the snapshot before login wall
    arc_jobs = [
        ("SAP BW/4HANA Data Engineer with German | Energy Sector", "Polcode", "https://arc.dev/remote-jobs/sap-bw-4hana-data-engineer-with-german-energy-sector", "Remote - Poland"),
        ("Senior Frontend Engineer", "hackajob", "https://arc.dev/remote-jobs/senior-frontend-engineer", "Remote - UK"),
        ("Senior Developer, Software", "Sherweb", "https://arc.dev/remote-jobs/senior-developer-software", "Remote - Canada, India"),
        ("Business Analyst / Requirements Engineer - SaaS Product", "CENDAS", "https://arc.dev/remote-jobs/business-analyst-requirements-engineer-saas-product", "Remote - Germany"),
        ("Developer Specializing In AI Tools", "Unknown", "https://arc.dev/remote-jobs/developer-specializing-ai-tools", "Remote"),
        ("Content Writer with Developer and Engineering Expertise", "Unknown", "https://arc.dev/remote-jobs/content-writer-developer-engineering-expertise", "Remote"),
        ("Staff Product Designer", "HubSpot", "https://arc.dev/remote-jobs/staff-product-designer-eastern-or-central-time-zones", "Remote - US"),
    ]

    for title, company, url, location in arc_jobs:
        if not is_tech_job(title):
            continue
        if insert_job(conn, title, company, url, location, 'arc'):
            count += 1
            print(f"  + {title} @ {company}")

    # Try Arc's internal API
    arc_api_url = "https://arc.dev/api/jobs?page=1&category=software-development&remote=true"
    data = fetch_url(arc_api_url)
    if data:
        try:
            parsed = json.loads(data)
            jobs = parsed.get('jobs', parsed.get('data', []))
            for job in jobs[:50]:
                title = job.get('title', '') or job.get('name', '')
                company = job.get('company', {}).get('name', '') if isinstance(job.get('company'), dict) else job.get('company', '')
                url_j = job.get('url', '') or f"https://arc.dev/remote-jobs/{job.get('slug', '')}"
                location = job.get('location', 'Remote') or 'Remote'
                if title and url_j and is_tech_job(title):
                    if insert_job(conn, title, company, url_j, location, 'arc'):
                        count += 1
                        print(f"  + {title} @ {company} [API]")
        except Exception:
            pass

    conn.commit()
    print(f"  Total new from Arc: {count}")
    return count

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("New Remote Job Board Scraper")
    print(f"DB: {DB_PATH}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    conn = get_db()
    ensure_columns(conn)

    totals = {}

    totals['remoteok'] = scrape_remoteok(conn)
    totals['weworkremotely'] = parse_wwr_from_snapshot(conn)
    totals['himalayas'] = scrape_himalayas(conn)
    totals['jobicy'] = scrape_jobicy(conn)
    totals['remotive'] = scrape_remotive(conn)
    totals['arc'] = parse_arc_from_snapshot(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY - New jobs inserted per source:")
    total_all = 0
    for source, cnt in totals.items():
        print(f"  {source:20s}: {cnt:4d} new jobs")
        total_all += cnt
    print(f"  {'TOTAL':20s}: {total_all:4d} new jobs")
    print("=" * 60)
    return total_all

if __name__ == '__main__':
    total = main()
    sys.exit(0 if total >= 0 else 1)
