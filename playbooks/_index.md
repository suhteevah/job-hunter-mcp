---
title: ATS Platform Playbooks Index
updated: 2026-03-20
total_platforms: 5 profiled
total_jobs: 2426
---

# ATS Platform Playbooks

Quick reference for all profiled application tracking systems and job platforms.

## Platform Summary

| Platform | Jobs | % | Fill Tool | Submit Method | Difficulty |
|----------|------|---|-----------|---------------|------------|
| [Greenhouse](greenhouse.md) | 1794 | 74% | Wraith | API POST / browser | Medium |
| [Ashby](ashby.md) | 175 | 7% | Chrome | Browser | Medium |
| [Lever](lever.md) | 42 | 2% | Wraith | Form POST | Easy |
| [Indeed](indeed.md) | 14 | 1% | Chrome | Browser | Hard |
| [LinkedIn](linkedin.md) | 13 | 1% | Chrome+Kapture | Browser | Hardest |
| [Company-Native](company-native-greenhouse.md) | ~800 | 33% | Wraith (via GH) | Greenhouse redirect | Medium |

Note: Company-Native overlaps with Greenhouse count (they ARE Greenhouse under the hood).

## Priority Order for Applying
1. **Lever** — easiest, no security code, direct form POST
2. **Greenhouse** — most volume, security code flow via Gmail MCP
3. **Company-Native** — skip wrapper, go direct to Greenhouse
4. **Ashby** — Chrome only, but straightforward forms
5. **Indeed** — CAPTCHA issues, Chrome only, mmichels88 account
6. **LinkedIn** — shadow DOM nightmare, last resort

## Quick Decision Tree
```
Is the URL jobs.lever.co? → Use Lever playbook (wraith)
Is the URL job-boards.greenhouse.io? → Use Greenhouse playbook (wraith)
Does the URL contain gh_jid=? → Use Company-Native playbook (redirect to GH)
Is the URL jobs.ashbyhq.com? → Use Ashby playbook (Chrome)
Is it on indeed.com? → Use Indeed playbook (Chrome, mmichels88)
Is it on linkedin.com? → Use LinkedIn playbook (Chrome+Kapture)
Otherwise → Navigate in Chrome, identify ATS, update playbooks
```

## Form Data (Universal)
```yaml
first_name: Matt
last_name: Gates
email: ridgecellrepair@gmail.com  # Primary (Greenhouse, Lever, Ashby)
email_indeed: mmichels88@gmail.com  # Indeed/LinkedIn only
phone: 5307863655
linkedin: https://www.linkedin.com/in/matt-michels-b836b260/
github: https://github.com/suhteevah
location: Chico, CA
work_auth: Yes (US citizen)
visa_sponsorship: No
remote: Yes
relocate: Yes (Phoenix area)
years_experience: 10
education: Some college (Associates level)
english: Native
background_check: Yes
drug_test: Yes
```
