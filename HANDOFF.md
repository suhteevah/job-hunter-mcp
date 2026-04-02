# CLAUDE CODE HANDOFF — Autonomous Job Hunter
# Read this FIRST. Then read J:\job-hunter-mcp\skills\SKILL.md for full details.
# Last updated: 2026-04-01 SESSION — 5,020+ applied, 24.7K+ jobs in DB, +1,839 apps this session

## IMMEDIATE CONTEXT
Matt Gates is job hunting. 9 days remaining to generate revenue. **REMOTE or Chico (95926) ONLY.**
~5,020+ applications submitted. ~24,700+ jobs tracked in DB.
**PostgreSQL live** on localhost:5432 (Docker). SQLite still primary for scripts but migration done.
Wraith CDP fully operational. navigate_cdp for React SPAs (Ashby/Greenhouse). Native for Lever.
**Wraith binary UPDATED**: `J:\wraith-browser\target\release\wraith-browser.exe` (built 2026-03-31, BUG-9 fixed)
**Old binary**: `openclaw-browser.exe` is DEPRECATED — do NOT use.
**.mcp.json updated** to point to `wraith-browser.exe` with `WRAITH_FLARESOLVERR=http://localhost:8191`.
**Indeed full pagination unlocked**: Google SSO login + `filter=0` URL param. Use `indeed_chrome_scrape.py`.
**Greenhouse URL embed conversion** unlocks custom career pages (Stripe, Samsara, Datadog, etc.)
BUG-9 (Indeed CF regression) FIXED in new binary. BUG-10 (page 2 auth) solved via Chrome login.
FlareSolverr running on localhost:8191 (Docker) — used for Indeed scraping (CF bypass).
The machine never sleeps.

### SESSION RESULTS (2026-04-01)
- **+861 NEW APPLICATIONS this session** (3,181 → 4,042) across Ashby/Greenhouse/Lever/Upwork
- **Ashby**: 97/98 (99%) + 6 retries recovered — PostHog, Vanta, Drata, Snowflake, Docker, Mosaic, Ramp
- **Greenhouse batch 1**: 41/47 (87%) — Elastic, Instacart, Databricks, Okta, Duolingo, Riot Games
- **Greenhouse batch 2**: 200/200 (100%) — Anduril (Senior LLM, AI, ML, Rust SWE), SpaceX
- **Greenhouse batch 3**: 453/453 (100%) — Anduril, SpaceX, Cloudflare, remaining companies
- **Lever**: 64/70 (91%) — Mistral (36 Applied AI/ML/SWE roles), Plaid (7), JumpCloud (6), Metabase (8), Neon (3)
- **Scored 3,433 unscored jobs** — found 656 high-value targets (Anduril 399, SpaceX 243, Elastic 7, Cloudflare 3)
- **Fixed bugs**: NULL id column preventing score updates, double /apply URL in Lever swarm
- **Upwork**: Submitted proposal for "AI Enabled SWE — Near-Launch Mobile App" ($55/hr, 20 connects). 70 connects remaining.
- **Gmail**: 1 new rejection (GitLab). Zero interviews yet.

### PREVIOUS SESSION (2026-03-31)
- **+1,086 APPS** (2,588 → 3,181) across 103 companies
- **Ashby**: 245/250 (98%), **Greenhouse**: 205/250 (82%), **Lever**: 120/125 (96%)
- Indeed full pagination unlocked, board discovery +5,655 new jobs, 1 Upwork proposal

### ACTIVE LEADS
1. **Aryan C. via Upwork** — GitHub & Stripe SME courses. Sent course list (7 courses) + SME guidelines PDF. Needs: (a) reply on Upwork, (b) 1-min audition video reading C# script from PDF, MP4 on Google Drive. Pay: $200-360/course. Course review agent pipeline exists at `J:\github-SME\`.
2. **Upwork: Claude AI Implementation Consultant — Law Firm** — Proposal submitted 2026-03-31. $50-80/hr. Texas law firm using Claude Team plan. Monitor for response.
3. **Hudson Manpower** — GenAI role, follow-up sent 2026-03-19, no response. Monitor mmichels88@gmail.com.
4. **WinCo Foods** — Sr. Middleware Developer, Phoenix. No response. Monitor mmichels88@gmail.com.

