"""Draft cover letters for top jobs and queue them."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src import db

MATT_SIG = """Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655
ridgecellrepair@gmail.com"""

# === 1. IgniteTech QA Automation - $100K ===
cl1 = f"""Dear Hiring Team,

I'm writing to express my strong interest in the Quality Assurance Automation Engineer position at IgniteTech. Your focus on embedding GenAI into every stage of the QA lifecycle aligns directly with my experience building AI-powered automation systems.

Over the past several years, I've built production test automation frameworks using Selenium, Playwright, and Python-based tooling. At Ridge Cell Repair LLC, I've developed AI agent systems that autonomously execute complex workflows - including automated testing pipelines, CI/CD integrations, and monitoring dashboards. My recent work includes building MCP (Model Context Protocol) servers for Claude that orchestrate multi-step automated processes, which maps directly to IgniteTech's vision of AI-driven QA.

Key qualifications that match your needs:
- Production experience with Python test automation, CI/CD pipelines, and Docker/Kubernetes deployments
- Built AI agent architectures that simulate user behaviors and generate test scenarios - exactly the GenAI-first approach IgniteTech is pioneering
- Strong background in API testing, regression suites, and end-to-end quality frameworks
- Hands-on with LLM integration, prompt engineering, and agentic workflow design

I'm particularly excited about IgniteTech's approach to using AI for predictive defect detection and intelligent test case generation. This is the future of QA, and I want to help build it.

I'm available immediately for a remote position and can demonstrate my automation frameworks and AI agent work in an interview.

{MATT_SIG}"""

db.queue_email(
    job_id="008486be4f804371",
    email_type="cover_letter",
    to_address="apply@ignitetech.com",
    subject="Application: QA Automation Engineer - Matt Gates",
    body=cl1
)
print("1. QUEUED: IgniteTech QA Automation ($100K)")

# === 2. Empower Professionals AI/ML Engineer (mentions MCP!) ===
cl2 = f"""Dear Hiring Team,

I'm applying for the AI/ML Engineer position. Your requirements read like a description of my daily work - LLMs, AI Agents, MCP servers, FastAPI, Docker, and Kubernetes are my core toolkit.

Relevant experience that directly matches your requirements:
- Built production MCP (Model Context Protocol) servers in both Python and Rust, including tool integration for Claude Code - this is my specialty
- Developed AI agent architectures using agentic workflows with multi-step orchestration, exactly the pattern LangChain/LangGraph enables
- Production FastAPI services deployed in Docker containers with Kubernetes orchestration
- Extensive prompt engineering experience across Claude, GPT, and open-source LLMs (Ollama fleet management)
- Built complete AI infrastructure: GPU inference servers (Tesla P40 fleet), model deployment pipelines, and monitoring stacks

I've also deployed Ollama + Open WebUI stacks for clients, built automated email pipelines with AI-powered classification, and created SEO audit systems using LLM analysis. My background spans both the ML engineering side and the DevOps/infrastructure side, which means I can build the agents AND deploy them reliably.

I'm available immediately for remote contract work and can start contributing from day one.

{MATT_SIG}"""

db.queue_email(
    job_id="1b13448deb463b14",
    email_type="cover_letter",
    to_address="apply@empowerprofessionals.com",
    subject="Application: AI/ML Engineer (Remote) - Matt Gates",
    body=cl2
)
print("2. QUEUED: Empower Professionals AI/ML Engineer")

# === 3. Flowmentum AI/DevOps Engineer ===
cl3 = f"""Dear Hiring Team,

I'm interested in the AI/DevOps Engineer position focused on Test Automation & Telemetry. My background combines AI infrastructure engineering with DevOps automation - exactly the intersection this role requires.

What I bring to this role:
- Built and maintain a fleet of GPU inference servers with automated monitoring, telemetry collection, and health checks using Prometheus/Grafana stacks
- Developed AI agent systems that autonomously execute complex workflows, generate behavioral signals, and monitor system reliability - directly matching your described infrastructure
- Production CI/CD pipeline design with Docker, automated testing, and deployment automation
- Python and Rust backend development with extensive API integration experience
- Experience with LLM-powered testing frameworks that simulate user interactions and validate system behavior

