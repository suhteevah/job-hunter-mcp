"""
Job Hunter MCP - Configuration
All settings, skill profiles, and search presets.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("job_hunter.config")

# ============================================================
# PATHS
# ============================================================
DATA_DIR = Path.home() / ".job-hunter-mcp"
DB_PATH = DATA_DIR / "jobs.db"
LOG_FILE = DATA_DIR / "job_hunter.log"
CONFIG_FILE = DATA_DIR / "config.json"
QUEUE_DIR = DATA_DIR / "queue"  # Drafts awaiting approval

# ============================================================
# MATT'S PROFILE - Used for fit scoring and cover letters
# ============================================================
USER_PROFILE = {
    "name": "Matt Gates",
    "company": "Ridge Cell Repair LLC",
    "title": "Owner & Technical Director",
    "location": "Chico, CA",
    "phone": "(530) 786-3655",
    "github": "suhteevah",
    "summary": (
        "Technical Director with deep expertise in AI/LLM infrastructure, automation, "
        "and full-stack development. Built production AI agent fleets using Claude/Anthropic APIs, "
        "Ollama inference servers, and Docker orchestration. Strong background in QA engineering, "
        "B2B sales consulting, and DevOps. Experienced with Python, Rust, TypeScript/React, "
        "and modern cloud infrastructure."
    ),
    "key_achievements": [
        "Built multi-agent AI fleet (OpenClaw) with 7 specialized agents for automated business operations",
        "Deployed GPU inference infrastructure across heterogeneous hardware fleet (RTX 3070 Ti, Tesla P40s, Mac Mini)",
        "Developed production MCP servers in Rust for AI-powered admin tooling",
        "Created Next.js 15 multi-tenant SaaS dashboard with real-time monitoring",
        "Managed B2B consulting relationships across manufacturing, bottling, and industrial sectors",
        "QA engineering background with expertise in test automation and CI/CD pipelines",
    ],
    "primary_skills": [
        "AI/LLM Integration (Claude API, Ollama, OpenAI)",
        "Python, Rust, TypeScript/JavaScript",
        "React/Next.js, Tailwind CSS",
        "Docker, Linux, DevOps, CI/CD",
        "API Development (REST, GraphQL, MCP)",
        "QA Engineering & Test Automation",
        "n8n/Make.com Workflow Automation",
        "B2B Sales & Technical Consulting",
    ],
    "secondary_skills": [
        "PostgreSQL, SQLite, Redis",
        "Web Scraping & Data Pipelines",
        "SEO & Digital Marketing",
        "GPU Infrastructure & ML Ops",
        "Tailscale/Networking",
        "Technical Writing",
    ],
}

# ============================================================
# FIT SCORING KEYWORDS
# ============================================================
SCORING = {
    "title_keywords": {
        # High-value title matches (weight: 15 each)
        "ai": 15, "automation": 15, "llm": 15, "prompt engineer": 20,
        "ai engineer": 20, "ml engineer": 15, "qa": 12, "quality": 10,
        "devops": 12, "infrastructure": 10, "backend": 10,
        "full stack": 12, "fullstack": 12, "python": 12, "rust": 15,
        "sales engineer": 12, "solutions engineer": 12,
        "technical consultant": 12, "developer advocate": 10,
    },
    "primary_skills": [
        # Skills that score 5 points each when found in description
        "ai", "automation", "llm", "claude", "anthropic", "openai", "chatgpt",
        "python", "rust", "javascript", "typescript", "react", "next.js", "nextjs",
        "n8n", "make.com", "zapier", "api", "rest", "graphql",
        "docker", "kubernetes", "devops", "ci/cd", "linux",
        "qa", "quality assurance", "testing", "selenium", "playwright",
        "web scraping", "data pipeline", "etl", "mcp", "model context protocol",
    ],
    "secondary_skills": [
        # Skills that score 2 points each
        "sales", "b2b", "consulting", "seo", "digital marketing",
        "node.js", "nodejs", "fastapi", "flask", "django",
        "postgresql", "sqlite", "redis", "mongodb",
        "git", "github", "aws", "gcp", "azure",
        "ollama", "inference", "gpu", "ml", "machine learning",
    ],
    "negative_keywords": [
        # Reduce score by 10 each
        "senior staff", "principal", "director", "vp ", "vice president",
        "phd required", "10+ years", "15+ years",
        "clearance required", "ts/sci", "security clearance",
        "java ", "c# ", ".net ", "angular", "php ",
    ],
    "bonus_keywords": {
        # Specific bonuses
        "remote": 5,
        "contractor": 3, "freelance": 3, "contract": 3,
        "startup": 3, "small team": 3,
    },
}

# ============================================================
# PRE-BUILT SEARCH QUERIES
# ============================================================
SEARCH_PRESETS = {
    "ai_automation": {
        "queries": [
            "AI automation engineer",
            "LLM engineer",
            "prompt engineer",
            "AI infrastructure",
            "Claude API developer",
        ],
        "categories": ["software-dev"],
        "priority": 1,
    },
    "qa_engineering": {
        "queries": [
            "QA engineer remote",
            "quality assurance automation",
            "test automation engineer",
            "SDET remote",
        ],
        "categories": ["qa"],
        "priority": 2,
    },
    "devops": {
        "queries": [
            "DevOps engineer remote",
            "infrastructure engineer",
            "platform engineer",
            "SRE site reliability",
        ],
        "categories": ["devops-sysadmin"],
        "priority": 3,
    },
    "sales_tech": {
        "queries": [
            "sales engineer remote",
            "solutions engineer",
            "technical account manager",
            "B2B sales technology",
        ],
        "categories": ["sales"],
        "priority": 4,
    },
}

# ============================================================
# SCHEDULER CONFIG
# ============================================================
SCHEDULER = {
    "search_interval_hours": 4,       # How often to run searches
    "email_check_interval_minutes": 30, # How often to check Gmail
    "auto_apply": False,               # If True, auto-submit applications (DANGEROUS)
    "auto_draft_cover_letters": True,  # Auto-draft for jobs scoring > threshold
    "cover_letter_threshold": 40,      # Min fit score to auto-draft cover letter
    "auto_reply_emails": False,        # If True, auto-send email replies (DANGEROUS)
    "max_applications_per_day": 10,    # Safety limit
    "notification_email": None,        # Email for notifications (optional)
}

# ============================================================
# EMAIL TEMPLATES
# ============================================================
EMAIL_TEMPLATES = {
    "recruiter_reply": (
        "Hi {recruiter_name},\n\n"
        "Thank you for reaching out! I'm very interested in the {job_title} position "
        "at {company}.\n\n"
        "{personalized_body}\n\n"
        "I'd love to schedule a time to discuss further. I'm available for a call "
        "at your convenience.\n\n"
        "Best regards,\n"
        "Matt Gates\n"
        "Ridge Cell Repair LLC\n"
        "(530) 786-3655"
    ),
    "follow_up": (
        "Hi {recruiter_name},\n\n"
        "I wanted to follow up on my application for the {job_title} position "
        "at {company}. I remain very enthusiastic about this opportunity.\n\n"
        "{personalized_body}\n\n"
        "Please let me know if you need any additional information from me.\n\n"
        "Best regards,\n"
        "Matt Gates"
    ),
    "interview_confirm": (
        "Hi {recruiter_name},\n\n"
        "Thank you for the interview invitation! I'd be happy to confirm "
        "{interview_details}.\n\n"
        "Looking forward to speaking with you.\n\n"
        "Best regards,\n"
        "Matt Gates"
    ),
}

# ============================================================
# GMAIL MONITORING CONFIG
# ============================================================
GMAIL = {
    "watch_labels": ["INBOX"],
    "recruiter_indicators": [
        "application", "position", "role", "opportunity",
        "interview", "schedule", "candidate", "resume",
        "hiring", "recruiter", "talent", "job",
    ],
    "auto_label": "JobHunter",  # Label to apply to matched emails
    "check_unread_only": True,
}


def load_config() -> dict:
    """Load saved config from disk, merging with defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            logger.info(f"Loaded config from {CONFIG_FILE}")
            return saved
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return {}


def save_config(config: dict):
    """Save config to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved to {CONFIG_FILE}")
