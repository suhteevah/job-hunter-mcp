# Job Hunter Autonomous Launcher
# Run: powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
# Or from Claude Code: just run this script

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Job Hunter Agent"

# Paths
$HUNTER_DIR = "J:\job-hunter-mcp"
$DB_PATH = "$env:USERPROFILE\.job-hunter-mcp\jobs.db"
$LOG_PATH = "$env:USERPROFILE\.job-hunter-mcp\job_hunter.log"
$RESUME_PATH = "$env:USERPROFILE\Downloads\matt_gates_resume_ai.docx"
$VENV = "$HUNTER_DIR\.venv\Scripts\python.exe"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LOG_PATH -Value $line -Encoding UTF8
}

function Run-SearchCycle {
    Log "=== STARTING SEARCH CYCLE ==="
    Set-Location $HUNTER_DIR
    & $VENV scheduler.py 2>&1 | ForEach-Object { Log $_ }
    Log "=== SEARCH CYCLE COMPLETE ==="
}

function Get-TopJobs {
    param([int]$Limit = 20, [int]$MinScore = 60)
    $py = @"
import sqlite3, os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute("SELECT id, fit_score, title, company, url, source, status FROM jobs WHERE fit_score >= ? AND status NOT IN ('applied','rejected','expired') ORDER BY fit_score DESC LIMIT ?", ($MinScore, $Limit))
rows = [{"id":r[0],"score":r[1],"title":r[2],"company":r[3],"url":r[4],"source":r[5],"status":r[6]} for r in c.fetchall()]
print(json.dumps(rows))
db.close()
"@
    $result = & $VENV -c $py 2>$null
    return $result | ConvertFrom-Json
}

function Update-JobStatus {
    param([string]$JobId, [string]$Status, [string]$Notes = "")
    $py = @"
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute("UPDATE jobs SET status=?, notes=?, applied_date=datetime('now') WHERE id=?", ("$Status", "$Notes", "$JobId"))
db.commit()
print(f"Updated {c.rowcount} rows: {c.lastrowid}")
db.close()
"@
    & $VENV -c $py 2>$null
}

function Get-Stats {
    $py = @"
import sqlite3, os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(os.path.expanduser('~/.job-hunter-mcp/jobs.db'))
c = db.cursor()
c.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
stats = {r[0] or 'new': r[1] for r in c.fetchall()}
c.execute("SELECT COUNT(*) FROM jobs")
stats['total'] = c.fetchone()[0]
c.execute("SELECT MAX(fit_score) FROM jobs WHERE status NOT IN ('applied','rejected','expired')")
stats['top_score'] = c.fetchone()[0] or 0
print(json.dumps(stats))
db.close()
"@
    return (& $VENV -c $py 2>$null) | ConvertFrom-Json
}

function Draft-CoverLetter {
    param([string]$Title, [string]$Company)
    $letter = @"
Hi - this role is an exact match for my current work. I build and deploy production LLM infrastructure daily.

What I bring:
- Built production MCP servers in Python and Rust for Claude Code integration
- Deployed Ollama + Open WebUI inference stacks with Prometheus/Grafana monitoring
- GPU inference infrastructure: Tesla P40 fleet with Docker container orchestration
- CI/CD pipeline integration with automated testing and deployment safety gates
- Direct experience with OpenAI, Anthropic/Claude, LangChain, and LlamaIndex
- Python SDK and Node SDK integration, FastAPI services, Docker/Kubernetes deployments

I'm US-based (California), available immediately, and comfortable working async.

-- Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655
"@
    return $letter
}

# === MAIN ===
Log "Job Hunter Agent starting on $env:COMPUTERNAME"
Log "DB: $DB_PATH"
Log "Resume: $RESUME_PATH"
Log "Venv: $VENV"

# Verify paths
if (-not (Test-Path $VENV)) { Log "ERROR: Python venv not found at $VENV"; exit 1 }
if (-not (Test-Path $DB_PATH)) { Log "ERROR: Database not found at $DB_PATH"; exit 1 }
if (-not (Test-Path $RESUME_PATH)) { Log "WARNING: Resume not found at $RESUME_PATH" }

# Run initial search
Run-SearchCycle

# Show stats
$stats = Get-Stats
Log "Stats: $($stats | ConvertTo-Json -Compress)"

# Get top jobs
$jobs = Get-TopJobs -Limit 20 -MinScore 60
Log "Top $($jobs.Count) unapplied jobs loaded"

foreach ($job in $jobs) {
    Log "  [$($job.score)] $($job.title) @ $($job.company) [$($job.source)]"
}

Log "=== AGENT READY FOR CLAUDE CODE ==="
Log "Next steps: Apply to top jobs via browser automation"
Log "Use Claude Code with skills at J:\job-hunter-mcp\skills\"