## YOUR JOB
1. Run fresh search cycles to find new jobs
2. Apply to every viable job (score >= 60) automatically
3. Track all applications in SQLite
4. Prioritize: Ashby (98% success) > Lever (96%) > Greenhouse (82%) > Indeed > Upwork
5. Never stop. If one application fails, move to the next.
6. ALWAYS write personalized cover letters for each application.
7. ALWAYS fetch full job descriptions for scoring — never score title-only.
8. Score and apply Anduril + SpaceX jobs (3,000+ unprocessed)
9. Monitor Upwork for <=10 connect jobs and submit proposals immediately
10. Monitor Gmail for interview responses — expect first responses week of 2026-03-31

## KEY STATS (as of 2026-03-31)
- **Total applied**: 5,020+
- **Apply failed**: ~516
- **Total jobs in DB**: 24,700+
- **Ashby success rate**: 99%
- **Greenhouse success rate**: 97% (653/700 across all batches, 100% on Anduril/SpaceX)
- **Lever success rate**: 91% with Wraith native
- **Indeed**: 190 new jobs via Chrome scrape (full pagination unlocked)
- **Rejections received**: ~29+
- **Zero interviews yet** — most apps <1 week old, expect responses this week
- **Upwork**: 2 active proposals (Claude Law Firm + AI SWE Mobile App), 70 connects remaining

## EXECUTION
```powershell
# Always use this for PowerShell:
powershell -ExecutionPolicy Bypass -Command { your commands here }
# Or for scripts:
powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
```

## KEY FILES
- `J:\job-hunter-mcp\WRAITH_BUGS.md` — **Single consolidated Wraith bug report** (BUG-9 FIXED, BUG-10 solved)
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
1. **HTTP APIs** — PRIMARY for scraping (no browser needed, fastest)
   - Greenhouse: `boards-api.greenhouse.io/v1/boards/{company}/jobs` (public REST, 150 workers proven)
   - Ashby: `jobs.ashbyhq.com/api/non-user-graphql` (public GraphQL — use `jobPostings` not `teams.jobs`)
   - Lever: `api.lever.co/v0/postings/{company}` (public REST)
2. **Wraith (wraith-browser)** — Lever full pipeline, CDP Greenhouse/Ashby pipeline
   - MCP server: `.mcp.json` configured with FlareSolverr + CDP env
   - **Binary**: `J:\wraith-browser\target\release\wraith-browser.exe` (rebuilt 2026-03-31 with BUG-9 fix)
   - Lever: FULL PIPELINE (board scrape + click nav + apply form) via native renderer
   - Greenhouse: CDP fill/upload/select/custom dropdown ALL WORK (BUG-7 FIXED). Embed URLs work (BUG-2 fixed).
   - Ashby: CDP board + click nav + apply form ALL WORK
   - Indeed: **Needs FlareSolverr escalation** — native engine detects CF, escalates to FlareSolverr. Requires `WRAITH_FLARESOLVERR=http://localhost:8191` env var.
3. **Chrome CDP (Playwright)** — Indeed scraping with logged-in session
   - Launch Chrome with `--remote-debugging-port=9222`
   - Log into Indeed via Google SSO (ridgecellrepair@gmail.com)
   - Use `indeed_chrome_scrape.py` with `filter=0` for full pagination
   - Also used for Upwork proposals (`upwork_apply.py`)
4. **FlareSolverr** — Docker on localhost:8191, CF Turnstile bypass — backup for Indeed
5. **Claude in Chrome** — For checking mmichels88 Gmail, manual interventions

