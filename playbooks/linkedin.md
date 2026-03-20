---
platform: LinkedIn
domain: linkedin.com
type: Professional Network / Job Board
prevalence: 13 jobs (direct)
fill_strategy: chrome_kapture_sendinput
submit_strategy: chrome_browser
last_profiled: 2026-03-20
---

# LinkedIn Playbook

## Overview
LinkedIn Easy Apply is the most technically challenging platform due to **shadow DOM**, limited browser automation support, and multi-step modals. Most LinkedIn jobs redirect to external ATS — only "Easy Apply" jobs are done on LinkedIn itself.

## URL Patterns
- **Job view**: `https://www.linkedin.com/jobs/view/{job_id}`
- **Search**: `https://www.linkedin.com/jobs/search/?keywords={query}&location={location}`

## Account
- **Profile**: Matt Michels
- **Email**: mmichels88@gmail.com
- LinkedIn profile headline + about section already updated

## Easy Apply Flow
Multi-step modal with 2-5 pages:
1. **Contact info**: pre-filled from profile
2. **Resume**: select from uploaded resumes or upload new
3. **Additional questions**: work auth, experience, skills
4. **Review**: summary of all answers
5. **Submit**

## Technical Challenges
- **Shadow DOM**: LinkedIn uses Web Components with shadow roots
- `find()` / `form_input()` often fail — elements not in light DOM
- **Kapture** can find elements via `elementsFromPoint` for initial page
- **PowerShell SendInput** is last resort for modal interactions
- Clipboard paste + Tab navigation works for form filling

## Fill Strategy (Escalation Chain)
1. **Chrome find() + form_input()** — try first, works for some fields
2. **Kapture elementsFromPoint** — for elements Chrome tools can't find
3. **Chrome javascript_tool** — inject JS to pierce shadow DOM
4. **Clipboard paste**: Copy value → Ctrl+V into focused field
5. **Tab navigation**: Tab between fields, paste values
6. **PowerShell SendInput** — absolute last resort for stubborn modals

## Quirks
- Chrome window must be positioned at L=680 T=267, height=129px, viewport=1836x906
- Easy Apply modal blocks all other page interaction
- "Follow company" checkbox is pre-checked — uncheck if unwanted
- Resume selector shows previously uploaded resumes
- Some questions have dropdown menus that need click-to-open
- LinkedIn may rate-limit applications (max ~25-50/day reportedly)
- Profile must be "Open to Work" for best visibility
