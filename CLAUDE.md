# CLAUDE.md — Job Hunter Autonomous Agent

## READ FIRST
Read `HANDOFF.md` for full context, then `skills/SKILL.md` for platform docs.

## ONE-LINER
```powershell
powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
```

## WHAT THIS PROJECT DOES
Autonomous job hunting system. Searches multiple job APIs, scores matches with AI,
tracks everything in SQLite, and applies via browser automation.

## HANDOFF PROTOCOL
- ALWAYS read HANDOFF.md and recent memory files BEFORE diagnosing any issue
- Trust prior session findings — do not re-diagnose bugs already patched
- Update HANDOFF.md at end of session with current state, blockers, and next steps
- When continuing from a prior session, summarize what you read before acting

## DIAGNOSIS DISCIPLINE
- Investigate the actual error before suggesting reinstalls or generic fixes
- For Windows spawn/ENOENT errors: check shim file extensions (.exe vs shell scripts) FIRST
- Do not assume a dependency is missing until you've verified with `where`/`which`
- Read error messages and stack traces carefully before proposing solutions

## TOOLING PREFERENCES
- DO NOT use Playwright unless explicitly requested or no alternative exists
- Prefer Wraith browser MCP for scraping/browser automation
- Chrome CDP (via Playwright connect_over_cdp) is acceptable for Upwork proposals where Wraith can't auth
- For Unraid deployments: use plain `docker run`, not docker-compose (busybox shell limitation)

## OUTPUT DISCIPLINE
- Keep responses concise; avoid long explanations after task completion
- When hitting token limits, summarize and offer to continue rather than retrying full output
- Write detailed output, logs, and analysis to files instead of chat when possible
- Checkpoint progress to HANDOFF.md during long-running work

## CRITICAL RULES
1. Always use `-ExecutionPolicy Bypass` for PowerShell
2. Always write scripts to .ps1 files instead of inline (escape issues)
3. Always `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` in Python
4. Python venv: `J:\job-hunter-mcp\.venv\Scripts\python.exe`
5. DB: `C:\Users\Matt\.job-hunter-mcp\jobs.db`
6. Resume: `C:\Users\Matt\Downloads\matt_gates_resume_ai.docx`
7. Never stop applying. If one fails, move to next.
8. Verbose logging on everything.
9. UAC is disabled. Admin PowerShell spawns clean.

## APPLY PRIORITY
Lever > Greenhouse > Indeed redirect > Upwork > LinkedIn Easy Apply (hardest)

## FORM DATA
Name: Matt Gates | Email: ridgecellrepair@gmail.com | Phone: 5307863655
LinkedIn: linkedin.com/in/matt-michels-b836b260 | GitHub: github.com/suhteevah
Location: Chico CA | US Work Auth: Yes | Remote: Yes | Years: 10 | English: Native
