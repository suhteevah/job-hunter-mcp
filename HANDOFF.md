# CLAUDE CODE HANDOFF — Autonomous Job Hunter
# Read this FIRST. Then read J:\job-hunter-mcp\skills\SKILL.md for full details.
# Last updated: 2026-03-20

## IMMEDIATE CONTEXT
Matt Gates is job hunting. 27 days remaining to generate revenue.
103 applications submitted. 858 jobs tracked in DB. Scheduler running every 4hr.
Wraith browser (openclaw-browser) is NOW COMPILED with 80+ MCP tools. CF Turnstile bypass operational.
The machine never sleeps.

## YOUR JOB
1. Run fresh search cycles to find new jobs
2. Apply to every viable job (score >= 60) automatically
3. Track all applications in SQLite
4. Prioritize: Lever > Greenhouse > Indeed > Upwork > LinkedIn Easy Apply
5. Never stop. If one application fails, move to the next.
6. ALWAYS write personalized cover letters for each application.

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
- `J:\job-hunter-mcp\hudson_followup_email.txt` — Hudson Manpower follow-up (ALREADY SENT)
- `J:\job-hunter-mcp\HANDOFF_2026-03-19.md` — Detailed session notes from 2026-03-19

## PYTHON VENV
```powershell
$VENV = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
& $VENV -c "print('ok')"
```

## BROWSER AUTOMATION PRIORITY
1. **Wraith (openclaw-browser)** — PRIMARY for scraping CF-protected sites (Indeed, Glassdoor)
   - MCP server: `.mcp.json` configured, restart Claude Code to activate
   - CLI: `J:\openclaw-browser\target\release\openclaw-browser.exe`
   - 80+ MCP tools: navigate, click, fill, extract, search, vault, cache, entity graph, swarm, workflows
   - CF Turnstile bypass: 4-tier (direct→QuickJS→FlareSolverr→proxy)
   - Stealth: TLS fingerprinting, 19 evasions, behavioral simulation
   - Cache: SQLite knowledge store — every page cached, never re-fetches unnecessarily
   - Swarm: parallel browser sessions for batch scraping
   - Workflow: record apply flow once, replay with variables for each job
2. **Claude in Chrome** — works on standard sites (Lever, Greenhouse, Upwork) for APPLYING
   - find() + form_input() + file_upload() + computer(left_click)
   - JavaScript injection via javascript_tool for tricky cases
   - Still needed for form filling + file upload (resume) — Wraith is headless
3. **Kapture** — works for LinkedIn initial page elements via elementsFromPoint
4. **PowerShell SendInput** — last resort for LinkedIn Easy Apply modals

## CRITICAL PATTERNS LEARNED
- LinkedIn shadow DOM: elementsFromPoint + clipboard paste + Tab navigation
- LinkedIn Easy Apply modals: invisible to all DOM queries, only keyboard and raw mouse clicks work
- Lever/Greenhouse: standard HTML, Claude in Chrome find/form_input works perfectly
- Always write PowerShell to .ps1 files to avoid escape issues
- Always add `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` in Python
- PowerShell `&&` doesn't work — use `;` as separator
- Chrome window position: L=680 T=267, chrome height=129px, viewport=1836x906
- Indeed CAPTCHA: triggers on new searches. User must solve manually. Use random delays (2-5s) between actions.
- iCIMS portals (WinCo etc): iframe-based forms don't respond well to find()/form_input(). Use coordinate clicks.
- Greenhouse API (job-boards.greenhouse.io): /application endpoint returns 404 — must apply via browser, not API.
- Indeed "Easily Apply" uses mmichels88@gmail.com account, NOT ridgecellrepair@gmail.com.
- Gmail MCP is connected to ridgecellrepair@gmail.com. For mmichels88, use Chrome browser automation.

## CONTACT INFO FOR FORMS
- Full name: Matt Gates (or Matt Michels on LinkedIn/Indeed)
- Email: ridgecellrepair@gmail.com (primary) / mmichels88@gmail.com (Indeed)
- Phone: 5307863655
- LinkedIn: https://www.linkedin.com/in/matt-michels-b836b260/
- GitHub: https://github.com/suhteevah
- Location: Chico, CA (willing to relocate to Phoenix area)
- Work authorization: Yes (US citizen)
- Remote: Yes
- Background check: Yes
- Drug test: Yes
- Years of experience: 10
- English proficiency: Native
- Education: Some college (Associates level)

## WHAT'S BEEN DONE (2026-03-20)
- Wraith browser MCP configured (.mcp.json) — 80+ tools, CF bypass, knowledge store
- WRAITH_GAPS.md written documenting all missing features for the Wraith dev
- 6 Greenhouse apps submitted via Playwright batch automation:
  - RegScale Senior AI Engineer (PERFECT match — MCP server dev in JD!) — SUBMITTED
  - Grafana Labs Senior AI Engineer ($154-185K + RSUs) — SUBMITTED
  - Censys Sr Software Engineer, AI/LLM ($159-225K) — SUBMITTED
  - Khan Academy Sr. AI Engineer ($137-172K, 24mo) — SUBMITTED
  - OnBoard Meetings Sr Software Engineer, AI — SUBMITTED
  - Pathward AI Engineer, Senior ($86-145K) — SUBMITTED
- 8 new Greenhouse jobs discovered via Wraith DuckDuckGo search and inserted into DB
- All cover letters personalized per company/role
- FlareSolverr Docker confirmed running on port 8191
- Wraith dev notified of gaps: file upload, binary rebuild, session persistence

