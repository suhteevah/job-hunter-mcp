---
platform: Defense Contractor ATSes
type: mixed (BrassRing, Workday, Oracle HCM, USAJobs)
prevalence: 728 viable jobs (clearance-filtered)
fill_strategy: mixed
submit_strategy: requires account creation per platform
last_profiled: 2026-04-08
status: BLOCKED — needs account creation decisions
---

# Defense Contractor ATSes Playbook

## ⚠️ Important Correction
The initial assumption that Lockheed/L3Harris/Boeing all use Workday was **WRONG**.
Ground-truth identification below.

## ATS Map (verified 2026-04-08)

| Source | Company | Viable Jobs | Actual ATS | Login Required |
|--------|---------|------------:|------------|:--------------:|
| lockheed | Lockheed Martin | 274 | **IBM BrassRing** (`sjobs.brassring.com`) | ✅ Yes |
| l3harris | L3Harris | 221 | TBD — probably BrassRing | ✅ Likely |
| boeing | Boeing | 172 | TBD — probably Workday or BrassRing | ✅ Likely |
| mitre | MITRE | 46 | **Workday** (`mitre.wd5.myworkdayjobs.com`) | ✅ Yes |
| honeywell | Honeywell | 8 | **Oracle HCM** (`careers.honeywell.com`) | ✅ Yes |
| usajobs | DFAS / federal | 7 | **USAJobs.gov** | ✅ Yes (login.gov) |

## URL Patterns
- **BrassRing**: `sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?...jobid=NNNN`
  - Branded wrappers: `lockheedmartinjobs.com/job/...` → "APPLY NOW" link → redirects to BrassRing
- **Workday**: `{company}.wd{N}.myworkdayjobs.com/{site}/job/{loc}/{slug}_{reqid}/apply`
- **Oracle HCM**: `careers.{company}.com/en/sites/{company}/job/{id}` (varies)
- **USAJobs**: `usajobs.gov/job/{id}` — federal-only flow

## Discovery Flow (all platforms)
1. Scraping currently lands on the **branded wrapper page** (e.g. lockheedmartinjobs.com)
2. Wrapper has an "APPLY NOW" link/button that redirects to the real ATS
3. Real ATS demands account creation on first apply

## 🚫 Blocker: Account Creation
All 4 ATSes require a persistent user account before accepting any application.
**Decision needed** before build-out:

**Option A — Manual account bootstrap (recommended):**
- Create one account per platform by hand (user does it, stores creds)
- Store in `J:\job-hunter-mcp\secrets.json`:
  ```json
  {
    "brassring": { "email": "...", "password": "..." },
    "workday_mitre": { "email": "...", "password": "..." },
    "oracle_honeywell": { "email": "...", "password": "..." },
    "usajobs": { "email": "...", "password": "..." }
  }
  ```
- Apply swarm logs in first, then applies

**Option B — Automated account creation:**
- Wraith creates accounts on-the-fly per platform
- Risk: CAPTCHA, email verification, ToS issues
- Not recommended

## Form Structure (BrassRing — Lockheed)
After sign-in, BrassRing typically presents:
1. Upload resume (parses into fields)
2. Confirm/edit parsed personal info
3. Work history section (multi-entry)
4. Education section
5. EEO/voluntary disclosures
6. Pre-screen questions (company-specific)
7. Final review + submit

**Required fields observed** (before sign-in screen loaded):
- Email + password for account
- Detailed work history with dates
- Clearance questionnaire (most entries will auto-reject without)

## Form Structure (Workday — MITRE)
Workday has a standardized flow used by 2000+ companies:
1. Create account (email + password + terms)
2. "Use My Last Application" if returning OR upload resume
3. Multi-step wizard: My Information → Experience → Application Questions → Voluntary Disclosures → Self Identify → Review → Submit
4. Each step has a "Save and Continue" button — `@ref` for button text contains "continue" or "next"

## Implementation Plan (when unblocked)
1. Create accounts (manual) on all 4 platforms
2. Store creds in secrets.json (gitignored)
3. Build `scripts/swarm/brassring_apply.py` — Lockheed (274 jobs, biggest bucket)
4. Build `scripts/swarm/workday_apply.py` — MITRE + any other Workday discoveries
5. Profile Boeing + L3Harris to see if they're also BrassRing (likely reusable)
6. Skip Honeywell (only 8 jobs, not worth Oracle HCM build)
7. Skip USAJobs (only 7 jobs, login.gov is auth nightmare)

## Clearance Warning
Even with working apply automation, expect ~60-80% of these jobs to demand
Secret/TS clearance that Matt doesn't have. Net viable after apply-time filtering
may drop from 728 → ~150-200. Worth the build only if Lockheed + Boeing pans out.
