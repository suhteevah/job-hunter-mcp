#!/usr/bin/env python
"""
parse_builtin_batch2.py - Parse BuiltIn dev-engineering remote jobs page 1
"""
import sys, sqlite3, uuid, re, logging
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from datetime import datetime

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MARKDOWN = """
[Applied Systems](/company/applied-systems)
## [Software Engineer](/job/software-engineer/8937623)
Remote or Hybrid United States 60K-120K Annually Junior level C# JavaScript TypeScript

[Rain](/company/rain-1)
## [Software Engineer - EVM](/job/software-engineer-blockchain/8135064)
Remote or Hybrid New York, NY, USA 150K-275K Annually Mid level Blockchain Node.js Smart Contracts

[Circle (circle.so)](/company/circle-so)
## [Senior Back-End Software Engineer, Infra](/job/senior-back-end-software-engineer-infra/8930453)
Remote 31 Locations 130K-140K Annually Senior level MySQL Postgres Ruby On Rails

[Vercel](/company/vercel)
## [Software Engineer, CDN Security](/job/software-engineer-cdn-security/8926445)
Remote United States 187K-280K Annually Mid level Go Lua

[Vercel](/company/vercel)
## [Software Engineer, Dashboard](/job/software-engineer-dashboard/8926429)
In-Office or Remote 2 Locations 196K-294K Annually Senior level Next.js React TypeScript

[Atlassian](/company/atlassian)
## [Senior Full Stack Software Engineer, DX](/job/full-stack-software-engineer-dx/8921312)
In-Office or Remote Washington, DC, USA 147K-230K Annually Senior level AWS React Ruby On Rails

[Atlassian](/company/atlassian)
## [Full Stack Software Engineer, DX](/job/full-stack-software-engineer-dx/8921310)
In-Office or Remote Salt Lake City, UT, USA 100K-156K Annually Junior level Ruby on Rails SQL

[Vercel](/company/vercel)
## [Software Engineer, Lua](/job/software-engineer-lua/7288266)
Remote United States 196K-280K Annually Senior level Go HTTP Lua

[Optum](/company/optum)
## [Senior Big Data Software Engineer Remote](/job/senior-big-data-software-engineer-remote/8677993)
In-Office or Remote Eden Prairie, MN, USA 92K-164K Annually Senior level Azure Databricks Python Spark SQL

[Gusto](/company/gusto)
## [Staff Mobile Software Engineer, Android](/job/mobile-engineer-android/7187836)
Remote or Hybrid 2 Locations 164K-260K Annually Senior level Android Kotlin

[Whatnot](/company/whatnot)
## [Software Engineer, Search & Discovery Platform](/job/software-engineer-search-and-discovery-platform/7507881)
In-Office or Remote 4 Locations 170K-230K Annually Senior level AWS Elasticsearch Kafka Python Spark

[Whatnot](/company/whatnot)
## [Software Engineer, Customer Experience](/job/software-engineer-customer-experience/7507890)
In-Office or Remote 4 Locations 195K-230K Annually Senior level Elixir Postgres Python

[Whatnot](/company/whatnot)
## [Software Engineer, Seller Growth](/job/software-engineer-seller-growth/7507875)
In-Office or Remote 4 Locations 195K-290K Annually Senior level Elixir JavaScript Python SQL

[General Motors](/company/general-motors)
## [Staff Android Software Engineer](/job/staff-android-software-engineer/8208931)
Remote or Hybrid Mountain View, CA, USA 157K-333K Annually Senior level Android Java Linux

[Hex](/company/hex)
## [Software Engineer, Backend (Platform)](/job/software-engineer-compute/7901975)
Remote or Hybrid 2 Locations 176K-220K Annually Senior level AWS Kubernetes Postgres Python Redis

[MongoDB](/company/mongodb)
## [Software Engineer, Networking & Observability](/job/software-engineer-networking-observability/8669877)
Remote or Hybrid 2 Locations 109K-215K Annually Mid level C++

[CrowdStrike](/company/crowdstrike)
## [Full Stack Software Engineer III, Infrastructure (Remote)](/job/software-engineer-iii-infrastructure-engineering-remote/6692184)
Remote or Hybrid USA 120K-180K Annually Senior level AWS Go Kubernetes React Terraform TypeScript

[Affirm](/company/affirm)
## [Software Engineer II, Backend (Marketplace Performance)](/job/software-engineer-ii-backend-marketplace-performance/8908754)
Remote United States 142K-210K Annually Junior level Kotlin Python React Vue

[Airwallex](/company/airwallex)
## [(Senior) Software Engineer (Frontend), Growth](/job/senior-software-engineer-frontend-growth/8221834)
Remote or Hybrid San Francisco, CA, USA Senior level React TypeScript

[Vercel](/company/vercel)
## [Software Engineer, Accounts](/job/software-engineer-accounts/3970120)
Remote United States 196K-294K Annually Mid level AWS JavaScript Kubernetes Node.js TypeScript

[Dropbox](/company/dropbox)
## [Staff Backend Product Software Engineer, Core](/job/staff-backend-product-software-engineer-core/8905310)
Remote United States 223K-302K Annually Mid level Java Machine Learning Python SQL

[Dropbox](/company/dropbox)
## [Staff Product Backend Software Engineer, Core Sync](/job/staff-product-backend-software-engineer-core-sync/8041512)
Remote United States 248K-336K Annually Expert/Leader C++ Go Python Rust

[Dropbox](/company/dropbox)
## [Staff Fullstack Software Engineer, Growth Monetization](/job/staff-fullstack-software-engineer-growth-monetization/7887981)
Remote United States 223K-302K Annually Senior level Go Python React TypeScript

[Garner Health](/company/garner-health)
## [Software Engineer II](/job/software-engineer-ii/8645709)
Remote USA 138K-160K Annually Junior level Airflow AWS Kubernetes Python

[YCharts](/company/ycharts)
## [Software Engineer II - Applied AI](/job/software-engineer-ii-applied-ai/7643812)
Remote or Hybrid United States 140K-180K Annually Junior level Anthropic Django FastAPI OpenAI Python TypeScript
"""

