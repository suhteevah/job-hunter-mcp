#!/usr/bin/env python
"""
wraith_builtin_scrape.py
Parses BuiltIn jobs from pre-captured markdown extracts.
Run this after using Wraith to navigate to builtin.com and extract content.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import json
import uuid
import re
import logging
from datetime import datetime

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

# Markdown content from Wraith browse_extract on builtin.com/jobs/remote
# Jobs from page 1 (engineer search)
BUILTIN_MARKDOWN = """
 [Samsara](/company/samsara)
## [Sr. Security Engineer I - Enterprise Security](/job/sr-security-engineer-i-enterprise-security/8937925)
 **48 Minutes Ago** Remote or Hybrid Austin, TX, USA  135K-205K Annually Senior level The Senior Security Engineer I will build and maintain core security infrastructure, collaborate with global teams, mentor junior engineers, and drive security initiatives. Python Terraform Zscaler

 [Samsara](/company/samsara)
## [Senior Software Engineer, Growth](/job/senior-software-engineer-growth/8933312)
 **Yesterday** Remote or Hybrid United States  132K-222K Annually Senior level As a Senior Software Engineer in Growth, you'll drive revenue through technology. AWSJavaScriptPythonVue

 [Samsara](/company/samsara)
## [Field Sales Engineer II, Enterprise-Midwest/Northeast](/job/field-sales-engineer-ii-enterprise-midwest-northeast/8314578)
 **Reposted Yesterday** Remote or Hybrid United States  198K-233K Annually Senior level The Field Sales Engineer will modernize industries using IoT solutions.

 [Airwallex](/company/airwallex)
## [Staff Data Platform Engineer](/job/staff-data-platform-engineer/8937916)
 **48 Minutes Ago** Remote or Hybrid San Francisco, CA, USA Senior level Data platform strategy and AI infrastructure. Airflow BigQuery Databricks GCP Kafka MCP Spark

 [Airwallex](/company/airwallex)
## [Principal Architect, Data Knowledge Platform](/job/principal-architect-data-knowledge-platform-san-franciso/8937904)
 **49 Minutes Ago** Remote or Hybrid San Francisco, CA, USA Expert/Leader Designing data and knowledge layers for AI platform.

 [Applied Systems](/company/applied-systems)
## [Sr. Security Engineer](/job/sr-security-engineer/8937624)
 **An Hour Ago** Remote or Hybrid United States 90K-140K Annually Senior level Identify and mitigate security vulnerabilities. AnsiblePythonTerraformKubernetes

 [Applied Systems](/company/applied-systems)
## [Software Engineer](/job/software-engineer/8937623)
 **An Hour Ago** Remote or Hybrid United States 60K-120K Annually Junior level Develop and test enterprise software solutions. C# JavaScript TypeScript React

 [Possible Finance](/company/possible-finance)
## [Engineering Manager, App Ecosystem](/job/engineering-manager-app-ecosystem/8937586)
 **2 Hours Ago** Remote or Hybrid USA 198K-215K Annually Senior level Lead engineers to develop mobile platform and shared app experience. React Native

 [General Motors](/company/general-motors)
## [Senior Machine Learning Engineer](/job/senior-machine-learning-engineer/8937442)
 **2 Hours Ago** Remote or Hybrid United States 170K-240K Annually Senior level Design scalable AI/ML infrastructure, optimize model training performance. Python PyTorch TensorFlow GCP AWS Azure

 [General Motors](/company/general-motors)
## [Principal ML Tech Lead Manager - Embodied AI Onboard Autonomy](/job/principal-ai-ml-engineer/7590364)
 **Reposted 5 Hours Ago** Remote or Hybrid United States 296K-424K Annually Expert/Leader Lead end-to-end machine learning solutions for autonomous driving. Python PyTorch

 [Learneo](/company/learneo)
## [Senior Director of AI, R&D & Agentic Systems](/job/senior-director-ai-r-d-agentic-systems/8937284)
 **3 Hours Ago** Remote US 249K-421K Annually Senior level Lead QuillBot's agent-driven AI platform, overseeing AI R&D and Applied AI teams. Agentic Systems AI NLP

 [QuillBot](/company/quillbot)
## [Senior Director of AI, R&D & Agentic Systems](/job/senior-director-ai-r-d-agentic-systems/8937186)
 **3 Hours Ago** Remote US 249K-421K Annually Senior level Architecting QuillBot's AI systems, leading R&D and Applied AI teams. AI MLP NLP

 [CSC](/company/csc)
## [Director of Tax Accounting](/job/director-tax-accounting/8937378)
 **3 Hours Ago** In-Office or Remote Dover, DE, USA Senior level Tax accounting management and compliance.

 [Learneo](/company/learneo)
## [Growth Marketing & Brand Strategy Manager - Home Lending](/job/growth-marketing-brand-strategy-manager-home-lending/8937226)
 **3 Hours Ago** Remote or Hybrid United States Senior level Lead social selling strategy for Home Lending.

 [SoFi](/company/sofi)
