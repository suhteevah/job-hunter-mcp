"""Batch apply to Greenhouse jobs via Playwright. Reusable for any Greenhouse posting."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time
import os
import sqlite3
import hashlib

RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
DB_PATH = os.path.expanduser("~/.job-hunter-mcp/jobs.db")

JOBS = [
    {
        "url": "https://job-boards.greenhouse.io/grafanalabs/jobs/5802159004",
        "company": "Grafana Labs",
        "title": "Senior AI Engineer - Grafana Ops",
        "cover_letter": """Dear Grafana Labs Hiring Team,

I'm deeply excited about this role because it sits at the exact intersection of my two strongest domains: AI/ML engineering and observability infrastructure.

What I bring:

Production Observability: I run Prometheus + Grafana monitoring stacks daily for my GPU inference fleet and AI agent systems. I understand metrics, traces, and logs not as abstract concepts but as tools I depend on to keep production AI systems healthy.

AI Agent Systems: I've built 10+ production MCP servers for Claude Code integration, a 27K-line Rust browser automation engine with MCTS action planning and multi-step agent orchestration, and an autonomous trading bot using ML prediction models (20x returns).

LLM Application Development: I build with OpenAI, Anthropic/Claude, LangChain, and custom inference stacks daily. Prompt engineering, RAG pipelines, tool calling, streaming — these are my daily tools, not buzzwords.

Infrastructure: Docker/Kubernetes container orchestration, CI/CD pipelines with safety gates, Python/Rust/TypeScript polyglot development, and GPU inference optimization.

The opportunity to build AI-powered features that help users understand and respond to their observability data is exactly where I want to be. I understand both sides of this problem intimately.

Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/censys/jobs/8245155002",
        "company": "Censys",
        "title": "Senior Software Engineer, AI/LLM",
        "cover_letter": """Dear Censys Hiring Team,

Building AI-powered features on top of Internet-scale data is exactly the kind of challenge I thrive on. My background combines production AI systems with the infrastructure expertise needed to make them reliable at scale.

Relevant experience:

Production AI/LLM Systems: I build and deploy LLM-powered applications daily — RAG pipelines, vector search, tool calling agents, and streaming interfaces. I've built 10+ MCP servers exposing platform capabilities to AI systems, and a 27K-line Rust browser engine with embedded knowledge graphs and semantic search.

Scale & Infrastructure: I operate GPU inference fleets with Docker container orchestration, Prometheus/Grafana monitoring, and CI/CD pipelines. I understand K8s networking, scaling, and monitoring for AI services — not theoretically, but from running them in production.

Python & Full Stack: Python is my primary language for AI work, alongside Rust for performance-critical systems and TypeScript for web interfaces. I'm comfortable across the entire stack from model fine-tuning to API design to frontend integration.

Evaluation & Quality: I build evaluation frameworks for my AI systems, track model performance metrics, and implement automated testing gates. I understand that shipping AI features means measuring what matters, not just deploying models.

I'm a US citizen based in California, available immediately.

Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/khanacademy/jobs/7724300",
        "company": "Khan Academy",
        "title": "Sr. AI Engineer (24mo fixed-term)",
        "cover_letter": """Dear Khan Academy Hiring Team,

I'm drawn to this role because I believe AI has the potential to transform education at scale — and I have the technical depth to help make that happen.

What I bring:

Applied AI Engineering: I build production AI systems daily — prompt chaining, RAG pipelines, tool calling, and multi-step agent orchestration. I've built 10+ MCP servers and a full AI browser automation engine (27K lines of Rust) with MCTS planning and knowledge graph integration.

Python Expertise: Python is my primary AI development language. I work with OpenAI, Anthropic/Claude, LangChain, FastAPI, and custom ML pipelines. I build evaluation frameworks, track model quality metrics, and implement automated testing.

Production Infrastructure: Docker/K8s orchestration, GPU inference fleet management, Prometheus/Grafana monitoring, CI/CD with safety gates. I understand how to ship AI features that are reliable, observable, and cost-effective.

Data-Driven Development: My Kalshi Weather Bot project demonstrates my approach — ML prediction models with rigorous backtesting, real-time performance tracking, and continuous iteration based on measured outcomes.

