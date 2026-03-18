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
