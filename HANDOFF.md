# CLAUDE CODE HANDOFF — Autonomous Job Hunter
# Read this FIRST. Then read J:\job-hunter-mcp\skills\SKILL.md for full details.
# Last updated: 2026-03-20 (evening session)

## IMMEDIATE CONTEXT
Matt Gates is job hunting. 26 days remaining to generate revenue.
502 applications submitted. 8,876 jobs tracked in DB.
Wraith browser (openclaw-browser) configured with FlareSolverr for CF bypass.
FlareSolverr running on localhost:8191 (Docker).
The machine never sleeps.

## YOUR JOB
1. Run fresh search cycles to find new jobs
2. Apply to every viable job (score >= 60) automatically
3. Track all applications in SQLite
4. Prioritize: Ashby (97.5% success) > Lever > Greenhouse (needs security codes) > Indeed > LinkedIn
5. Never stop. If one application fails, move to the next.
6. ALWAYS write personalized cover letters for each application.
7. ALWAYS fetch full job descriptions for scoring — never score title-only.

## KEY STATS (as of 2026-03-20 evening)
- **Total applied**: 502 (was 306 at session start)
- **Applied today**: 402
- **Needs security code**: 151 (mostly GitLab — code retry script works)
- **New viable (fit>=60)**: 65
- **Total jobs in DB**: 8,876
- **Ashby success rate**: 159/163 = 97.5%
- **Zero replies from companies yet** — most apps are <12 hours old

## EXECUTION
```powershell
# Always use this for PowerShell:
powershell -ExecutionPolicy Bypass -Command { your commands here }
# Or for scripts:
powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
```

## KEY FILES
- `J:\job-hunter-mcp\skills\SKILL.md` — Full platform docs, DB schema, workflow
- `J:\job-hunter-mcp\skills\linkedin\SKILL.md` — LinkedIn shadow DOM patterns
- `J:\job-hunter-mcp\skills\upwork\SKILL.md` — Upwork proposal workflow
- `J:\job-hunter-mcp\skills\dice\SKILL.md` — Aggregator behavior map
- `J:\job-hunter-mcp\launch_hunter.ps1` — PowerShell functions (search, status, stats)
- `C:\Users\Matt\Downloads\matt_gates_resume_ai.docx` — AI-focused resume (USE THIS)
- `C:\Users\Matt\.job-hunter-mcp\jobs.db` — SQLite job database
- `J:\job-hunter-mcp\secrets.json` — Gmail app passwords (both accounts VERIFIED WORKING)

## PYTHON VENV
```powershell
$VENV = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
& $VENV -c "print('ok')"
```

## BROWSER AUTOMATION PRIORITY
1. **Wraith (openclaw-browser)** — PRIMARY for scraping CF-protected sites (Indeed, Glassdoor)
   - MCP server: `.mcp.json` configured WITH FlareSolverr env var
   - CLI: `J:\openclaw-browser\target\release\openclaw-browser.exe`
   - 80+ MCP tools: navigate, click, fill, extract, search, vault, cache, entity graph, swarm, workflows
   - CF Turnstile bypass: Tier 3 FlareSolverr at localhost:8191 (MUST RESTART Claude Code to activate)
   - Indeed: CONFIRMED WORKING via FlareSolverr (19 jobs scraped in test)
   - Cache: SQLite knowledge store — every page cached, never re-fetches
   - Stealth: 19 evasions enabled
   - **GAP**: Cannot render React SPAs (Ashby, Greenhouse forms). File upload works (v10).
2. **Playwright (headless)** — For React SPA form filling (Greenhouse, Ashby, Lever)
   - Invisible Chromium, not user's Chrome
   - Ashby: 97.5% success rate, ~20s per app
   - Greenhouse: works but needs security code handling
   - Lever: needs Playwright (API submit returns 400)
3. **Claude in Chrome** — For checking mmichels88 Gmail, manual interventions
4. **FlareSolverr** — Docker on localhost:8191, solves CF Turnstile challenges

## SWARM SCRIPTS (BATTLE-TESTED)
- `swarm_greenhouse_playwright.py` — Greenhouse batch applicant (Playwright headless)
  - Args: `--limit N --resume-from N --delay N --headed`
  - Handles: form fill, resume upload, cover letters, EEOC, security codes (IMAP)
  - Set env: `GMAIL_APP_PASSWORD="yzpn qern vrax fvta"`
- `swarm_ashby_playwright.py` — Ashby batch applicant (Playwright headless)
  - Args: `--limit N --resume-from N --delay N --worker-id N`
  - 97.5% success rate. Click Apply, upload resume, fill fields, submit.