## SCRIPTS (organized in scripts/ subfolder)
```
scripts/
├── swarm/          # Battle-tested batch apply + scrape pipelines
│   ├── mega_pipeline.py                (UNIFIED: --scrape --rescore --apply --all --stats --retry-failed)
│   ├── wraith_mcp_client.py            (Python MCP client — spawns Wraith, sends JSON-RPC)
│   ├── wraith_apply_swarm.py           (Wraith CDP apply swarm — replaces Playwright for apply)
│   ├── indeed_chrome_scrape.py         (NEW: Chrome CDP Indeed scrape with anti-detection, filter=0)
│   ├── indeed_sso_login.py             (NEW: FlareSolverr SSO flow + cookie export)
│   ├── indeed_cookies.json             (Exported Indeed auth cookies)
│   ├── upwork_apply.py                 (NEW: Upwork proposal submit via Chrome CDP)
│   ├── score_unscored.py               (Quick title-based scoring for new jobs)
│   ├── swarm_greenhouse_playwright.py  (Playwright fallback, --limit N --resume-from N)
│   ├── swarm_ashby_playwright.py       (Playwright fallback, --limit N --resume-from N)
│   ├── greenhouse_code_retry.py        (single-threaded IMAP code retry)
│   ├── flaresolverr_indeed.py          (Indeed CF bypass scrape — page 1 only)
│   ├── indeed_mass_scrape.py           (FlareSolverr Indeed scrape — page 1 only, use chrome version instead)
│   └── logs/                           (all swarm run logs)
├── scrape/         # Harvest/insert scripts
│   ├── discover_boards.py              (NEW: Lever/Ashby board discovery)
│   └── discover_defense_boards.py      (NEW: Defense/gov board discovery)
├── apply_one_off/  # Single-company apply scripts (historical)
├── db_utils/       # DB queries, status checks, mark_applied
├── debug/          # Probes, cover letters, screenshots
└── cookie/         # playwright_cookie_export.py, cdp_cookie_bridge.py
```

### NEW TOOL USAGE
```powershell
# Full pipeline (scrape + rescore + apply)
.venv\Scripts\python.exe scripts\swarm\mega_pipeline.py --all

# Apply via Wraith CDP (preferred — handles React dropdowns)
.venv\Scripts\python.exe scripts\swarm\wraith_apply_swarm.py --platform ashby --min-score 60 --limit 100

# Indeed scrape via logged-in Chrome (REQUIRES Chrome with --remote-debugging-port=9222)
.venv\Scripts\python.exe scripts\swarm\indeed_chrome_scrape.py --pages 5

# Upwork proposal (REQUIRES Chrome with --remote-debugging-port=9222, logged into Upwork)
.venv\Scripts\python.exe scripts\swarm\upwork_apply.py "https://www.upwork.com/jobs/JOB_URL"

# Score unscored jobs
.venv\Scripts\python.exe scripts\swarm\score_unscored.py

# Board discovery
.venv\Scripts\python.exe scripts\scrape\discover_boards.py
.venv\Scripts\python.exe scripts\scrape\discover_defense_boards.py

# Stats
.venv\Scripts\python.exe scripts\swarm\mega_pipeline.py --stats
```
Key env: `GMAIL_APP_PASSWORD="yzpn qern vrax fvta"`

## CRITICAL PATTERNS LEARNED
- **Ashby forms**: React SPA. CDP handles full pipeline. **Ashby GraphQL schema changed**: use `jobPostings { id title locationName }` not `teams { jobs }`.
- **Lever forms**: Server-rendered HTML — Wraith native renders perfectly. No Playwright needed.
- **Greenhouse via CDP**: Full pipeline. Embed URL conversion for custom career pages. Security codes auto-fetched from Gmail IMAP.
- **Indeed via Chrome**: Login required for page 2+. Use `filter=0` to bypass dedup. Randomize delays (2-8s) and shuffle query order for anti-detection. Chrome must have `--remote-debugging-port=9222`.
- **Indeed via Wraith**: Needs rebuilt binary (`wraith-browser.exe`) with FlareSolverr escalation. Native engine detects CF challenge → escalates to FlareSolverr → gets page. CDP path still blocked.
- **Upwork**: Proposals via Chrome CDP. Rate increase frequency dropdown is REQUIRED (combobox, click "Select a frequency" → "Never"). Max 10 connects per job to conserve budget.
- **Defense contractors**: Raytheon, Lockheed, Northrop, Boeing use Workday/Taleo (not GH/Ashby/Lever). Use Indeed to find their jobs. Anduril + SpaceX use Greenhouse.
- **Gmail IMAP vs API**: IMAP search has 60-90s index lag. Use message count or Gmail MCP API (no lag).
- **Parallel workers**: Multiple Wraith instances work fine. Security code jobs: SINGLE-THREADED.
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