def parse_md(text):
    jobs = []
    lines = text.strip().split('\n')
    current_company = None
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Company line
        cm = re.match(r'^\[([^\]]+)\]\(/company/[^\)]+\)$', line)
        if cm:
            current_company = cm.group(1).strip()
            continue
        # Job line
        jm = re.match(r'^##\s+\[([^\]]+)\]\(/job/([^/\)]+)/(\d+)\)', line)
        if jm:
            title = jm.group(1).strip()
            slug = jm.group(2).strip()
            jid = jm.group(3).strip()
            url = f"https://builtin.com/job/{slug}/{jid}"
            # Location from next line
            loc_line = lines[i+1].strip() if i+1 < len(lines) else ''
            if 'Remote' in loc_line or 'Hybrid' in loc_line:
                if 'United States' in loc_line or 'USA' in loc_line:
                    loc = 'United States'
                else:
                    loc = 'Remote'
            else:
                loc = 'Remote'
            desc = loc_line[:500]
            jobs.append({'title': title, 'company': current_company or 'BuiltIn', 'url': url, 'location': loc, 'source': 'builtin', 'description': desc})
    return jobs

def insert(jobs):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()
    ins = 0
    for j in jobs:
        t, c, u = j['title'].strip(), j['company'].strip(), j['url'].strip()
        if not t: continue
        if u:
            cur.execute("SELECT id FROM jobs WHERE url=?", (u,))
            if cur.fetchone(): continue
        cur.execute("SELECT id FROM jobs WHERE title=? AND company=?", (t, c))
        if cur.fetchone(): continue
        jid = str(uuid.uuid4())[:8]
        cur.execute("INSERT INTO jobs (id,source,source_id,title,company,url,location,date_found,fit_score,status,description) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (jid,'builtin',u[:200],t[:500],c[:300],u[:1000],j['location'][:200],NOW,55,'new',j['description'][:3000]))
        ins += 1
    conn.commit(); conn.close()
    return ins

if __name__ == '__main__':
    jobs = parse_md(MARKDOWN)
    log.info(f"Parsed {len(jobs)} BuiltIn dev-engineering jobs")
    ins = insert(jobs)
    log.info(f"Inserted {ins} new jobs")
