# CLAUDE CODE HANDOFF — Autonomous Job Hunter
# Read this FIRST. Then read J:\job-hunter-mcp\skills\SKILL.md for full details.
# Last updated: 2026-03-17

## IMMEDIATE CONTEXT
Matt Gates is job hunting. 30 days to generate revenue or we're homeless.
Two applications submitted. ~200 jobs tracked. Scheduler running every 4hr.
The machine never sleeps.

## YOUR JOB
1. Run fresh search cycles to find new jobs
2. Apply to every viable job (score >= 60) automatically
3. Track all applications in SQLite
4. Prioritize: Lever > Greenhouse > Indeed > Upwork > LinkedIn Easy Apply
5. Never stop. If one application fails, move to the next.

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

## PYTHON VENV
```powershell
$VENV = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
& $VENV -c "print('ok')"
```

## BROWSER AUTOMATION PRIORITY
1. **Claude in Chrome** — works on standard sites (Lever, Greenhouse, Indeed, Upwork)
   - find() + form_input() + file_upload() + computer(left_click)
   - JavaScript injection via javascript_tool for tricky cases
2. **Kapture** — works for LinkedIn initial page elements via elementsFromPoint
3. **PowerShell SendInput** — last resort for LinkedIn Easy Apply modals

## CRITICAL PATTERNS LEARNED
- LinkedIn shadow DOM: elementsFromPoint + clipboard paste + Tab navigation
- LinkedIn Easy Apply modals: invisible to all DOM queries, only keyboard and raw mouse clicks work
- Lever/Greenhouse: standard HTML, Claude in Chrome find/form_input works perfectly
- Always write PowerShell to .ps1 files to avoid escape issues
- Always add `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` in Python
- PowerShell `&&` doesn't work — use `;` as separator
- Chrome window position: L=680 T=267, chrome height=129px, viewport=1836x906

## CONTACT INFO FOR FORMS
- Full name: Matt Gates (or Matt Michels on LinkedIn)
- Email: ridgecellrepair@gmail.com
- Phone: 5307863655
- LinkedIn: https://www.linkedin.com/in/matt-michels-b836b260/
- GitHub: https://github.com/suhteevah
- Location: Chico, CA
- Work authorization: Yes (US citizen)
- Remote: Yes
- Background check: Yes
- Drug test: Yes
- Years of experience: 10
- English proficiency: Native

## WHAT'S BEEN DONE (2026-03-17)
- Upwork AI Infra Engineer proposal SUBMITTED ($85/hr)
- Flowmentum AI/DevOps LinkedIn Easy Apply SUBMITTED ($102-150K)
- LinkedIn profile: headline + about section updated
- AI resume v2 built and uploaded to LinkedIn
- 3 Claude Code skills written
- 200+ jobs in DB, scheduler active

## NEXT IMMEDIATE TARGETS
1. LeoTech AI/LLM Evaluation ($135-160K) — Lever: jobs.lever.co/LEOTechnologies/1847504a-c707-443a-9554-eb154ef1cd60/apply
2. Allergan Sr QA ($121-230K) — Indeed → company site
3. Run fresh search, find more live Lever/Greenhouse postings
4. Apply to ALL viable matches