- `greenhouse_code_retry.py` — Re-applies to needs_code jobs with real-time Gmail code fetch
  - Uses IMAP message-count tracking (not search) to detect new codes
  - Extracts code from HTML `<h1>` tags via regex
  - Uses JavaScript injection to fill code + enable/click disabled submit button
  - ~50% success rate (race conditions when parallel)
  - BEST RUN SINGLE-THREADED to avoid code conflicts
- `mega_swarm_scrape.py` — Scrapes 260 company Greenhouse+Ashby boards via API
  - 150 parallel HTTP workers, scraped 10,058 jobs in 48 seconds
  - **FIX NEEDED**: Must fetch full descriptions at scrape time (not title-only)
- `rescore_with_descriptions.py` — Re-scores jobs by fetching descriptions from Greenhouse API
  - 150 parallel workers, rescored 6,827 jobs in 3 minutes
- `lever_blast.py` — Attempted Lever API submit (failed — needs Playwright)

## CRITICAL PATTERNS LEARNED
- **Ashby forms**: React SPA, but Playwright handles perfectly. Click "Apply" button, fill by selectors + label association, upload resume, check consent boxes, submit. 97.5% success.
- **Greenhouse security codes**: Email arrives as HTML-only (no text/plain). Code is in `<h1>` tag. IMAP search has Gmail index lag — use message COUNT comparison instead. JavaScript injection needed to enable disabled submit button after code entry.
- **Greenhouse EEOC Gender dropdown**: Reddit/Discord require gender field. React Select with numeric IDs (e.g., #443). Current script can't fill these — `fill_react_select` doesn't work on this variant.
- **Greenhouse custom career pages**: Stripe, Samsara, Databricks, Okta use wrapped URLs — form doesn't render on `boards.greenhouse.io`. These need direct career page automation.
- **Gmail IMAP vs API**: IMAP search has 60-90s index lag for new messages. Use message count (INBOX SELECT returns count) to detect new messages instead of search. Gmail MCP API has no lag.
- **FlareSolverr + Indeed**: CONFIRMED WORKING. `POST http://localhost:8191/v1` with `cmd: "request.get"`. Returns 2MB HTML with 19 job beacons. Wraith needs restart to use it via MCP.
- **Parallel workers**: 10 simultaneous Playwright instances work fine on this machine. For security code jobs, run SINGLE-THREADED to avoid race conditions.
- **Lever forms**: API submit deprecated (404/400). Must use Playwright browser.
- Always add `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` in Python
- PowerShell `&&` doesn't work — use `;` as separator

## CONTACT INFO FOR FORMS
- Full name: Matt Gates (or Matt Michels on LinkedIn/Indeed)
- Email: ridgecellrepair@gmail.com (primary) / mmichels88@gmail.com (Indeed)
- Phone: 5307863655
- LinkedIn: https://www.linkedin.com/in/matt-michels-b836b260/
- GitHub: https://github.com/suhteevah
- Location: Chico, CA (willing to relocate to Phoenix area)
- Work authorization: Yes (US citizen)
- Remote: Yes
- Years of experience: 10
- Education: Some college (Associates level) — Butte College
- Current company: Ridge Cell Repair LLC (Self-employed)

## WHAT WAS DONE (2026-03-20 evening session)
### Mega Session Results: +196 applications (306 → 502)
- Gmail app passwords verified (both accounts SMTP OK)
- **Ashby Swarm**: 5 parallel Playwright workers, 163 jobs, 159 SUCCESS (97.5%)
  - Companies: OpenAI (20+), Perplexity AI (6), LangChain (5+), Deepgram (4), Harvey AI, Baseten (3), Sentry, Anyscale, Pinecone, Replit, Reka (3), Railway, LiveKit (2)
- **Greenhouse Swarm**: 5 parallel Playwright workers, 595 jobs
  - 0 direct successes (stale Databricks, custom career pages for Stripe/Samsara)
  - 200+ jobs reached security code stage (GitLab, ClickHouse, Tailscale, Chainguard, etc.)
- **Security Code Retry**: Built and debugged IMAP code fetcher
  - Fixed: HTML-only emails, `<h1>` code extraction, JS injection for disabled buttons
  - 5 parallel workers, ~66 total successes across GitLab, ClickHouse, Tailscale, Chainguard, Vercel, Anthropic, PagerDuty
- **Mega Scrape**: 260 company boards (164 Greenhouse + 96 Ashby) via API
  - 150 parallel HTTP workers, 10,058 jobs scraped in 48 seconds, 5,909 new inserted
  - Top finds: Databricks 605, Stripe 414, Okta 366, MongoDB 353, Anthropic 322
- **Full Description Rescore**: 6,827 jobs rescored with Greenhouse API descriptions in 3 minutes
- **Indeed via FlareSolverr**: CONFIRMED WORKING (19 jobs in test scrape)
- **.mcp.json updated**: Added `WRAITH_FLARESOLVERR=http://localhost:8191` env var
- **Wraith SPA gap filed**: Cannot render React SPAs — needs headful browser mode

### Checked Both Gmail Accounts for Replies
- ridgecellrepair@gmail.com: Zero recruiter replies. Auto-responders only (OpenAI, Rad AI, TRM Labs)
- mmichels88@gmail.com: Hudson Manpower hasn't replied to follow-up. WinCo confirmation only.
- Most apps are <12 hours old — check again Monday/Tuesday

## WHAT WAS DONE (2026-03-20 morning session)
- 6 Greenhouse apps via Playwright: RegScale, Grafana Labs, Censys, Khan Academy, OnBoard, Pathward
- 8 new Greenhouse jobs discovered via Wraith DuckDuckGo search
- FlareSolverr Docker confirmed running on port 8191
- Wraith dev notified of gaps: file upload (NOW FIXED in v10), binary rebuild, session persistence

## WHAT WAS DONE (2026-03-19)
- 100+ applications total reached
- Indeed browser automation: Sr. QA Automation Engineer @ Two95, Sales Engineer @ Purple Cow
- WinCo Foods Sr. Middleware Developer iCIMS application COMPLETED ($110-150K + 20% ESOP)
- Hudson Manpower GenAI follow-up email SENT (asking 3 critical questions)
- LatchPac repo reviewed — industrial automation experience documented for cover letters

## ACTIVE LEADS AWAITING RESPONSE
1. **Hudson Manpower** — GenAI / ML AI / Data Scientist. Follow-up sent 2026-03-19 7:26 PM. Asked about end client, comp range, W2/contract. Monitor mmichels88@gmail.com for reply.
2. **WinCo Foods** — Sr. Middleware Developer, Phoenix (remote). iCIMS application submitted. $110-150K + 20% ESOP. Monitor mmichels88@gmail.com.
3. **All 502 applications** — Monitor ridgecellrepair@gmail.com. Expect first responses by 2026-03-24 (Monday/Tuesday).

## NEXT IMMEDIATE TARGETS
1. **RESTART CLAUDE CODE** to activate Wraith FlareSolverr integration
2. **Indeed mega-scrape via Wraith+FlareSolverr** — untapped source, thousands of jobs
3. **Lever board scrape** — similar to Greenhouse mega-scrape, hundreds of companies use Lever
4. **Run security code retry SINGLE-THREADED** on 151 remaining needs_code jobs
5. **Apply to 65 new viable (fit>=60) Greenhouse jobs** with code retry
6. **Lower threshold to 40** on existing DB — 729 more borderline jobs
7. **Wellfound/AngelList scrape** — startup-heavy, good fit, has public API
8. **Monitor both Gmail accounts** for recruiter replies starting Monday

## PLATFORMS COVERED vs NOT COVERED
| Platform | Status | Jobs in DB |
|----------|--------|-----------|
| Greenhouse | 101 companies scraped, 7,958 jobs | SATURATED for known boards |
| Ashby | 22 companies, 408 jobs (159 applied) | SATURATED (SPA blocks new scraping) |
| Indeed | FlareSolverr CONFIRMED, not yet scraped at scale | READY TO GO |
| Lever | 44 jobs (Plaid), API submit broken | Need board scrape + Playwright |
| LinkedIn | Not scraped, needs auth + anti-bot | HARD |
| Workday | Not scraped (Amazon, Microsoft, etc.) | Enterprise companies |
| Wellfound | Not scraped, has public API | Startups |
| JSearch API | 291 jobs, RapidAPI quota exhausted | Need plan upgrade or alternative |

## WRAITH (OPENCLAW-BROWSER) — CONFIG
- **Binary**: `J:\openclaw-browser\target\release\openclaw-browser.exe`
- **MCP config**: `J:\job-hunter-mcp\.mcp.json` (UPDATED with FlareSolverr env)
- **FlareSolverr**: Docker on `localhost:8191` — solves CF Turnstile for Indeed/Glassdoor
- **Stealth**: 19 evasions, Chrome 131 TLS fingerprint
- **Key gap**: Cannot render React SPAs — use Playwright for form filling

## MATT'S KEY PROJECTS FOR COVER LETTERS
- **Wraith Browser**: 27K lines Rust, AI-driven browser automation, agent orchestration
- **Kalshi Weather Bot**: 20x returns, 4 beta testers, ML prediction + autonomous trading
- **OpenClaw**: AI inference fleet, distributed model serving
- **10+ MCP Servers**: Production Model Context Protocol integrations
- **LatchPac Validator 3000**: ESP32-S3 production test fixture, 120VAC, SWD programming, opto-isolated
- **PID Controller**: Custom implementation on GitHub
- **Industrial Sensors QA**: Compas Engineering — liquid level switches, ERECTA SWITCH