I'm excited about the mission of providing free, world-class education and would bring both technical excellence and genuine enthusiasm to the team.

Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/onboardmeetings/jobs/5813540004",
        "company": "OnBoard Meetings",
        "title": "Senior Software Engineer, eScribe - AI",
        "cover_letter": """Dear OnBoard Meetings Hiring Team,

I'm excited about this Senior Software Engineer role focused on AI-assisted development. My background in production AI systems and full-stack engineering maps directly to your needs.

I build and deploy AI-powered applications daily — 10+ MCP servers for Claude Code integration, a 27K-line Rust browser automation engine, and ML prediction systems. I'm fluent in Python, Rust, and TypeScript with strong Docker/K8s, CI/CD, and monitoring experience.

I embrace AI-assisted development practices as part of my daily workflow and would bring both technical depth and practical AI integration experience to your engineering team.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/pathward/jobs/5828346004",
        "company": "Pathward",
        "title": "AI Engineer, Senior",
        "cover_letter": """Dear Pathward Hiring Team,

I bring 10 years of software engineering experience with deep AI/ML focus to this role. I build production AI systems daily — LLM applications, ML prediction models, data pipelines, and API integrations.

My portfolio includes 10+ production MCP servers, autonomous ML trading systems, GPU inference fleet management, and full-stack AI application development in Python, Rust, and TypeScript.

I'm a US citizen, available immediately, and excited about applying AI to financial services.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
]

def select_react_dropdown(page, name, value):
    """Handle React-Select combobox."""
    combo = page.get_by_role("combobox", name=name)
    combo.click()
    time.sleep(0.3)
    combo.fill(value)
    time.sleep(0.8)
    option = page.locator('[class*="option"]').filter(has_text=value).first
    if option.count() > 0 and option.is_visible():
        option.click()
    else:
        combo.press("ArrowDown")
        time.sleep(0.2)
        combo.press("Enter")
    time.sleep(0.3)

def apply_to_job(page, job):
    """Fill and submit a single Greenhouse application."""
    url = job["url"]
    company = job["company"]
    title = job["title"]
    cover_text = job["cover_letter"]

    print(f"\n{'='*60}")
    print(f"[*] Applying: {title} @ {company}")
    print(f"[*] URL: {url}")
    print(f"{'='*60}")

    page.goto(url, wait_until="networkidle")
    time.sleep(2)

    # Check if page loaded correctly
    body = page.text_content("body")
    if "can't find" in body.lower() or "not found" in body.lower() or "404" in body.lower():
        print(f"[!] Job page not found — may be expired. SKIPPING.")
        return False

    # Fill text fields
    try:
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name", exact=True).fill("Gates")
        page.get_by_role("textbox", name="Email", exact=True).fill("ridgecellrepair@gmail.com")
    except Exception as e:
        print(f"[!] Error filling name/email: {e}")
        return False

    # Country
    try:
        select_react_dropdown(page, "Country", "United States")
    except:
        print("  - Country dropdown not found or failed")

    # Phone
    try:
        page.get_by_role("textbox", name="Phone").last.fill("5307863655")
    except:
        print("  - Phone field not found")

    # Resume
    try:
        page.locator('input#resume[type="file"]').set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded")
    except Exception as e:
        print(f"  [!] Resume upload failed: {e}")

    # Cover letter
    cover_path = os.path.join(os.path.dirname(__file__), f"cover_{company.lower().replace(' ', '_')}.txt")
    with open(cover_path, 'w', encoding='utf-8') as f:
        f.write(cover_text)
    try:
        cl_input = page.locator('input#cover_letter[type="file"]')
        if cl_input.count() > 0:
            cl_input.set_input_files(cover_path)
            time.sleep(1)
            print("  - Cover letter uploaded (file)")
        else:
            # Try textarea for cover letter
            cl_textarea = page.locator('textarea[id*="cover"], textarea[name*="cover"]')
            if cl_textarea.count() > 0:
                cl_textarea.fill(cover_text)
                print("  - Cover letter filled (textarea)")
            else:
                print("  - No cover letter field found")
    except Exception as e:
        print(f"  - Cover letter: {e}")

    # LinkedIn (required on most Greenhouse)
    try:
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
    except:
        try:
            page.get_by_role("textbox", name="LinkedIn").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        except:
            print("  - LinkedIn field not found")

    # Website
    try:
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
    except:
        pass

    # Visa sponsorship
    try:
        select_react_dropdown(page, "Will you now, or in the future, require Visa sponsorship", "No")
    except:
        try:
            select_react_dropdown(page, "visa", "No")
        except:
            print("  - Visa question not found")

    # EEO (voluntary, try but don't fail)
    for field, value in [("Gender", "Male"), ("Hispanic/Latino", "No"),
                         ("Veteran Status", "I am not a protected veteran"),
                         ("Disability Status", "I do not want to answer")]:
        try:
            select_react_dropdown(page, field, value)
        except:
            pass

    # Any additional text fields (work authorization, etc.)
    try:
        auth_fields = page.locator('input[type="text"][aria-required="true"]').all()
        for field in auth_fields:
            val = field.input_value()
            if not val:
                label = field.get_attribute("aria-label") or ""
                if "authorization" in label.lower() or "authorized" in label.lower():
                    field.fill("Yes")
                elif "salary" in label.lower() or "compensation" in label.lower():
                    field.fill("Open to discussion")
                elif "location" in label.lower() or "city" in label.lower():
                    field.fill("Chico, CA")
                elif "hear" in label.lower() or "how did" in label.lower():
                    field.fill("Job board search")
    except:
        pass

    # Submit
    print("  [*] Submitting...")
    try:
        submit = page.get_by_role("button", name="Submit application")
        submit.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit.click()
        time.sleep(6)
    except Exception as e:
        print(f"  [!] Submit button error: {e}")
        # Try alternate submit buttons
        try:
            page.locator('button[type="submit"]').click()
            time.sleep(6)
        except:
            print(f"  [!] No submit button found. FAILED.")
            return False

    # Check result
    body = page.text_content("body")
    page_url = page.url
    success = ("thank" in body.lower() or "submitted" in body.lower() or
               "received" in body.lower() or "interest" in body[:500].lower() or
               "confirmation" in page_url.lower())

    # Also check if we're on a different page than the application form
    if "Submit application" not in body and "Apply for this job" not in body:
        success = True  # We left the form page = likely submitted

    if success:
        print(f"  === SUCCESS: {title} @ {company} SUBMITTED ===")
    else:
        page.screenshot(path=os.path.join(os.path.dirname(__file__), f"fail_{company.lower().replace(' ','_')}.png"), full_page=True)
        # Check for specific validation errors
        err_elements = page.locator('[aria-invalid="true"]').all()
        for el in err_elements[:5]:
            label = el.get_attribute("aria-label") or el.get_attribute("id") or "?"
            print(f"  VALIDATION: {label} is invalid")
        print(f"  [?] Result unclear for {company}. Screenshot saved.")

    return success

