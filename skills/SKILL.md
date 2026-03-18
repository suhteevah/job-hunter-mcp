# Job Hunter Autonomous Agent — Claude Code Skill

## MISSION
Autonomously find, apply to, and track AI/ML/DevOps/QA engineering jobs until Matt Gates gets hired.
Revenue target: 30 days or we're homeless. This runs 24/7 on kokonoe (Windows 11, i9-11900K, RTX 3070 Ti).

## QUICK START (Claude Code)
```powershell
powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
```

## SYSTEM LAYOUT
- **Job Hunter MCP**: `J:\job-hunter-mcp\` (Python, 15 tools, SQLite DB)
- **Database**: `C:\Users\Matt\.job-hunter-mcp\jobs.db`
- **Logs**: `C:\Users\Matt\.job-hunter-mcp\job_hunter.log`
- **Resume (AI v2)**: `C:\Users\Matt\Downloads\matt_gates_resume_ai.docx` (built 2026-03-17)
- **Resume (Sales)**: `C:\Users\Matt\Downloads\Matt Gates Resume SalesAccountManager.docx`
- **Skills**: `J:\job-hunter-mcp\skills\{linkedin,upwork,dice}\SKILL.md`
- **Scheduler**: Windows Task `JobHunterMCP` every 4hr
- **Python venv**: `J:\job-hunter-mcp\.venv\`
- **RapidAPI Key**: In `J:\job-hunter-mcp\secrets.json` (~186 req/month remaining)

## MATT'S INFO
- **Name**: Matt Michels (LinkedIn) / Matt Gates (business)
- **Phone**: (530) 786-3655 / 5307863655
- **Email (LinkedIn)**: mmichels88@gmail.com
- **Email (business)**: ridgecellrepair@gmail.com
- **LinkedIn**: https://www.linkedin.com/in/matt-michels-b836b260/
- **GitHub**: github.com/suhteevah
- **Location**: Chico, CA (Magalia technically)
- **Company**: Ridge Cell Repair LLC
- **Title**: Technical Director / AI Infrastructure Engineer
- **Availability**: Immediate, remote preferred, open to contract or FT

## TARGET ROLES (priority order)
1. AI/ML Engineer / AI Infrastructure ($100K-200K)
2. MCP Server Developer / AI Agent Architect ($90K-160K)
3. DevOps Engineer ($90K-150K)
4. QA Automation Engineer ($80K-140K)
5. Full-Stack Developer with AI focus ($80K-130K)
6. Technical Consultant / Freelance ($50-150/hr)

## AUTONOMOUS WORKFLOW

### Phase 1: Search (every 4hr via scheduler, or on-demand)
```powershell
cd J:\job-hunter-mcp
.venv\Scripts\activate
python scheduler.py  # Runs search cycle, scores jobs, stores in DB
```

### Phase 2: Review top jobs
```python
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute("SELECT fit_score, title, company, url, source FROM jobs WHERE status NOT IN ('applied','rejected','expired') ORDER BY fit_score DESC LIMIT 20")
for r in c.fetchall():
    print(f"  {r[0]:5.0f} | {r[1][:50]:50s} | {(r[2] or '')[:20]:20s} | {r[4]}")
```

### Phase 3: Apply (platform-specific)

#### Lever (leotechnologies, etc.) — BEST, standard HTML forms
1. Navigate to `https://jobs.lever.co/{company}/{id}/apply`
2. Claude in Chrome:find("Full name") → form_input
3. Claude in Chrome:find("Email") → form_input  
4. Claude in Chrome:find("Phone") → form_input
5. Claude in Chrome:find("Resume") → file_upload with `C:\Users\Matt\Downloads\matt_gates_resume_ai.docx`
6. Claude in Chrome:find("LinkedIn") → form_input with LinkedIn URL
7. Claude in Chrome:find("Submit") → click

#### Greenhouse — Standard HTML, similar to Lever
Same pattern. URL: `boards.greenhouse.io/{company}/jobs/{id}`

