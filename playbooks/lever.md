---
platform: Lever
domain: jobs.lever.co
type: ATS
prevalence: 42 jobs (2% of DB)
fill_strategy: wraith
submit_strategy: wraith_form_post
last_profiled: 2026-03-20
---

# Lever Playbook

## Overview
Lever serves the application form directly at `jobs.lever.co/{company}/{job_id}/apply`. Forms are server-rendered HTML (not React SPA), making them more straightforward than Greenhouse.

## URL Patterns
- **Job page**: `https://jobs.lever.co/{company}/{job_id}`
- **Apply page**: `https://jobs.lever.co/{company}/{job_id}/apply`
- Always append `/apply` to go directly to the form.

## Form Structure (Standard)

### Required Fields
| Field | Type | Value |
|-------|------|-------|
| Full name | text (@e13 area) | Matt Gates |
| Email | email (@e15 area) | ridgecellrepair@gmail.com |
| Phone | text (@e17 area) | 5307863655 |
| Resume/CV | file (@e10) | Upload via browse_upload_file |

### Common Optional Fields
| Field | Type | Notes |
|-------|------|-------|
| Current location | text + autocomplete + hidden field | Type city, hidden field stores structured value |
| Current company | text | Leave blank or fill |
| LinkedIn URL | text | https://www.linkedin.com/in/matt-michels-b836b260/ |
| GitHub URL | text | https://github.com/suhteevah |
| Other website | text | |
| Additional information | textarea | Cover letter goes here |

### Custom Questions (Hidden Field JSON)
**Critical Lever discovery**: Custom questions are stored as **JSON blobs in hidden input values**. The JSON contains:
- `fields[].type`: "multiple-choice", "multiple-select", "text", "textarea"
- `fields[].text`: The question text
- `fields[].required`: boolean
- `fields[].options[].text`: Option labels
- `fields[].options[].optionId`: UUID for each option

This means we can parse the hidden fields to understand all custom questions programmatically without reading labels.

Example hidden field value:
```json
{
  "text": "Work Authorization",
  "fields": [{
    "type": "multiple-choice",
    "text": "Will you require sponsorship?",
    "required": true,
    "options": [
      {"text": "Yes", "optionId": "uuid1"},
      {"text": "No", "optionId": "uuid2"}
    ]
  }]
}
```

### Radio/Checkbox Groups
Custom questions render as:
- `radio` inputs for single-choice (each with `value="Option Text"`)
- `checkbox` inputs for multi-select (each with `value="Option Text"`)

### EEO Section
- Gender: `<select>` dropdown (native HTML, not React)
- Race: `<select>` dropdown
- Veteran status: `<select>` dropdown
Standard `<select>` elements — use `browse_select` with the option value text.

## Submission
- Form action: `POST` to the same `/apply` URL
- Content-Type: `application/x-www-form-urlencoded`
- **No security code flow** — Lever submits directly
- Confirmation page appears immediately

## File Upload
- Standard `input[type="file"]` at @e10 area
- Max 100MB
- "ATTACH RESUME/CV" link triggers the file input
- Lever shows "Analyzing resume... Success!" after upload

## Fill Strategy
1. Navigate to `jobs.lever.co/{company}/{id}/apply`
2. `browse_upload_file` for resume first (triggers auto-parse)
3. `browse_fill` name, email, phone, location, LinkedIn, GitHub
4. Parse hidden fields to identify custom questions
5. `browse_click` appropriate radio/checkbox for each custom question
6. `browse_fill` textarea for "Additional information" (cover letter)
7. `browse_click` "Submit application" button

## Quirks
- "Apply with LinkedIn" button exists but requires OAuth — skip it
- Location field has autocomplete; hidden field stores the real value — fill the visible text field
- Resume parsing may auto-fill name/email — verify with snapshot after upload
- Hidden fields contain the FULL question schema as JSON (goldmine for automation)
- Account ID in hidden fields is per-company
- Some Lever forms have multiple custom question sections (h4 headers separate them)