## WHAT'S BEEN DONE (2026-03-19)
- 100+ applications total reached
- Indeed browser automation: Sr. QA Automation Engineer @ Two95 SUBMITTED
- Indeed browser automation: Sales Engineer - Automation @ Purple Cow ($121-203K) SUBMITTED
- WinCo Foods Sr. Middleware Developer iCIMS application COMPLETED ($110-150K + 20% ESOP)
- Hudson Manpower GenAI follow-up email SENT via mmichels88 Gmail (asking 3 critical questions)
- 7 Greenhouse jobs batch-marked applied (GitLab x2, Gusto, Reddit x3, Twilio) — API returned 404, need browser followup
- Wraith (openclaw-browser) tested against Indeed — JSearch built in but RapidAPI quota exhausted (429)
- LatchPac repo reviewed — industrial automation experience documented for cover letters
- PID controller project noted for cover letters

## ACTIVE LEADS AWAITING RESPONSE
1. **Hudson Manpower** — GenAI / ML AI / Data Scientist. Follow-up sent 2026-03-19 7:26 PM. Asked about end client, comp range, W2/contract. Monitor mmichels88@gmail.com for reply.
2. **WinCo Foods** — Sr. Middleware Developer, Phoenix (remote). iCIMS application submitted. $110-150K + 20% ESOP. Monitor mmichels88@gmail.com.

## NEXT IMMEDIATE TARGETS
1. Set up FlareSolverr Docker + wraith stack for bypassing Indeed CAPTCHA/bot detection
2. Upgrade RapidAPI plan OR use wraith+FlareSolverr to replace JSearch
3. Browser-apply to the 7 Greenhouse jobs that got 404 on API (GitLab, Gusto, Reddit, Twilio)
4. Monitor mmichels88@gmail.com for Hudson Manpower and WinCo replies
5. Continue applying — 159 viable unapplied jobs in DB with scores 90-100
6. Target AI-focused companies directly: Anthropic, OpenAI, Scale AI, Anyscale, Modal

## WRAITH (OPENCLAW-BROWSER) — FULL CAPABILITY MAP
- **Binary**: `J:\openclaw-browser\target\release\openclaw-browser.exe`
- **MCP config**: `J:\job-hunter-mcp\.mcp.json` (restart Claude Code to activate)
- **Docs**: `J:\openclaw-browser\CAPABILITIES.md`, `J:\openclaw-browser\HANDOFF.md`

### Search (free, no API keys needed)
- DuckDuckGo metasearch: `openclaw-browser.exe search "query" --max-results 15`
- SearXNG (free), Remotive (free, job-specific)
- JSearch (RAPIDAPI_KEY quota exhausted for March), Adzuna, Brave (need keys)

### Scraping CF-Protected Sites (Indeed, Glassdoor)
- Tier 1: Direct fetch with rquest/BoringSSL + Chrome 131 TLS (passes Akamai, PerimeterX)
- Tier 2: QuickJS in-process JS challenge solver (~100ms)
- Tier 3: FlareSolverr for Cloudflare Turnstile (~5-10s) — NEEDS DOCKER RUNNING
- Tier 4: Fallback proxy for IP bans
- Verified: Indeed PASS, Glassdoor PASS (7,439 jobs extracted), Nike/Target/Walmart PASS

### Key MCP Tool Categories (80+ tools)
- **Navigation**: navigate, back, forward, reload, scroll, wait, wait_for_navigation
- **Interaction**: click, fill, select, type_text, hover, key_press, dom_focus
- **Extraction**: snapshot, extract (markdown), screenshot, eval_js, dom_query, pdf_extract, ocr
- **Search**: web metasearch across providers
- **Vault**: encrypted credential store (AES-256-GCM) — store Indeed/LinkedIn creds
- **Cookies**: get/set/save/load — persist sessions across runs
- **Cache**: knowledge store — search cached pages, tag, pin, find similar, domain profiles
- **Entity Graph**: track companies, relationships, merge duplicates
- **Embeddings**: semantic search across all cached content
- **Swarm**: fan_out URLs for parallel scraping (e.g., scrape 15 Greenhouse pages at once)
- **Workflow**: record an apply flow, replay with variables (e.g., different job URLs)
- **Task DAG**: orchestrate parallel subtasks with dependencies
- **MCTS Planning**: AI action planning for complex multi-step flows
- **Scripting (Rhai)**: load custom scripts that auto-execute on page patterns
- **Auth Detection**: detect login forms and auth flows automatically
- **Identity/Fingerprint**: TLS profiles, stealth evasion status
- **Network Intel**: API discovery, DNS resolution, site fingerprinting

### Job Hunting Strategy with Wraith
1. **Scrape Indeed/Glassdoor** directly (bypass CF) → extract job listings → insert into jobs.db
2. **Swarm fan-out** Greenhouse/Lever URLs → extract job details in parallel
3. **Cache everything** — never re-scrape a page that hasn't changed
4. **Entity graph** — track which companies are hiring, cross-reference across platforms
5. **Workflow record/replay** — record one Greenhouse apply flow, replay for all 15 jobs
6. **Vault** — store credentials for Indeed, LinkedIn, Upwork for automated login

## MATT'S KEY PROJECTS FOR COVER LETTERS
- **Wraith Browser**: 27K lines Rust, AI-driven browser automation, agent orchestration
- **Kalshi Weather Bot**: 20x returns, 4 beta testers, ML prediction + autonomous trading
- **OpenClaw**: AI inference fleet, distributed model serving
- **10+ MCP Servers**: Production Model Context Protocol integrations
- **LatchPac Validator 3000**: ESP32-S3 production test fixture, 120VAC, SWD programming, opto-isolated
- **PID Controller**: Custom implementation on GitHub
- **Industrial Sensors QA**: Compas Engineering — liquid level switches, ERECTA SWITCH
