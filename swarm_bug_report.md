# Swarm Application Bug Report

**Generated**: 2026-03-20 08:43:25 UTC
**Duration**: 13.2s
**Attempted**: 5 | **Success**: 5 | **Failed**: 0
**Skipped (not swarmable)**: 2283
**Total jobs audited**: 2288
**Success Rate (of attempted)**: 100.0%

## Overview by Platform

| Platform | Tier | Count | Status | Blocker |
|----------|------|-------|--------|----------|
| Ashby | api_native | 5 | 5 OK / 0 failed | None — fully automated |
| greenhouse_wrapped | wraith_redirect | 1110 | Skipped | WRAITH BUG: Company career site wrapping Greenhouse (gh_jid=7688069). Wraith nee... |
| greenhouse_direct | wraith_ready | 871 | Skipped | WRAITH TASK: Greenhouse forms are React SPAs but Wraith renders them. Needs sequ... |
| unknown (www.arbeitnow.com) | unknown | 77 | Skipped | WRAITH TASK: Unrecognized ATS at www.arbeitnow.com. Needs Wraith profiling: brow... |
| aggregator | skip | 63 | Skipped | SKIP: Job aggregator/scraper site — not the actual employer. These redirect to t... |
| lever | wraith_ready | 33 | Skipped | WRAITH TASK: Lever forms are server-rendered HTML — Wraith CAN render these. Nee... |
| unknown (hiredock.kesug.com) | unknown | 20 | Skipped | WRAITH TASK: Unrecognized ATS at hiredock.kesug.com. Needs Wraith profiling: bro... |
| indeed | wraith_investigation | 10 | Skipped | WRAITH BUG: Indeed uses CloudFlare bot protection + reCAPTCHA v3. Direct Indeed ... |
| linkedin | manual_only | 10 | Skipped | WRAITH BUG: LinkedIn has aggressive anti-bot detection: CAPTCHA challenges, sess... |
| unknown () | unknown | 8 | Skipped | WRAITH TASK: Unrecognized ATS at . Needs Wraith profiling: browse_navigate to UR... |
| unknown (jobgether.com) | unknown | 7 | Skipped | WRAITH TASK: Unrecognized ATS at jobgether.com. Needs Wraith profiling: browse_n... |
| unknown (www.remoterocketship.com) | unknown | 6 | Skipped | WRAITH TASK: Unrecognized ATS at www.remoterocketship.com. Needs Wraith profilin... |
| unknown (www.jobleads.com) | unknown | 6 | Skipped | WRAITH TASK: Unrecognized ATS at www.jobleads.com. Needs Wraith profiling: brows... |
| unknown (www.adzuna.com) | unknown | 5 | Skipped | WRAITH TASK: Unrecognized ATS at www.adzuna.com. Needs Wraith profiling: browse_... |
| upwork | manual_only | 5 | Skipped | MANUAL: Upwork requires authenticated session with 2FA. Proposals require custom... |
| unknown (lensa.com) | unknown | 4 | Skipped | WRAITH TASK: Unrecognized ATS at lensa.com. Needs Wraith profiling: browse_navig... |
| unknown (dailyremote.com) | unknown | 4 | Skipped | WRAITH TASK: Unrecognized ATS at dailyremote.com. Needs Wraith profiling: browse... |
| unknown (www.dice.com) | unknown | 3 | Skipped | WRAITH TASK: Unrecognized ATS at www.dice.com. Needs Wraith profiling: browse_na... |
| unknown (jooble.org) | unknown | 3 | Skipped | WRAITH TASK: Unrecognized ATS at jooble.org. Needs Wraith profiling: browse_navi... |
| unknown (www.jobease.ca) | unknown | 3 | Skipped | WRAITH TASK: Unrecognized ATS at www.jobease.ca. Needs Wraith profiling: browse_... |
| unknown (jobright.ai) | unknown | 3 | Skipped | WRAITH TASK: Unrecognized ATS at jobright.ai. Needs Wraith profiling: browse_nav... |
| unknown (remote.co) | unknown | 3 | Skipped | WRAITH TASK: Unrecognized ATS at remote.co. Needs Wraith profiling: browse_navig... |
| unknown (www.glassdoor.com) | unknown | 2 | Skipped | WRAITH TASK: Unrecognized ATS at www.glassdoor.com. Needs Wraith profiling: brow... |
| unknown (www.recruit.net) | unknown | 2 | Skipped | WRAITH TASK: Unrecognized ATS at www.recruit.net. Needs Wraith profiling: browse... |
| unknown (www.talent.com) | unknown | 2 | Skipped | WRAITH TASK: Unrecognized ATS at www.talent.com. Needs Wraith profiling: browse_... |
| unknown (www.virtualvocations.com) | unknown | 2 | Skipped | WRAITH TASK: Unrecognized ATS at www.virtualvocations.com. Needs Wraith profilin... |
| cybercoders | wraith_ready | 1 | Skipped | WRAITH TASK: CyberCoders serves standard HTML forms. Wraith should render them. ... |
| unknown (himalayas.app) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at himalayas.app. Needs Wraith profiling: browse_n... |
| unknown (up2staff.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at up2staff.com. Needs Wraith profiling: browse_na... |
| unknown (jobs.energyimpactpartners.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at jobs.energyimpactpartners.com. Needs Wraith pro... |
| unknown (firstadvantage.applytojob.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at firstadvantage.applytojob.com. Needs Wraith pro... |
| unknown (careers.marriott.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at careers.marriott.com. Needs Wraith profiling: b... |
| unknown (career.io) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at career.io. Needs Wraith profiling: browse_navig... |
| unknown (bebee.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at bebee.com. Needs Wraith profiling: browse_navig... |
| unknown (careers.cognizant.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at careers.cognizant.com. Needs Wraith profiling: ... |
| unknown (www.synchronycareers.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.synchronycareers.com. Needs Wraith profilin... |
| unknown (www.builtinsf.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.builtinsf.com. Needs Wraith profiling: brow... |
| unknown (www.remotejobs.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.remotejobs.com. Needs Wraith profiling: bro... |
| unknown (noma.security) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at noma.security. Needs Wraith profiling: browse_n... |
| unknown (www.toptal.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.toptal.com. Needs Wraith profiling: browse_... |
| unknown (nofluffjobs.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at nofluffjobs.com. Needs Wraith profiling: browse... |
| unknown (careers.pantomath.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at careers.pantomath.com. Needs Wraith profiling: ... |
| unknown (careers.t-mobile.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at careers.t-mobile.com. Needs Wraith profiling: b... |
| unknown (www.upwind.io) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.upwind.io. Needs Wraith profiling: browse_n... |
| unknown (www.learn4good.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.learn4good.com. Needs Wraith profiling: bro... |
| unknown (builtin.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at builtin.com. Needs Wraith profiling: browse_nav... |
| unknown (www.remotenomadjobs.com) | unknown | 1 | Skipped | WRAITH TASK: Unrecognized ATS at www.remotenomadjobs.com. Needs Wraith profiling... |

---

## Non-Swarmable Jobs — What's Wrong & How to Fix

### Wraith-Ready (Can automate now, needs session) (905 jobs)

**greenhouse_direct** (871 jobs)

> **What's wrong**: WRAITH TASK: Greenhouse forms are React SPAs but Wraith renders them. Needs sequential browser session — browse_navigate → browse_snapshot → browse_fill → browse_upload_file → browse_click. Playbook at playbooks/greenhouse.md.
>
> **How to fix**: Wraith: browse_navigate → snapshot → fill per greenhouse playbook → submit

- Remote People — Senior AI Engineer
  `https://job-boards.eu.greenhouse.io/remotepeople/jobs/4721961101`
- WITHIN — AI Engineer
  `https://job-boards.greenhouse.io/agencywithin/jobs/5056863007`
- Reddit — Staff Software Engineer, Ads API
  `https://job-boards.greenhouse.io/reddit/jobs/7167632`
- ZipRecruiter — Senior Software Engineer, Machine Learning
  `https://job-boards.greenhouse.io/ziprecruiter/jobs/5167472`
- ZipRecruiter — Staff Software Engineer, Machine Learning
  `https://job-boards.greenhouse.io/ziprecruiter/jobs/5167480`
- *... and 866 more*

**lever** (33 jobs)

> **What's wrong**: WRAITH TASK: Lever forms are server-rendered HTML — Wraith CAN render these. Needs sequential browse_navigate → browse_fill → browse_upload_file → browse_click. No captcha. Playbook exists at playbooks/lever.md.
>
> **How to fix**: Wraith: browse_navigate(url+'/apply') → fill per lever playbook → submit

- Plaid — Senior Software Engineer - Data Infrastructure
  `https://jobs.lever.co/plaid/05b0ae3f-ec60-48d6-ae27-1bd89d928c47`
- Plaid — Senior Software Engineer - Fullstack
  `https://jobs.lever.co/plaid/28bad806-9938-48eb-b643-2720605cd965`
- Plaid — Senior Software Engineer - ML Infrastructure
  `https://jobs.lever.co/plaid/16383203-9942-42be-9698-76207e2a500e`
- Plaid — Engineering Manager - Machine Learning Infrastructure
  `https://jobs.lever.co/plaid/cdc5447e-b4c5-49f4-807a-f95656e2f1ce`
- Plaid — Senior Data Engineer - Data Engineering
  `https://jobs.lever.co/plaid/022278b3-0943-44b3-a54b-1de421017589`
- *... and 28 more*

**cybercoders** (1 jobs)

> **What's wrong**: WRAITH TASK: CyberCoders serves standard HTML forms. Wraith should render them. Needs profiling: browse_navigate → browse_snapshot to verify form structure.
>
> **How to fix**: Wraith: profile then fill standard HTML form

- CyberCoders — AI Infrastructure System Administrator
  `https://www.cybercoders.com/job-detail/931706?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=org`

### Wraith Redirect (Needs redirect/iframe handling — WRAITH BUG) (1110 jobs)

**greenhouse_wrapped** (1110 jobs)

> **What's wrong**: WRAITH BUG: Company career site wrapping Greenhouse (gh_jid=7688069). Wraith needs to follow redirect chain from company URL to find the actual Greenhouse form. May render as iframe (Wraith can't enter iframes) or redirect to greenhouse.io (Wraith can handle). Needs: 1) browse_navigate to company URL, 2) detect redirect vs iframe, 3) if redirect → fill Greenhouse form, 4) if iframe → BLOCKED (Wraith iframe support needed).
>
> **How to fix**: Wraith: navigate → detect redirect/iframe → fill if accessible

- Stripe — Senior Staff Product Designer, Agentic Commerce
  `https://stripe.com/jobs/search?gh_jid=7688069`
- Samsara — Senior Software Engineer, AI Platform
  `https://www.samsara.com/company/careers/roles/7266719?gh_jid=7266719`
- Samsara — Senior Software Engineer I - Agent Foundations
  `https://www.samsara.com/company/careers/roles/7356410?gh_jid=7356410`
- Samsara — Senior Software Engineer - Safety - GenAI 
  `https://www.samsara.com/company/careers/roles/7266483?gh_jid=7266483`
- Datadog — Staff AI Engineer - MCP Services
  `https://careers.datadoghq.com/detail/7627410/?gh_jid=7627410`
- *... and 1105 more*

### Wraith Investigation (May work after redirect) (10 jobs)

**indeed** (10 jobs)

> **What's wrong**: WRAITH BUG: Indeed uses CloudFlare bot protection + reCAPTCHA v3. Direct Indeed apps require login (2FA). However, many Indeed listings redirect to company ATS (Greenhouse, Lever, etc.) — Wraith should follow the redirect and apply at the destination. Needs: 1) browse_navigate to Indeed URL, 2) detect if it redirects to external ATS, 3) if redirect → re-classify destination URL and apply there, 4) if direct Indeed → BLOCKED (captcha).
>
> **How to fix**: Wraith: navigate → follow redirect → apply at destination ATS

- Living Talent — Solutions Architect – K8s – AI Infrastructure Orchestration – REMOTE
  `https://www.indeed.com/viewjob?jk=c4a01f63a743e447&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_mediu`
- Goldstone Partners, Inc. — DevOps Platform Engineer – US Remote
  `https://www.indeed.com/viewjob?jk=465c9fe48dc758b6&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_mediu`
- 444LOVES, LLC — Technology Sales Advisor (1099 Contract) B2B AI/Managed Service Provider Technology
  `https://www.indeed.com/viewjob?jk=9b94db24df6988ca&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_mediu`
- Living Talent — Solutions Engineer – K8s Support – Customer 1st – REMOTE
  `https://www.indeed.com/viewjob?jk=4a6fa9003069ab57&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_mediu`
- Peraton — AWS CLOUD SITE RELIABILITY ENGINEER (SRE)
  `https://www.indeed.com/viewjob?jk=5da647d91f7137f6&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_mediu`
- *... and 5 more*

### Manual Only (Anti-Bot/Auth/ToS Barriers) (15 jobs)

**linkedin** (10 jobs)

> **What's wrong**: WRAITH BUG: LinkedIn has aggressive anti-bot detection: CAPTCHA challenges, session fingerprinting, rate limiting by IP. Easy Apply requires authenticated session + CSRF tokens. Wraith needs: 1) Cookie import from real browser session (browse_cookie_import or similar), 2) LinkedIn-specific fingerprint profile to avoid detection, 3) CSRF token extraction from page. Even with these, LinkedIn blocks after 2-3 automated attempts per IP.
>
> **How to fix**: Wraith with session cookies + stealth profile (not built)

- V-Soft Consulting Group, Inc. — UKG/KRONOS QA(Quality Assurance)/Testers - Remote
  `https://www.linkedin.com/jobs/view/ukg-kronos-qa-quality-assurance-testers-remote-at-v-soft-consulting-group-inc-4385291`
- Komforce — E2E Telco QA Test Engineer
  `https://www.linkedin.com/jobs/view/e2e-telco-qa-test-engineer-at-komforce-4385915791?utm_campaign=google_jobs_apply&utm_`
- Alluvial Concepts — Software Automation Test Engineer (Remote)
  `https://www.linkedin.com/jobs/view/software-automation-test-engineer-remote-at-alluvial-concepts-4372544513?utm_campaign`
- Jobs via Dice — REMOTE Senior Enterprise Infrastructure Engineer-
  `https://www.linkedin.com/jobs/view/remote-senior-enterprise-infrastructure-engineer-at-jobs-via-dice-4385927552?utm_camp`
- Commercient — AI SaaS Account Executive (B2B Sales, Remote/Hybrid)
  `https://www.linkedin.com/jobs/view/ai-saas-account-executive-b2b-sales-remote-hybrid-at-commercient-4384341469?utm_campa`
- *... and 5 more*

**upwork** (5 jobs)

> **What's wrong**: MANUAL: Upwork requires authenticated session with 2FA. Proposals require custom cover letters + bid amounts. ToS prohibits automated applications. No Wraith workaround.
>
> **How to fix**: Manual application only — ToS prohibits automation

- Upwork — Full-Cycle B2B Sales Executive (Custom AI Solutions) - 20% Commission Bonus Model
  `https://www.upwork.com/freelance-jobs/apply/Full-Cycle-B2B-Sales-Executive-Custom-Solutions-Commission-Bonus-Model_~0220`
- Upwork — Prompt Engineer + SEO Content Systems (Fix AI Template for Scalable Pages)
  `https://www.upwork.com/freelance-jobs/apply/Prompt-Engineer-SEO-Content-Systems-Fix-Template-for-Scalable-Pages_~0220338`
- Upwork — Claude API Setup & Hello World - Quick Task (1-2 Hours) - Contract to Hire
  `https://www.upwork.com/freelance-jobs/apply/Claude-API-Setup-Hello-World-Quick-Task-Hours_~022033176566287116176/?utm_ca`
- Upwork — B2B Sales Closer (Productized AI Services) - 20% Commission Per Close
  `https://www.upwork.com/freelance-jobs/apply/B2B-Sales-Closer-Productized-Services-Commission-Per-Close_~0220337042691492`
- Upwork — AWS Cloud Architect – Secure AI Infrastructure (8 Week Project)
  `https://www.upwork.com/freelance-jobs/apply/AWS-Cloud-Architect-Secure-Infrastructure-Week-Project_~02203358256191726991`

### Skip (Aggregator/Scraper Sites) (63 jobs)

**aggregator** (63 jobs)

> **What's wrong**: SKIP: Job aggregator/scraper site — not the actual employer. These redirect to the real ATS. Should extract destination URL and re-classify.
>
> **How to fix**: Extract destination URL via Wraith browse_navigate → follow redirect

- Twilio — Staff Software Engineer - LLM / AI Agents
  `https://www.tealhq.com/job/staff-software-engineer-llm-ai-agents_7ea1ad725fba10e2eef080259fe4ea78b89a0?utm_campaign=goog`
- Flexionis — Remote Quality Assurance Engineer – Advanced Software Testing & Automation Specialist for Costco Travel IT (Work‑From‑Home, $32/hr)
  `https://flexionis.wuaze.com/job/remote-quality-assurance-engineer-advanced-software-testing-automation-specialist-for-co`
- Flexionis — [Remote] Senior Cloud Solutions Engineer – AI & Google Cloud
  `https://flexionis.wuaze.com/job/remote-senior-cloud-solutions-engineer-ai-google-cloud?utm_campaign=google_jobs_apply&ut`
- Flexionis — Senior QA Engineer - Remote US
  `https://flexionis.wuaze.com/job/senior-qa-engineer-remote-us?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply`
- Flexionis — Remote Lead Infrastructure Engineer
  `https://flexionis.wuaze.com/job/remote-lead-infrastructure-engineer-2?utm_campaign=google_jobs_apply&utm_source=google_j`
- *... and 58 more*

### Unknown ATS (Needs Wraith Profiling) (180 jobs)

**unknown (www.arbeitnow.com)** (77 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.arbeitnow.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- TripleTen — AI Strategy Advisor for Business Programs (B2B)
  `https://www.arbeitnow.com/jobs/companies/tripleten/remote-ai-strategy-advisor-for-business-programs-b2b-berlin-266145`
- neoBIM GmbH — Working Student: LCA & Sustainability in BIM (m/f/d)
  `https://www.arbeitnow.com/jobs/companies/neobim-gmbh/working-student-lca-sustainability-in-bim-karlsruhe-69935`
- TripleTen — AI Solution Architect   (Educational content author)
  `https://www.arbeitnow.com/jobs/companies/tripleten/remote-ai-solution-architect-educational-content-author-berlin-26927`
- Caona Health — Senior Freelance Engineer (Mobile + Backend)
  `https://www.arbeitnow.com/jobs/companies/caona-health/senior-freelance-engineer-mobile-backend-viersen-175269`
- neoBIM GmbH — Senior LCA & Sustainability Specialist in BIM (m/f/d)
  `https://www.arbeitnow.com/jobs/companies/neobim-gmbh/senior-lca-sustainability-specialist-in-bim-karlsruhe-194721`
- *... and 72 more*

**unknown (hiredock.kesug.com)** (20 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at hiredock.kesug.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Hiredock — Infrastructure Engineer (Mid-level, Senior, or Staff) (Remote)
  `https://hiredock.kesug.com/job/infrastructure-engineer-mid-level-senior-or-staff-remote?utm_campaign=google_jobs_apply&u`
- Hiredock — Remote Software Engineer, DevOps
  `https://hiredock.kesug.com/job/remote-software-engineer-devops?utm_campaign=google_jobs_apply&utm_source=google_jobs_app`
- Hiredock — Jr. Test Automation Engineer (Remote Opportunity)
  `https://hiredock.kesug.com/job/jr-test-automation-engineer-remote-opportunity?utm_campaign=google_jobs_apply&utm_source=`
- Hiredock — Junior Azure/DevOps Engineer – 100% Remote
  `https://hiredock.kesug.com/job/junior-azure-devops-engineer-100-remote?utm_campaign=google_jobs_apply&utm_source=google_`
- Hiredock — W2 Only _ Infrastructure Engineer (Nutanix) _ Remote .
  `https://hiredock.kesug.com/job/w2-only-_-infrastructure-engineer-nutanix-_-remote?utm_campaign=google_jobs_apply&utm_sou`
- *... and 15 more*

**unknown ()** (8 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at . Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- unknown — click here
  `/search?q=site:jobs.lever.co+%22AI+engineer%22+remote&sca_esv=880bc3402c9aa32e&emsg=SG_REL&sei=BGm7adDkH-vPxc8Px-fHoQk`
- unknown — click here
  `/search?q=site:jobs.lever.co+%22software+engineer%22+remote&sca_esv=880bc3402c9aa32e&emsg=SG_REL&sei=BWm7aa7MC6Gtxc8P48G`
- unknown — click here
  `/search?q=site:jobs.lever.co+%22backend+engineer%22+remote&sca_esv=880bc3402c9aa32e&emsg=SG_REL&sei=Bmm7afXlA5-Fxc8Pl6fq`
- unknown — click here
  `/search?q=site:jobs.lever.co+%22Python+developer%22+remote&sca_esv=880bc3402c9aa32e&emsg=SG_REL&sei=CGm7aauEGKuIxc8Ph-Te`
- unknown — click here
  `/search?q=site:jobs.lever.co+%22AI+engineer%22+remote&sca_esv=880bc3402c9aa32e&emsg=SG_REL&sei=LWm7aYDZENT05OUP9_OtgAs`
- *... and 3 more*

**unknown (jobgether.com)** (7 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at jobgether.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Upwind Security — Pre-Sales Engineer (Dubai, UAE - Remote)
  `https://jobgether.com/offer/69b09ba024d79271ee01addd-pre-sales-engineer-dubai-uae---remote?utm_campaign=google_jobs_appl`
- Nebius Group — Network Site Reliability Engineer (NetSRE)
  `https://jobgether.com/offer/69b965af24d79271ee0951b3-network-site-reliability-engineer-netsre?utm_campaign=google_jobs_a`
- tax.com — Sales Engineer, Platform (Remote)
  `https://jobgether.com/offer/69b2175024d79271ee039696-sales-engineer-platform-remote?utm_campaign=google_jobs_apply&utm_s`
- Mirantis — Technical Account Manager (Technical Service Delivery, OpenStack) - remote in the US
  `https://jobgether.com/offer/69b457d824d79271ee065e79-technical-account-manager-technical-service-delivery-openstack---re`
- Vulnerability Check LLC — Head of Technical Account Managers (Austin, TX - Remote)
  `https://jobgether.com/offer/69b2ce2624d79271ee046c15-head-of-technical-account-managers-austin-tx---remote?utm_campaign=`
- *... and 2 more*

**unknown (www.remoterocketship.com)** (6 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.remoterocketship.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Intus Care — Tech Lead, SDET
  `https://www.remoterocketship.com/us/company/intuscare/jobs/tech-lead-sdet-united-states-remote/?utm_campaign=google_jobs`
- Neo4j — Solutions Engineer, US Startup Program
  `https://www.remoterocketship.com/us/company/neo4j/jobs/solutions-engineer-us-startup-program-united-states-remote/?utm_c`
- Braintrust — Solutions Engineer – Central Region
  `https://www.remoterocketship.com/us/company/usebraintrust/jobs/solutions-engineer-central-region-united-states-remote/?u`
- VulnCheck — Head of Technical Account Managers
  `https://www.remoterocketship.com/company/vulncheck/jobs/head-of-technical-account-managers-united-states-remote/?utm_cam`
- Hytera US Inc. — Sales Engineer – PoC Focus
  `https://www.remoterocketship.com/us/company/hytera-us-inc-us/jobs/sales-engineer-poc-focus-united-states-remote/?utm_cam`
- *... and 1 more*

**unknown (www.jobleads.com)** (6 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.jobleads.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Jobs via Dice — Remote QA Engineer: Manual & Automation Testing
  `https://www.jobleads.com/us/job/remote-qa-engineer-manual-automation-testing--united-states--eb7eab365ca4fbfba5f9e6edcfe`
- Mesh Systems — Remote QA Engineer - Azure IoT & Cloud Testing
  `https://www.jobleads.com/us/job/remote-qa-engineer-azure-iot-cloud-testing--united-states--eac8f3e479792fe31c39c4f5413bb`
- Jobot — Senior SDET (playwright / ruby)
  `https://www.jobleads.com/us/job/senior-sdet-playwright-ruby--baltimore--ec771a5a4bb7bac02a6bdae1af2d5af8e?utm_campaign=g`
- Gatekeeper Systems, Inc. — Remote B2B Growth Leader — Retail Tech & Loss Prevention
  `https://www.jobleads.com/us/job/remote-b2b-growth-leader-retail-tech-loss-prevention--united-states--e3535714bf7ef0b06d2`
- EngFlow GmbH — Remote Sales Engineer: Build Systems & Cloud
  `https://www.jobleads.com/us/job/remote-sales-engineer-build-systems-cloud--san-francisco--ea7661377c7d5a85d897d05a45bb0e`
- *... and 1 more*

**unknown (www.adzuna.com)** (5 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.adzuna.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Medium — ML Engineer: NLP, RAG & LLM Modeling
  `https://www.adzuna.com/details/5669675879?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic`
- Spotify — ML Engineer – LLM Storytelling & Personalization
  `https://www.adzuna.com/details/5669674032?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic`
- Samsara — Remote Senior PM, Sales Engineering (New Products)
  `https://www.adzuna.com/details/5670266184?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic`
- Florvets Structures — Cloud Infrastructure Engineer - Remote & Flexible Hours
  `https://www.adzuna.com/details/5670292704?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic`
- Veeva Systems — Senior SRE, Vault Platform — Remote/Work Anywhere
  `https://www.adzuna.com/details/5670259783?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic`

**unknown (lensa.com)** (4 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at lensa.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Maintec Technologies — TOSCA Automation @ Remote - GC / USC only - Contract
  `https://lensa.com/job-v1/maintec-technologies/remote/automation-tester/0524bd63b1486ab7184ee38e29bb9530?utm_campaign=goo`
- Lorven Technologies — Sr AI Platform Engineer AI Platform Engineer - Charlotte, NC (Hybrid)
  `https://lensa.com/job-v1/lorven-technologies/remote/senior-platform-engineer/063f130a96225088636f2b4d07a659b1?utm_campai`
- Savant Financial Technologies — Sr. Staff Site Reliability (SRE)/DevOps Engineer (Remote)
  `https://lensa.com/job-v1/savant-financial-technologies/remote/senior-site-reliability-engineer/416a8775e193949c8c5f083ac`
- Nile Global Inc — Solutions Engineer- Central/East Coast Regions
  `https://lensa.com/job-v1/nile-global-inc/remote/solutions-engineer/1c35fdd69242b5a2e793f592bab3e1b1?utm_campaign=google_`

**unknown (dailyremote.com)** (4 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at dailyremote.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Welocalize — Project Lion - Lead Prompt Engineer - United States (Remote, Part-Time)
  `https://dailyremote.com/remote-job/project-lion-lead-prompt-engineer-united-states-remote-part-time-4745775?utm_campaign`
- TradeStation — Principal SDET Brokerage Services
  `https://dailyremote.com/remote-job/principal-sdet-brokerage-services-4725310?utm_campaign=google_jobs_apply&utm_source=g`
- Procore Technologies — Commercial Solutions Engineer, Owners (Remote)
  `https://dailyremote.com/remote-job/commercial-solutions-engineer-owners-remote-4715720?utm_campaign=google_jobs_apply&ut`
- Point of Rental Software — Support Solutions Engineer
  `https://dailyremote.com/remote-job/support-solutions-engineer-4719883?utm_campaign=google_jobs_apply&utm_source=google_j`

**unknown (www.dice.com)** (3 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.dice.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Highbrow Technology Inc — AWS Cloud Consultant (Data & AI Infrastructure)
  `https://www.dice.com/job-detail/9322608c-1c2d-46c3-b0c9-c20744f7ce23?utm_campaign=google_jobs_apply&utm_source=google_jo`
- Photon — SRE+Dynatrace - Guadalajara, MX
  `https://www.dice.com/job-detail/b40d19e2-a44c-4c1e-a8aa-4ffbeaf978a4?utm_campaign=google_jobs_apply&utm_source=google_jo`
- West Coast Consulting LLC — Senior Software Engineer - Platform / AI Infrastructure
  `https://www.dice.com/job-detail/d1256c62-8ad4-4009-95d6-e89a54254c8a?utm_campaign=google_jobs_apply&utm_source=google_jo`

**unknown (jooble.org)** (3 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at jooble.org. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Solar Works Energy — Remote AI Automation Engineer (Junior-Mid) Build & Scale
  `https://jooble.org/jdp/8458081000150110802?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organi`
- Motion Recruitment Partners LLC — Senior Platform Engineer - Remote & SRE Focus
  `https://jooble.org/jdp/-3459591067402946984?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organ`
- Schröder Sales Solutions GmbH — Remote B2B SaaS Sales Leader — Real Impact
  `https://jooble.org/jdp/8923493006654060652?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organi`

**unknown (www.jobease.ca)** (3 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.jobease.ca. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Various Employers — Remote DevOps Engineer
  `https://www.jobease.ca/remote-jobs/job/devops-engineer/?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_`
- Various Employers — Remote QA Engineer
  `https://www.jobease.ca/remote-jobs/job/qa-engineer/?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medi`
- Various Employers — Remote Platform Engineer
  `https://www.jobease.ca/remote-jobs/job/platform-engineer/?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&ut`

**unknown (jobright.ai)** (3 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at jobright.ai. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Ashby — [Remote] Staff Platform Engineer, Americas
  `https://jobright.ai/jobs/info/6928e7e591ceeb2e8a546946?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_m`
- Crossing Hurdles — [Remote] Prompt Engineer (Chinese) | $43/hr Remote
  `https://jobright.ai/jobs/info/699ada3be0bddb6acaca0158?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_m`
- GRUNDFOS — [Remote] Technical Key Account Manager-Industry East
  `https://jobright.ai/jobs/info/6996bc92e0bddb6acac55e5e?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_m`

**unknown (remote.co)** (3 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at remote.co. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Altana AI — Technical Account Manager, Enterprise job at Altana AI in Brooklyn, NY
  `https://remote.co/job-details/technical-account-manager-enterprise-440323d9-d91c-44ec-b06e-465bfe209d4b?utm_campaign=goo`
- SpyCloud — Sales Engineer - Strategic Accounts job at SpyCloud in US National
  `https://remote.co/job-details/sales-engineer-strategic-accounts-d38d441c-5275-45af-876a-2da9ede77169?utm_campaign=google`
- American Century Investments — Artificial Intelligence Platform Engineer - Senior Specialist job at American Century Investments in Kansas City, MO
  `https://remote.co/job-details/artificial-intelligence-platform-engineer-senior-specialist-1d18973c-358d-4097-8af9-2c39c0`

**unknown (www.glassdoor.com)** (2 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.glassdoor.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Velocity, AI Automation Solutions — AI Automation Sales Consultant (High Commission B2B Sales)
  `https://www.glassdoor.com/job-listing/ai-automation-sales-consultant-high-commission-b2b-sales-velocity-ai-automation-so`
- Rula — Staff Software Engineer - Platform (Remote)
  `https://www.glassdoor.com/job-listing/staff-software-engineer-platform-remote-rula-JV_IC1146821_KO0,39_KE40,44.htm?jl=10`

**unknown (www.recruit.net)** (2 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.recruit.net. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- HumanIT Digital Consulting — QA Engineer - Full Remote Portugal
  `https://www.recruit.net/job/qa-engineer-full-portugal-jobs/5E099F15616076B5?utm_campaign=google_jobs_apply&utm_source=go`
- Grafana Labs — Senior Solutions Engineer | Mid Atlantic or Southeast | RemoteUnited States (Remote)
  `https://www.recruit.net/job/solutions-engineer-mid-atlantic-southeast-jobs/8F8C671CE3781EA2?utm_campaign=google_jobs_app`

**unknown (www.talent.com)** (2 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.talent.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- ECP — Remote SDET: Build Robust Test Frameworks & QA Excellence
  `https://www.talent.com/view?id=611146137705651398&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium`
- Axon — Remote Enterprise Sales Engineer — Strategic Tech Leader
  `https://www.talent.com/view?id=611146437112768463&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium`

**unknown (www.virtualvocations.com)** (2 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.virtualvocations.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Kyndryl Inc. — Lead QA Software Engineer
  `https://www.virtualvocations.com/job/lead-qa-software-engineer-2959030-i.html?utm_campaign=google_jobs_apply&utm_source=`
- Avaya LLC — Site Reliability Engineer SRE
  `https://www.virtualvocations.com/job/site-reliability-engineer-sre-1031096.html?utm_campaign=google_jobs_apply&utm_sourc`

**unknown (himalayas.app)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at himalayas.app. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Fundraise Up — Senior Solutions Engineer, Enterprise & Strategic, USA, Remote
  `https://himalayas.app/companies/fundraise-up/jobs/senior-solutions-engineer-enterprise-strategic-usa-remote?utm_campaign`

**unknown (up2staff.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at up2staff.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- CI&T — [Job- 28148] Site Reliability Engineer (SRE) Mid-Level / Senior, Portugal – Portugal
  `https://up2staff.com/job-28148-site-reliability-engineer-sre-portugal-at-cit?utm_campaign=google_jobs_apply&utm_source=g`

**unknown (jobs.energyimpactpartners.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at jobs.energyimpactpartners.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Swimlane — Associate SDET
  `https://jobs.energyimpactpartners.com/companies/swimlane-2/jobs/70582544-associate-sdet?utm_campaign=google_jobs_apply&u`

**unknown (firstadvantage.applytojob.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at firstadvantage.applytojob.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- First Advantage — SRE Lead (US Remote)
  `https://firstadvantage.applytojob.com/apply/OWemc1pHsH/SRE-Lead-US-Remote?utm_campaign=google_jobs_apply&utm_source=goog`

**unknown (careers.marriott.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at careers.marriott.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Marriott International, Inc — FLEX Salesforce Senior Platform Engineer
  `https://careers.marriott.com/flex-salesforce-senior-platform-engineer/job/C1228C506982C4618F80C653450BF298?utm_campaign=`

**unknown (career.io)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at career.io. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Trend Micro — Sr. Solutions Engineer (Field) – US Remote, Boston
  `https://career.io/job/remote-sr-solutions-engineer-field-us-trend-micro-7e42871a0ced87084a3fb5a23d0fcd77?utm_campaign=go`

**unknown (bebee.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at bebee.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Welocalize — Project Lion - Prompt Engineer - United States (Remote, Part-Time)
  `https://bebee.com/us/jobs/project-lion-prompt-engineer-united-states-remote-part-time-welocalize--fj-2062019605?utm_camp`

**unknown (careers.cognizant.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at careers.cognizant.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Cognizant — DevOps Engineer with OCI   - Remote
  `https://careers.cognizant.com/global-en/jobs/00068110691/devops-engineer-with-oci-remote/?utm_campaign=google_jobs_apply`

**unknown (www.synchronycareers.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.synchronycareers.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Synchrony Financial — Mobile Apps Test Automation Engineer
  `https://www.synchronycareers.com/job-detail/23149112/mobile-apps-test-automation-engineer-remote/?utm_campaign=google_jo`

**unknown (www.builtinsf.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.builtinsf.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- HomeVision — Site Reliability Engineer - US - Remote
  `https://www.builtinsf.com/job/site-reliability-engineer-us-remote/7132666?utm_campaign=google_jobs_apply&utm_source=goog`

**unknown (www.remotejobs.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.remotejobs.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- TMS — Urgent Need – SAP Infrastructure Engineering | Remote | 12+ Years Exp
  `https://www.remotejobs.com/jobs/urgent-need-sap-infrastructure-engineering-remote-12-years-exp-a8657bdd?utm_campaign=goo`

**unknown (noma.security)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at noma.security. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Noma Security — Senior Technical Account Manager
  `https://noma.security/careers/co/usa/8A.D58/senior-technical-account-manager/all/?utm_campaign=google_jobs_apply&utm_sou`

**unknown (www.toptal.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.toptal.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Toptal — Remote DevOps Engineer Job for International Agency (Full-time)
  `https://www.toptal.com/freelance-jobs/developers/aws/remote-devops-engineer-job-for-international-agency-full-time-18?ut`

**unknown (nofluffjobs.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at nofluffjobs.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Link Group — Automation Engineer – Agentic Workflows
  `https://nofluffjobs.com/hu/job/automation-engineer-agentic-workflows-link-group-remote?utm_campaign=google_jobs_apply&ut`

**unknown (careers.pantomath.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at careers.pantomath.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Pantomath — Sr. Site Reliability Engineer
  `https://careers.pantomath.com/jobs/569704-sr-site-reliability-engineer?utm_campaign=google_jobs_apply&utm_source=google_`

**unknown (careers.t-mobile.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at careers.t-mobile.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- TMobile — Sr. Solutions Engineer - Mid-Market | Houston | Austin
  `https://careers.t-mobile.com/sr-solutions-engineer-mid-market-houston-austin/job/1C3F9BE067FCF16FE72C2D88DEEED6B2?utm_ca`

**unknown (www.upwind.io)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.upwind.io. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Upwind Security — Technical Account Manager (US Remote)
  `https://www.upwind.io/careers/co/us-remote/CE.659/technical-account-manager-us-remote/all?utm_campaign=google_jobs_apply`

**unknown (www.learn4good.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.learn4good.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- ConsultNet Technology Services and Solutions — SDET: Hybrid​/Remote - Automated Tests Autonomy
  `https://www.learn4good.com/jobs/online_remote/info_technology/4910617368/e/?utm_campaign=google_jobs_apply&utm_source=go`

**unknown (builtin.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at builtin.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Genius Agency AI — B2B Closer - Remote
  `https://builtin.com/job/b2b-closer-remote/8295912?utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium`

**unknown (www.remotenomadjobs.com)** (1 jobs)

> **What's wrong**: WRAITH TASK: Unrecognized ATS at www.remotenomadjobs.com. Needs Wraith profiling: browse_navigate to URL, browse_snapshot to check if form is present, determine if standard HTML or SPA.
>
> **How to fix**: Wraith: browse_navigate → browse_snapshot → classify

- Saviynt — Identity Security - Technical Account Manager - EMEA
  `https://www.remotenomadjobs.com/remote-jobs/identity-security-technical-account-manager-emea-69b8d7cda285f34befcb6c53?ut`


---

## Successful Applications

1. **Harvey AI** — Staff Software Engineer, Site Reliability Engineer (SRE) [ashby]
2. **Harvey AI** — Staff Software Engineer, Full Stack [ashby]
3. **Harvey AI** — Mid/Senior/Staff Software Engineer, Agents [ashby]
4. **OpenAI** — Senior Software Engineer, Infrastructure  [ashby]
5. **Sentry** — Senior Software Engineer (C/C++), SDK [ashby]