## [Home Equity Closing Coordinator](/job/home-equity-closing-coordinator/8518630)
 **Reposted 5 Hours Ago** Remote or Hybrid United States Entry level Coordinate and schedule mortgage loan closings.

 [Samsara](/company/samsara)
## [Senior Software Engineer II - Mobile Platform](/job/senior-software-engineer-ii-mobile-platform/8935926)
 **Yesterday** Remote or Hybrid United States 155K-245K Annually Senior level Build and maintain mobile platform infrastructure. Swift Kotlin React Native

 [Samsara](/company/samsara)
## [Senior Software Engineer II - Machine Learning Platform](/job/senior-software-engineer-ii-machine-learning-platform/8935900)
 **Yesterday** Remote or Hybrid United States 155K-245K Annually Senior level ML platform development and infrastructure. Python PyTorch

 [Samsara](/company/samsara)
## [Senior Software Engineer II - Developer Platform](/job/senior-software-engineer-ii-developer-platform/8935915)
 **Yesterday** Remote or Hybrid United States 155K-245K Annually Senior level Build developer tools and platform capabilities. Python Go Kubernetes

 [Airwallex](/company/airwallex)
## [Backend Engineer, Risk & Compliance](/job/backend-engineer-risk-compliance/8937108)
 **An Hour Ago** Remote or Hybrid United States Senior level Backend systems for risk management. Python Go SQL

 [Airwallex](/company/airwallex)
## [Senior Data Engineer](/job/senior-data-engineer/8936842)
 **Yesterday** Remote or Hybrid United States Senior level Build and maintain data pipelines and infrastructure. Python SQL Spark Kafka BigQuery
"""

def parse_builtin_markdown(text):
    """Parse jobs from BuiltIn markdown extract."""
    jobs = []
    # Pattern: company then ## [Title](/job/slug/ID) then details
    lines = text.strip().split('\n')
    current_company = None

    for i, line in enumerate(lines):
        line = line.strip()

        # Company line: [Company](/company/slug)
        company_m = re.match(r'^\[([^\]]+)\]\(/company/[^\)]+\)\s*$', line)
        if company_m:
            current_company = company_m.group(1).strip()
            continue

        # Job title line: ## [Title](/job/slug/ID)
        job_m = re.match(r'^##\s+\[([^\]]+)\]\(/job/([^/\)]+)/(\d+)\)', line)
        if job_m:
            title = job_m.group(1).strip()
            slug = job_m.group(2).strip()
            job_id = job_m.group(3).strip()
            job_url = f"https://builtin.com/job/{slug}/{job_id}"

            # Look at next few lines for location and description
            context = ' '.join(lines[i+1:i+4]) if i+1 < len(lines) else ''

            if 'Remote' in context:
                loc = 'Remote'
            elif 'United States' in context or 'USA' in context:
                loc = 'United States'
            else:
                loc = 'Remote'

            # Extract description snippet
            desc_m = re.search(r'\d+\s+(?:level|Level)(.*?)(?:Top Skills:|$)', context, re.DOTALL)
            description = desc_m.group(1).strip() if desc_m else ''

            jobs.append({
                'title': title,
                'company': current_company or 'BuiltIn',
                'url': job_url,
                'location': loc,
                'source': 'builtin',
                'description': description[:2000],
            })

    return jobs

def insert_jobs(jobs):
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    cur = conn.cursor()
    inserted = 0
    for j in jobs:
        title = (j.get('title') or '').strip()
        company = (j.get('company') or '').strip()
        url = (j.get('url') or '').strip()
        if not title:
            continue
        if url:
            cur.execute("SELECT id FROM jobs WHERE url=?", (url,))
            if cur.fetchone():
                continue
        cur.execute("SELECT id FROM jobs WHERE title=? AND company=?", (title, company))
        if cur.fetchone():
            continue
        jid = str(uuid.uuid4())[:8]
        try:
            cur.execute("""
                INSERT INTO jobs (id, source, source_id, title, company, url, location, date_found, fit_score, status, description)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (jid, 'builtin', url[:200], title[:500], company[:300], url[:1000],
                  j.get('location','Remote')[:200], NOW, 55, 'new',
                  (j.get('description',''))[:3000]))
            inserted += 1
        except Exception as e:
            log.warning(f"Insert error: {e}")
    conn.commit()
    conn.close()
    return inserted

if __name__ == '__main__':
    jobs = parse_builtin_markdown(BUILTIN_MARKDOWN)
    log.info(f"Parsed {len(jobs)} jobs from BuiltIn")
    for j in jobs[:5]:
        log.info(f"  {j['title']} @ {j['company']} [{j['location']}]")
    ins = insert_jobs(jobs)
    log.info(f"Inserted {ins} new jobs from BuiltIn")
