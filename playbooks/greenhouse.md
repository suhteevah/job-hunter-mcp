---
platform: Greenhouse
domain: job-boards.greenhouse.io
type: ATS
prevalence: 1794 jobs (74% of DB)
fill_strategy: wraith
submit_strategy: wraith_api_post
last_profiled: 2026-03-20
---

# Greenhouse Playbook

## Overview
Greenhouse is the dominant ATS. Used directly at `job-boards.greenhouse.io/{company}/jobs/{id}` and embedded by 100+ companies (Samsara, Databricks, Datadog, Stripe, Coinbase, Brex, etc.) via their own career sites with `gh_jid=` parameter.

## URL Patterns
- **Direct board**: `https://job-boards.greenhouse.io/{company}/jobs/{job_id}`
- **EU variant**: `https://job-boards.eu.greenhouse.io/{company}/jobs/{job_id}`
- **Company wrapper**: `https://{company}.com/careers/{path}?gh_jid={job_id}`
- **Apply page**: Same URL — form is embedded on the job detail page (scroll down)

## Form Structure (Standard)
All forms are **React-rendered** with controlled inputs. No traditional `<form action>`.

### Required Fields (universal)
| Field | Type | Ref Pattern | Value |
|-------|------|-------------|-------|
| First Name | text | `@eN` after "First Name *" label | Matt |
| Last Name | text | `@eN` after "Last Name *" label | Gates |
| Email | text | `@eN` after "Email *" label | ridgecellrepair@gmail.com |

### Common Optional Fields
| Field | Type | Notes |
|-------|------|-------|
| Phone | tel | 5307863655 |
| Country | dropdown (React) | Select via browse_fill or browse_select |
| Resume | file (hidden input) | Use browse_upload_file; input is visually-hidden |
| LinkedIn Profile | text | https://www.linkedin.com/in/matt-michels-b836b260/ |
| Website | text | https://github.com/suhteevah |
| Cover Letter / Additional Info | textarea | Personalized per role |

### Company-Specific Custom Questions
Greenhouse allows companies to add custom questions. Common patterns:
- **Work authorization**: dropdown ("Yes"/"No") — always "Yes"
- **Visa sponsorship**: dropdown — "No"
- **Relocation**: dropdown — varies
- **"Why [Company]?"**: textarea, often 200-400 words
- **Technical questions**: textarea, freeform
- **Previously interviewed?**: dropdown
- **AI Policy acknowledgment**: dropdown ("Yes")

### EEO / Voluntary Self-ID Section
Always at bottom. All optional. Standard fields:
- Gender (dropdown)
- Hispanic/Latino (dropdown)
- Race/Ethnicity (dropdown)
- Veteran Status (dropdown)
- Disability Status (dropdown)
Leave blank or select "Decline to self-identify" where available.

## Submission

### Security Code Flow
After clicking "Submit application", Greenhouse sends a **verification code** to the applicant's email:
```
Subject: "Security code for your application to {Company}"
From: no-reply@us.greenhouse-mail.io
Body: "Copy and paste this code: XXXXXXXX"
```
**Must read this code via Gmail MCP** and enter it on the page, then resubmit.

### API Endpoint (for wraith submit_form)
```
POST https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}/applications
Content-Type: multipart/form-data
```
EU variant: `boards-api.eu.greenhouse.io`

Note: Direct API POST returned 404 in earlier tests. Browser submission is more reliable.

## File Upload
- Input type: `input[type="file"]` — often **visually hidden** (CSS `clip: rect(0,0,0,0)`)
- Wraith's `browse_upload_file` targets it by searching all file inputs, not just visible ones
- Accepted types: pdf, doc, docx, txt, rtf
- Max size varies by company (typically 10-100MB)

## Fill Strategy
1. `browse_navigate` to job URL
2. `browse_fill` each field by ref_id (labels precede inputs by 1 ref)
3. `browse_upload_file` for resume (ref_id of file input, or first file input found)
4. `browse_fill` textareas for cover letter / custom questions
5. `browse_select` for dropdowns (React custom dropdowns may need browse_click first)
6. `browse_click` the "Submit application" button
7. **Wait for security code email** via Gmail MCP
8. `browse_fill` the security code field
9. `browse_click` submit again

## Quirks
- React controlled inputs: must use `__wraith_react_set_value` (handles native setter + _valueTracker invalidation)
- Dropdowns are NOT `<select>` elements — they're custom React components. May need to click to open, then click option.
- Country field uses autocomplete/typeahead
- File upload input is hidden; `browse_upload_file` finds it by scanning all `input[type=file]`
- Security code email arrives within 30-60 seconds
- Some companies have **multiple pages** (click "Next" to proceed)
- The page URL doesn't change when form becomes visible (it's a scroll target)