My recent work includes building an autonomous job hunting pipeline with SMTP/IMAP automation, SQLite tracking, and scheduled execution - demonstrating the kind of end-to-end automated system your team builds. I'm comfortable operating independently in evolving AI-driven environments and collaborating with senior stakeholders.

Available immediately for remote work.

{MATT_SIG}"""

db.queue_email(
    job_id="7e8771cc616c9234",
    email_type="cover_letter",
    to_address="apply@flowmentum.com",
    subject="Application: AI/DevOps Engineer (Test Automation & Telemetry) - Matt Gates",
    body=cl3
)
print("3. QUEUED: Flowmentum AI/DevOps Engineer")

# === 4. GenAI Support Engineer - LLM Agents & MCP ($48-52/hr) ===
cl4 = f"""Dear Hiring Team,

I'm applying for the GenAI Support Engineer position focused on LLM Agents & MCP Servers. This role is an exact match for my current work - I build MCP servers and AI agent systems professionally.

Direct experience matching your requirements:
- Built production MCP servers (Python and Rust) for Claude Code integration, including tool schema design, server creation, and enterprise deployment
- Developed AI agent architectures for enterprise automation and workflow orchestration across 7+ specialized agents
- REST API and webhook integrations across Gmail, Slack, and custom backend services
- System monitoring, log analysis, and tool interaction debugging for high-availability AI systems
- 5+ years Python development with deep experience in the AI/LLM ecosystem

Current MCP server projects include:
- openclaw-admin-mcp: Production Rust MCP server for fleet management
- job-hunter-mcp: Python MCP server with 15 tools for autonomous job searching, email automation, and application tracking
- Custom deployment skill servers for AI infrastructure provisioning

I understand the MCP framework at a deep level - not just using it, but building servers, designing tool schemas, and integrating with enterprise systems. I'm available immediately for the 6-month contract.

{MATT_SIG}"""

db.queue_email(
    job_id="b17face69fe399d6",
    email_type="cover_letter",
    to_address="apply@flexionis.com",
    subject="Application: GenAI Support Engineer - LLM Agents & MCP - Matt Gates",
    body=cl4
)
print("4. QUEUED: GenAI Support Engineer - MCP ($48-52/hr)")

# === 5. Upwork AI Infrastructure Engineer - LLM Reliability ===
cl5 = f"""Dear Hiring Team,

I'm applying for the AI Infrastructure Engineer contract focused on LLM Reliability & Observability. Building reliable AI infrastructure is exactly what I do - I've deployed and maintained production LLM systems across multiple machines and GPU configurations.

Relevant experience:
- Deployed production Ollama + Open WebUI inference stacks with monitoring, health checks, and automated failover
- Built GPU inference infrastructure using Tesla P40 fleet (8-GPU Supermicro chassis) with container orchestration
- Python SDK and API integration experience across OpenAI, Anthropic Claude, and open-source models
- CI/CD pipeline design with Docker deployments, automated testing, and deployment safety gates
- Production monitoring with Prometheus, Grafana, and custom telemetry pipelines
- MCP server development for tool integration and agentic workflow orchestration

I'm particularly aligned with Reliai's mission - I've experienced firsthand the challenges of LLM regression detection, runtime guardrails, and deployment safety for AI systems. My current infrastructure spans 6+ machines on Tailscale with centralized management, giving me practical experience with the exact deployment patterns your clients need.

Available immediately for contract/project-based work on the Upwork platform.

{MATT_SIG}"""

db.queue_email(
    job_id="53d6056c1ca22752",
    email_type="cover_letter",
    to_address="apply@upwork.com",
    subject="Application: AI Infrastructure Engineer - LLM Reliability - Matt Gates",
    body=cl5
)
print("5. QUEUED: Upwork AI Infra Engineer (Contract)")

# Update job statuses
for jid in ["008486be4f804371", "1b13448deb463b14", "7e8771cc616c9234", "b17face69fe399d6", "53d6056c1ca22752"]:
    db.update_job(jid, status="saved", notes="Cover letter drafted and queued")

# Show queue
print("\n=== EMAIL QUEUE ===")
drafts = db.get_email_queue("draft")
for d in drafts:
    print(f"  #{d['id']} [{d['email_type']}] -> {d['to_address']}: {d['subject']}")

print(f"\nTotal drafts: {len(drafts)}")
print("Use job_approve_email in Claude Code to approve, then gmail_flush_queue to send.")
