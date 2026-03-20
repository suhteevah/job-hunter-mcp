---
platform: Indeed
domain: indeed.com
type: Job Board / Aggregator
prevalence: 14 jobs (direct), many more via redirect
fill_strategy: chrome
submit_strategy: chrome_browser
last_profiled: 2026-03-20
---

# Indeed Playbook

## Overview
Indeed is a job aggregator. Some jobs have "Easily Apply" (form on Indeed), others redirect to the company's ATS. Indeed has aggressive **bot detection** (CAPTCHA, Cloudflare Turnstile).

## URL Patterns
- **Job view**: `https://www.indeed.com/viewjob?jk={job_key}`
- **Apply**: Click "Apply now" → opens Indeed's apply flow or redirects to external site
- **Search**: `https://www.indeed.com/jobs?q={query}&l={location}`

## Account
- **Email**: mmichels88@gmail.com (NOT ridgecellrepair)
- **Profile**: Matt Michels
- Must be logged in for "Easily Apply"

## Indeed "Easily Apply" Flow
Multi-step modal:
1. **Contact info** (pre-filled from profile): name, email, phone, location
2. **Resume** (pre-uploaded from profile, or upload new)
3. **Screening questions**: company-specific (work auth, experience years, etc.)
4. **Review & Submit**

## Bot Detection
- **CAPTCHA**: Triggers on new searches and rapid actions. User must solve manually.
- **Cloudflare Turnstile**: On some pages. Wraith Tier 3 (FlareSolverr) can bypass.
- **Rate limiting**: Random delays (2-5s) between actions required.
- **Account lockout**: Too many rapid applications triggers review.

## Fill Strategy (Chrome only)
1. Ensure logged in as mmichels88@gmail.com
2. Navigate to job page
3. Click "Apply now"
4. Review pre-filled contact info
5. Select/upload resume
6. Answer screening questions (use `find()` + `form_input()`)
7. Click through each step
8. Submit

## Quirks
- **Cannot use wraith for applying** — bot detection too aggressive for headless
- Wraith CAN scrape job listings (CF bypass works for reading)
- "Easily Apply" jobs are the only ones worth doing on Indeed — others redirect to company ATS
- mmichels88@gmail.com is not connected to Gmail MCP — use Chrome to check emails
- Shadow DOM on some elements
- iCIMS-hosted Indeed applications (like WinCo) use iframes that don't respond to find()/form_input()
- Indeed may auto-withdraw applications after 30 days of no response