## ACTIVE LEADS AWAITING RESPONSE
1. **Upwork: Claude AI Law Firm** — Proposal submitted 2026-03-31. $50-80/hr. Monitor ridgecellrepair@gmail.com.
2. **Aryan C. via Upwork** — GitHub SME gig. Needs audition video. Monitor ridgecellrepair@gmail.com.
3. **Hudson Manpower** — GenAI / ML AI / Data Scientist. Follow-up sent 2026-03-19. Monitor mmichels88@gmail.com.
4. **WinCo Foods** — Sr. Middleware Developer, Phoenix. Monitor mmichels88@gmail.com.
5. **All 3,181 applications** — Monitor ridgecellrepair@gmail.com. Expect first responses by 2026-04-01.

## NEXT IMMEDIATE TARGETS
1. **Score + apply Anduril/SpaceX jobs** — 3,000+ unscored, likely hundreds of viable SE/AI roles
2. **Continue Indeed Chrome scrape** — add more queries, defense-specific terms
3. **Upwork proposals** — watch for <=10 connect jobs, submit immediately (90 connects left)
4. **Monitor both Gmail accounts** — expect interview responses starting 2026-04-01
5. **Retry 520 apply_failed** — many may be expired, but some recoverable with CDP
6. **Discover more Ashby/Lever boards** — try more companies
7. **PRIORITY**: Remote or Chico (95926) jobs only

## PLATFORMS COVERED vs NOT COVERED
| Platform | Status | Jobs in DB |
|----------|--------|-----------|
| Greenhouse | 110+ companies scraped, ~12,000 jobs | Including Anduril (1,769), SpaceX (1,511) |
| Ashby | 52 companies, ~2,200 jobs | Snowflake, Vanta, Ramp, Notion, Deel, Docker, Plaid, etc. |
| Lever | 31 companies, ~2,500 jobs | Palantir (233), Shield AI, Veeva, etc. |
| Indeed | 35 queries x 5 pages, ~940 jobs | Full pagination via Chrome login + filter=0 |
| Upwork | 1 proposal submitted, 90 connects | Watch for <=10 connect AI/Claude jobs |
| LinkedIn | Not scraped, needs auth + anti-bot | HARD |
| Workday | Not scraped (Raytheon, Lockheed, Boeing) | Enterprise companies — use Indeed |
| Wellfound | Not scraped, has public API | Startups |

## WRAITH (WRAITH-BROWSER) — CONFIG
- **Binary**: `J:\wraith-browser\target\release\wraith-browser.exe` (rebuilt 2026-03-31 with BUG-9 fix)
- **OLD Binary**: `openclaw-browser.exe` — DEPRECATED, do not use
- **Version**: 0.1.0
- **CDP**: COMPILED AND WORKING
- **MCP config**: `J:\job-hunter-mcp\.mcp.json` (FlareSolverr + CDP env vars, points to wraith-browser.exe)
- **FlareSolverr**: Docker on `localhost:8191` — Indeed CF bypass via escalation
- **Stealth**: 19 evasions, Chrome TLS fingerprint
- **Bug tracking**: `WRAITH_BUGS.md` (BUG-9 FIXED, BUG-10 solved via login, 0 open blocking bugs)

## MATT'S KEY PROJECTS FOR COVER LETTERS
- **Wraith Browser**: 27K lines Rust, AI-driven browser automation, agent orchestration
- **Kalshi Weather Bot**: 20x returns, 4 beta testers, ML prediction + autonomous trading
- **OpenClaw**: AI inference fleet, distributed model serving
- **10+ MCP Servers**: Production Model Context Protocol integrations
- **LatchPac Validator 3000**: ESP32-S3 production test fixture, 120VAC, SWD programming, opto-isolated
- **PID Controller**: Custom implementation on GitHub
- **Industrial Sensors QA**: Compas Engineering — liquid level switches, ERECTA SWITCH
