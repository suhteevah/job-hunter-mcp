# Bypass Library

Anti-bot solutions catalog and live alerts. The orchestrator writes
auto-detected yield drops to the **Alerts** section. Manual entries go in
**Known Solutions**. Both stay here permanently — historical knowledge.

Format for an alert: `YYYY-MM-DD HH:MM | board | observed_yield/baseline | suspected_cause`
Format for a solution: `## board — short title` then full body.

---

## Alerts (auto-written by orchestrator)

- 2026-04-12 22:13 UTC | greenhouse | 4/23 (18%) | suspected: partial block (yield drop)


- 2026-04-12 09:43 UTC | greenhouse | 0/19 (0%) | suspected: complete block (zero yield)


- 2026-04-12 02:13 UTC | greenhouse | 9/29 (31%) | suspected: partial block (yield drop)


_(none — false alerts from 2026-04-11 08:43 and 10:23 UTC were cleared after fixing the EMA baseline pollution bug. See HANDOFF.md session #2 notes.)_

---

## Known Solutions

### Greenhouse — expired-job redirect (FIXED 2026-04-10)

**Symptom:** Wraith CDP apply submit returns "Submit button not found" on
jobs that were actually expired and redirected to `?error=true`.

**Root cause:** Greenhouse redirects expired postings to a company job-list
page that has no apply form, so the form-field count drops to 0-1.

**Fix:** Early-detect in `wraith_apply_swarm.py` — check if URL contains
`?error=true` or if the form field count is < 2, mark the job as `expired`
not `apply_failed`. See `playbooks/greenhouse.md`. The sweep script
`scripts/swarm/sweep_expired_gh.py` reclassified 126/300 historical failures.

### Indeed — Cloudflare bot challenge (FIXED 2026-04-09)

**Symptom:** Wraith returns CF interstitial page on indeed.com job listings.

**Root cause:** Indeed runs CF managed challenge on suspicious user agents.

**Fix:** Wraith BUG-9 fix shipped in the new `wraith-browser.exe` binary —
escalates automatically to FlareSolverr running in Docker on `localhost:8191`
when a CF challenge is detected. Also: logging into Indeed via Chrome CDP
(port 9222) bypasses the challenge entirely for authenticated sessions.

### Defense ATSes — account creation wall (BLOCKED, MANUAL ONLY)

**Symptom:** Lockheed (BrassRing), MITRE (Workday), Honeywell (Oracle HCM),
USAJobs (login.gov) all require an account before viewing or applying to
listings. Wraith and HTTP scrapers cannot proceed.

**Fix:** None automated. Matt creates accounts manually. After accounts exist,
build per-vendor apply scripts. See `playbooks/defense_ats.md`. Until then,
filter the 728 viable defense jobs out of any orchestrator scrape attempts.

### Aggregators — login wall hides real apply URL (NOT WORTH FIXING)

**Symptom:** weworkremotely / jobicy / remoteok / remotive / himalayas all
require login before exposing the real ATS URL behind their listing card.

**Fix:** Don't bother. Most companies on these aggregators also have direct
ATS scrapers (GH/Ashby/Lever) covering them. ROI for resolving aggregator
login walls is near zero.