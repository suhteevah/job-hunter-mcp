---
platform: Company-Native (Greenhouse-backed)
domain: various
type: ATS wrapper
prevalence: ~800 jobs
fill_strategy: wraith_or_chrome
submit_strategy: redirect_to_greenhouse
last_profiled: 2026-03-20
---

# Company-Native Sites (Greenhouse-backed) Playbook

## Overview
Companies like Samsara, Databricks, Datadog, Stripe, Coinbase, and Brex host their own career pages but use Greenhouse as the backend ATS. The job description is on their domain; the "Apply" button either:
1. **Redirects** to `job-boards.greenhouse.io/{company}/jobs/{id}` (most common)
2. **Opens an iframe/modal** with the Greenhouse form embedded
3. **Has a custom form** that POSTs to Greenhouse API

## How to Identify
- URL contains `gh_jid=` parameter
- "Apply" button links to greenhouse.io
- Footer says "Powered by Greenhouse"
- Confirmation emails come from `no-reply@us.greenhouse-mail.io`

## Affected Companies in Our DB
| Company | Jobs | Career Page Pattern |
|---------|------|-------------------|
| Samsara | 262 | samsara.com/company/careers/roles/{id} |
| Databricks | 224 | databricks.com/company/careers/open-positions/job?gh_jid={id} |
| Datadog | 102 | careers.datadoghq.com/detail/{id}/ |
| Stripe | 102 | stripe.com/jobs/search?gh_jid={id} |
| Coinbase | 70 | coinbase.com/careers/positions/{id} |
| Brex | 48 | brex.com/careers/{id} |
| Airbnb | 39 | careers.airbnb.com |
| Nuro | 75 | nuro.ai |
| Elastic | 23 | jobs.elastic.co |
| CockroachLabs | 17 | cockroachlabs.com |

## Strategy: Skip the Wrapper
Instead of navigating the company site, **go directly to the Greenhouse board URL**:
```
https://job-boards.greenhouse.io/{company}/jobs/{job_id}
```

To find the company slug:
1. Check the `gh_jid` in the URL
2. Or navigate the company page and follow the "Apply" redirect

Once on the Greenhouse page, follow the **Greenhouse Playbook** exactly.

## Exceptions
- **Coinbase**: Cloudflare protected ("Just a moment...") — use Chrome
- **Brex**: Vercel security checkpoint — use Chrome
- Some companies have **custom forms** that don't redirect to Greenhouse (rare)

## Fill Strategy
1. Extract `gh_jid` from company URL
2. Try direct Greenhouse URL: `job-boards.greenhouse.io/{company_slug}/jobs/{gh_jid}`
3. If that works → follow Greenhouse playbook
4. If 404 → navigate company page in Chrome, click Apply, follow redirect

## Mapping Company → Greenhouse Slug
This requires one-time discovery. When we encounter a new company:
1. Navigate their career page in wraith
2. Look for Greenhouse links in the DOM
3. Cache the `{company_slug}` in our DB for future use
