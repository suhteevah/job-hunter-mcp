# job-hunter-mcp

Autonomous job hunting system powered by Wraith Browser (MCP), Playwright, and AI scoring. Searches multiple job APIs, scores matches against resume, tracks everything in SQLite, and applies via browser automation.

## Stats (as of 2026-03-22)

- **502 applications submitted**
- **8,876 jobs tracked** across Greenhouse, Ashby, Lever, Indeed
- **97.5% Ashby success rate** (159/163)
- **Zero human intervention** — fully autonomous apply pipeline

## Architecture

```
Phase 1: Scrape                    Phase 2: Apply
┌─────────────────┐               ┌──────────────────────┐
│ Greenhouse REST  │──┐            │ Wraith CDP (GH/Ashby)│
│ Ashby GraphQL    │  ├─► SQLite ─►│ Wraith Native (Lever)│
│ Lever REST       │  │   (score)  │ Playwright (fallback)│
│ Indeed (Wraith)  │──┘            └──────────────────────┘
└─────────────────┘                         │
                                   ┌────────▼────────┐
                                   │ Dedup + Verify   │
                                   │ Cover Letter Gen │
                                   │ Security Codes   │
                                   └─────────────────┘
```

## Platform Support

| Platform | Scrape | Apply | Method |
|----------|--------|-------|--------|
| Greenhouse | REST API (150 workers) | CDP or Playwright | Full pipeline, React dropdown support |
| Ashby | GraphQL API | CDP or Playwright | 97.5% success rate |
| Lever | REST API | Wraith native | Server-rendered, no Playwright needed |
| Indeed | Wraith native (CF bypass) | Redirect to ATS | Search + redirect to company apply page |
| LinkedIn | Not supported | Not supported | Anti-bot blocks automation |

## Wraith Browser Integration

Uses [Wraith (openclaw-browser)](https://github.com/suhteevah/openclaw-browser) as the primary browser automation engine via MCP (Model Context Protocol).

### Key Capabilities
- **CDP Engine**: Chrome DevTools Protocol for React SPAs (Greenhouse, Ashby)
- **Native Engine**: Rust HTTP renderer for server-rendered sites (Lever, Indeed)
- **Engine Switching**: Seamless native <-> CDP transitions
- **Cloudflare Bypass**: TLS fingerprinting passes CF bot detection
- **Swarm Mode**: Parallel fan-out, dedup tracking, submission verification, built-in playbooks

### Swarm Tools
- `swarm_fan_out` — Visit multiple URLs in parallel
- `swarm_dedup_check/record/stats` — Duplicate application tracking
- `swarm_verify_submission` — Post-submit success/failure detection
- `swarm_run_playbook` — Execute YAML automation scripts (greenhouse-apply, ashby-apply, lever-apply, indeed-search)

## Setup

### Prerequisites
- Python 3.11+ with venv
- Wraith Browser (openclaw-browser) compiled with CDP support
- Chrome installed (for CDP engine)
- FlareSolverr Docker container (optional, Indeed backup)

### Install

```powershell
git clone https://github.com/suhteevah/job-hunter-mcp.git
cd job-hunter-mcp
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### Run

```powershell
powershell -ExecutionPolicy Bypass -File J:\job-hunter-mcp\launch_hunter.ps1
```

### Key Files

```
HANDOFF.md              # Full context for Claude Code sessions
WRAITH_BUGS.md          # Wraith bug tracking (single source of truth)
skills/SKILL.md         # Platform docs, DB schema, workflow
launch_hunter.ps1       # PowerShell entry point
scripts/
├── swarm/              # Battle-tested batch apply + scrape pipelines
├── apply_one_off/      # Single-company apply scripts
├── scrape/             # Harvest/insert scripts
├── db_utils/           # DB queries, status checks
├── debug/              # Probes, cover letters, screenshots
└── cookie/             # Cookie export/bridge utilities
```

### Database

SQLite at `C:\Users\Matt\.job-hunter-mcp\jobs.db` — tracks all jobs with fit scores, application status, and platform metadata.

## Form Data

| Field | Value |
|-------|-------|
| Name | Matt Gates |
| Email | ridgecellrepair@gmail.com |
| Phone | 5307863655 |
| LinkedIn | linkedin.com/in/matt-michels-b836b260 |
| GitHub | github.com/suhteevah |
| Location | Chico, CA |
| Work Auth | US Citizen |
| Remote | Yes |
| Experience | 10 years |

## License

This project is open source and available under the [MIT License](LICENSE).

---

---

---

## Support This Project

If you find this project useful, consider buying me a coffee! Your support helps me keep building and sharing open-source tools.

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal)](https://www.paypal.me/baal_hosting)

**PayPal:** [baal_hosting@live.com](https://paypal.me/baal_hosting)

Every donation, no matter how small, is greatly appreciated and motivates continued development. Thank you!