def update_db(url, company, title, success):
    """Mark job as applied in DB."""
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    if success:
        c.execute("UPDATE jobs SET status='applied', applied_date=datetime('now'), notes=? WHERE url=?",
                  (f"Applied via Playwright batch automation 2026-03-20. Personalized cover letter.", url))
        if c.rowcount == 0:
            # Insert if not in DB
            job_id = hashlib.md5(url.encode()).hexdigest()[:16]
            c.execute("""INSERT OR IGNORE INTO jobs (id, source, title, company, url, location, job_type, category,
                         date_found, fit_score, status, applied_date, notes)
                         VALUES (?, 'greenhouse', ?, ?, ?, 'Remote', 'full-time', 'AI/ML',
                         datetime('now'), 85, 'applied', datetime('now'), 'Applied via batch automation')""",
                      (job_id, title, company, url))
    db.commit()
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
    total = c.fetchone()[0]
    db.close()
    return total

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=150)
        page = browser.new_page()

        for job in JOBS:
            try:
                success = apply_to_job(page, job)
                total = update_db(job["url"], job["company"], job["title"], success)
                results.append((job["company"], job["title"], success, total))
                print(f"  DB total applied: {total}")
            except Exception as e:
                print(f"  [!] EXCEPTION: {e}")
                results.append((job["company"], job["title"], False, 0))
            time.sleep(2)

        browser.close()

    print(f"\n{'='*60}")
    print("BATCH RESULTS")
    print(f"{'='*60}")
    for company, title, success, total in results:
        status = "SUBMITTED" if success else "FAILED"
        print(f"  [{status}] {title} @ {company}")

    submitted = sum(1 for _, _, s, _ in results if s)
    print(f"\n{submitted}/{len(results)} applications submitted")
    if results:
        print(f"Total applied in DB: {results[-1][3]}")

if __name__ == "__main__":
    main()
