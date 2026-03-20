---
platform: Ashby
domain: jobs.ashbyhq.com
type: ATS
prevalence: 175 jobs (7% of DB)
fill_strategy: chrome
submit_strategy: chrome_browser
last_profiled: 2026-03-20
---

# Ashby Playbook

## Overview
Ashby is a **pure client-side React SPA**. Wraith's headless engine (QuickJS) cannot render it — the page returns an empty snapshot. Must use **Claude in Chrome** for Ashby applications.

## URL Patterns
- **Job page**: `https://jobs.ashbyhq.com/{company}/{job_id}`
- **Apply page**: `https://jobs.ashbyhq.com/{company}/{job_id}/application`

## Form Structure (Typical)
Ashby forms are relatively standard but vary by company. Common fields:
- Full name (or First/Last split)
- Email
- Phone
- Resume upload
- LinkedIn URL
- Cover letter / Additional info (textarea)
- Custom questions (dropdowns, radio, text)
- Work authorization
- Location

## Submission
- **API endpoint**: `POST https://jobs.ashbyhq.com/{company}/{job_id}/application/submit`
- Content-Type: `application/json`
- Direct API submission may work (untested with wraith)

## Fill Strategy (Chrome only)
1. Navigate to application URL in Chrome
2. Use `find()` to locate form fields
3. Use `form_input()` for text fields
4. Use `computer(left_click)` for dropdowns
5. Use file upload for resume
6. Click submit

## Quirks
- **Cannot use wraith** — empty DOM on headless render
- React SPA requires full browser with JS engine
- Some Ashby forms have multi-step pages
- May need to scroll to load lazy-rendered sections
- Consider using Kapture as backup if Chrome tools fail
