# Upwork Proposal Automation Skill

## Overview
Automate Upwork job proposal submissions using Claude in Chrome browser automation. This workflow has been proven working and successfully submitted proposals.

## Prerequisites
- Must be logged into Upwork in Chrome
- Upwork profile must exist (General profile is fine)
- Need sufficient Connects (15 per proposal for most jobs)

## Workflow: Submit Proposal (PROVEN WORKING)

### Step 1: Navigate to Job
```
Claude in Chrome:navigate(tabId, "https://www.upwork.com/jobs/{jobSlug}")
```
Wait 3 seconds for page load. The job details page shows rate range, project details, and "Apply now" button.

### Step 2: Click Apply Now
Use `Claude in Chrome:find("Apply now button")` or click the green "Apply now" button in the sidebar (typically at coordinates ~1192, 126).

### Step 3: Fill Hourly Rate
The rate field is pre-populated with your profile rate ($85/hr). To change:
```
Claude in Chrome:find("hourly rate input")
Claude in Chrome:form_input(ref, tabId, "85")
```

### Step 4: Set Rate Increase Frequency (REQUIRED)
This field caused validation errors when missed. Must be set:
```
Claude in Chrome:find("rate increase frequency dropdown")
```
Click the dropdown and select "Never" from the options. This is a combobox, not a regular select.

**Pattern that works:**
1. Click the "Select a frequency" dropdown
2. Wait for options to appear
3. Click "Never" in the dropdown list

### Step 5: Fill Cover Letter
```
Claude in Chrome:find("Cover Letter text area")  → returns ref_348 (typical)
Claude in Chrome:form_input(ref_348, tabId, "Your cover letter text here")
```
The cover letter field is a standard textarea — `form_input` works directly, no clipboard hack needed.

### Step 6: Submit
```
Claude in Chrome:find("Send proposal submit button")  → returns ref_439 (typical)
Claude in Chrome:computer(action="left_click", ref=ref_439)
```
Wait 3-4 seconds. Upwork redirects to the Proposals page with "Your proposal was submitted" confirmation.

## Key Details
- Rate: $85/hr (profile default), $76.50 after 10% Upwork fee
- Connects: 15 per proposal (most jobs), 0 remaining after submission
- Profile: General profile
- Confirmation URL pattern: `upwork.com/nx/proposals/{proposalId}?success`

## Proposal Insights (from confirmation page)
After submission, Upwork shows:
- Total proposals count
- Average bid amount
- Number shortlisted
- Number messaged
- Your bid rank

## Cover Letter Template for AI/Infrastructure Roles
```
Hi — this role is an exact match for my current work. I build and deploy production LLM infrastructure daily.

What I bring:
• Built production MCP servers in Python and Rust for Claude Code integration
• Deployed Ollama + Open WebUI inference stacks with Prometheus/Grafana monitoring
• GPU inference infrastructure: Tesla P40 fleet with Docker container orchestration
• CI/CD pipeline integration with automated testing and deployment safety gates
• Direct experience with OpenAI, Anthropic/Claude, LangChain, and LlamaIndex
• Python SDK and Node SDK integration, FastAPI services, Docker/Kubernetes deployments

I'm US-based (California), available immediately, and comfortable working async.

— Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655
```

## Connects Management
- Free connects replenish monthly
- 15 connects per application (standard)
- Buy more at: Upwork settings → Connects
- Current balance: 0 (after 2 proposals submitted this session)

## Known Issues
- Capital One Shopping browser extension popup appears — close with X or Escape
- Rate increase dropdown is REQUIRED even though it looks optional — always set to "Never"
- Claude in Chrome:find works reliably on Upwork (unlike LinkedIn's shadow DOM)
- ref IDs are stable within a page session but change on reload
