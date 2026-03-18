# Job Aggregator & Application Skill

## Overview
Patterns for applying to jobs found through aggregator sites (DailyRemote, Flexionis, Dice, Indeed). These sites scrape jobs from multiple sources and redirect to the actual application pages.

## Aggregator Behavior Map

### DailyRemote (dailyremote.com)
- **Apply flow:** "Apply Now" button → redirects to employer's actual application page
- **Apply URL pattern:** `https://dailyremote.com/apply/{jobId}` → 302 redirect
- **Common redirects to:** LinkedIn Easy Apply, company career pages, Greenhouse, Lever
- **Extraction method:** 
  ```
  Kapture:dom(tabId, xpath="//a[contains(text(),'Apply Now')]")
  ```
  Returns HTML with `href="/apply/{jobId}"`. Prepend `https://dailyremote.com` and navigate.
- **Key insight:** The Apply Now link has `target="_blank"` — opens new tab. Use `Kapture:navigate` to follow the redirect URL directly instead.

### Flexionis (flexionis.wuaze.com)
- **Apply flow:** NO APPLY FORM — pure aggregator
- **Status:** Scrapes and reposts jobs from other sources
- **Action:** Extract the original job source from the description text, then apply there
- **Skip this site** for direct applications — use the original source URL from the job hunter DB

### Dice (dice.com)
- **Apply flow:** Direct "Apply" or "Easy Apply" button on the job page
- **Requires:** Dice account (login required)
- **Job expiration:** Jobs expire fast — check availability before applying
- **Error indicator:** Red banner "Sorry this job is no longer available"
- **Alternative:** Similar Jobs section shows related active listings

### Indeed (indeed.com)
- **Apply flow:** "Apply now" button → may redirect to company site or use Indeed's built-in form
- **Requires:** Indeed account for Easy Apply
- **Not directly tested yet** — jobs appear through JSearch API

### LinkedIn Easy Apply
- **Apply flow:** Blue "Easy Apply" button on job page
- **Requires:** LinkedIn login (already authenticated)
- **Form:** Multi-step modal with phone, resume, cover letter, screening questions
- **See:** `linkedin/SKILL.md` for detailed automation patterns

## Workflow: Apply via DailyRemote → LinkedIn

1. Get job URL from job hunter DB
2. Navigate to DailyRemote job page
3. Extract Apply Now href:
   ```
   Kapture:dom(tabId, xpath="//a[contains(text(),'Apply Now')]")
   ```
4. Navigate to the redirect URL (prepend domain if relative)
5. Follow redirect — typically lands on LinkedIn job page
6. Use LinkedIn Easy Apply workflow from `linkedin/SKILL.md`

## Workflow: Apply via Dice

1. Navigate to Dice job URL
2. Check for "no longer available" banner
3. If available, click "Apply" button
4. Fill application form (Dice has standard HTML forms — regular selectors work)
5. Upload resume if prompted

## Job Hunter MCP Integration

The job hunter MCP server at `J:\job-hunter-mcp\` tracks all jobs in SQLite:
- DB: `C:\Users\Matt\.job-hunter-mcp\jobs.db`
- Get top jobs: `python get_top.py` (score >= 60)
- Draft cover letters: `python draft_letters.py`
- Email queue: Stores drafted cover letters for each job

### Useful queries:
```python
from src import db
# Get top matches
jobs = db.get_jobs(min_score=80, limit=10)
# Get job details
job = db.get_job("job_id_here")
# Update status after applying
db.update_job("job_id_here", status="applied", notes="Applied via LinkedIn Easy Apply")
```

## Application Status Tracking
Update job status in the DB after each application:
- `new` → freshly discovered
- `saved` → cover letter drafted
- `applied` → application submitted
- `interviewing` → got a response
- `rejected` → declined
- `offer` → received offer

## Source-to-Platform Mapping
| Source in DB | Platform | Apply Method |
|-------------|----------|-------------|
| jsearch | Varies | Follow URL, usually LinkedIn/Dice/Indeed |
| arbeitnow | Arbeitnow | Direct on arbeitnow.com (EU-focused) |
| remotive | Remotive | Direct on remotive.com |

## Known Issues
- JSearch URLs often include `utm_campaign=google_jobs_apply` tracking params — these work fine
- Flexionis is always an aggregator — never try to apply there
- DailyRemote Apply Now opens new tabs — navigate directly to avoid losing tab context
- Dice jobs expire within days — prioritize fresh listings
- Some JSearch results return None data — handled by error catching in apis.py