#### Upwork — PROVEN WORKING (see skills/upwork/SKILL.md)
1. Navigate to job URL → Apply Now → fill rate ($85/hr)
2. Set rate increase to "Never" (REQUIRED)
3. Fill cover letter textarea
4. Submit (costs 15 connects per application)
5. Current connects: 0 (need to buy more or wait for monthly refresh)

#### LinkedIn Easy Apply — HARDEST (see skills/linkedin/SKILL.md)
- Shadow DOM blocks ALL CSS/XPath selectors
- `elementsFromPoint` finds clickable elements on the job page
- Modal overlay is INVISIBLE to DOM queries
- PowerShell SendInput clicks at screen coordinates for modal buttons
- Tab + clipboard paste for form fields inside modal
- Multi-step: Contact → Resume → Screening Questions → Work Auth → Review → Submit

#### Indeed — "Apply on company site" redirects to employer
Click the button, follow redirect, fill employer's form (usually Lever/Greenhouse/Workday)

#### DailyRemote — Aggregator, redirects to LinkedIn/employer
Follow the Apply Now link, handle the redirect

#### Flexionis — PURE AGGREGATOR, NO APPLY. Skip. Find original source.

#### Dice — Direct apply but jobs expire fast. Need Dice account.

### Phase 4: Track status
```python
# After applying:
c.execute("UPDATE jobs SET status='applied', notes='...' WHERE id=?", (job_id,))
# Mark expired:
c.execute("UPDATE jobs SET status='expired' WHERE id=?", (job_id,))
```

## COVER LETTER TEMPLATE (AI/Infrastructure roles)
```
Hi — this role is an exact match for my current work. I build and deploy production LLM infrastructure daily.

What I bring:
- Built production MCP servers in Python and Rust for Claude Code integration
- Deployed Ollama + Open WebUI inference stacks with Prometheus/Grafana monitoring
- GPU inference infrastructure: Tesla P40 fleet with Docker container orchestration
- CI/CD pipeline integration with automated testing and deployment safety gates
- Direct experience with OpenAI, Anthropic/Claude, LangChain, and LlamaIndex
- Python SDK and Node SDK integration, FastAPI services, Docker/Kubernetes deployments

I'm US-based (California), available immediately, and comfortable working async.

— Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655
```

## PLATFORM DISCOVERY
When Flexionis/aggregator jobs have no apply button, search for the original:
```
web_search: "{job title}" "{company}" apply lever OR greenhouse OR careers
```

## WINDOWS AUTOMATION NOTES
- UAC is disabled — admin PowerShell spawns without prompts
- Use `-ExecutionPolicy Bypass` on all PowerShell invocations
- Escape special chars: write to .ps1 files instead of inline commands
- Unicode: always `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` in Python
- Chrome window: L=680 T=267 R=2532 B=1302 (1852x1035), Chrome height=129px
- Screen: 2560x1440 at 100% DPI, no scaling
- Viewport coords → screen: screenX = windowLeft + viewportX, screenY = windowTop + 129 + viewportY

## DB SCHEMA
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    source TEXT, source_id TEXT,
    title TEXT, company TEXT, url TEXT,
    location TEXT, salary TEXT, job_type TEXT, category TEXT,
    description TEXT, tags TEXT,
    date_posted TEXT, date_found TEXT,
    fit_score REAL, fit_reason TEXT,
    status TEXT DEFAULT 'new',  -- new/saved/applied/interviewing/rejected/expired/offer
    notes TEXT, cover_letter TEXT, applied_date TEXT
);
```

## CURRENTLY APPLIED (as of 2026-03-17)
1. Upwork AI Infrastructure Engineer — LLM Reliability & Observability ($85/hr) ✅
2. Flowmentum AI/DevOps Engineer — Test Automation & Telemetry ($102-150K) ✅

## NEXT TARGETS (ready to apply)
1. LeoTech AI/LLM Evaluation Engineer ($135-160K) — Lever form at jobs.lever.co/LEOTechnologies/1847504a-c707-443a-9554-eb154ef1cd60/apply
2. Allergan Aesthetics Sr QA Software Engineer ($121-230K) — Indeed → company site redirect
