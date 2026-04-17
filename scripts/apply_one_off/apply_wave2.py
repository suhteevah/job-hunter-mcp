"""Wave 2: Batch apply to top Greenhouse jobs via Playwright.
Targets: Anthropic, Scale AI, Datadog, WITHIN, Remote People
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time, os, sqlite3, hashlib

RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
DB_PATH = os.path.expanduser("~/.job-hunter-mcp/jobs.db")

JOBS = [
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/5065894008",
        "company": "Anthropic",
        "title": "Senior / Staff+ Software Engineer, Autonomous Agent Infrastructure",
        "cover_letter": """Dear Anthropic Hiring Team,

I'm applying for the Autonomous Agent Infrastructure role because I've been building exactly this kind of system — and I built it on top of Claude.

What I bring:

Production Agent Infrastructure: I've built a 27,000-line Rust browser automation engine (Wraith/OpenClaw) with MCTS action planning, multi-step agent orchestration, knowledge graph integration, and workflow replay. This is production autonomous agent infrastructure — not a prototype.

10+ MCP Servers: I build and ship Model Context Protocol servers for Claude Code integration. I understand the MCP spec, tool calling patterns, streaming protocols, and the challenges of making agents reliable in production.

AI-First Development: My daily workflow runs on Claude Code. I've automated job hunting with autonomous agents that search, score, apply, and track — coordinating browser automation, API calls, database management, and LLM inference in production loops.

Infrastructure: Rust (27K lines shipped), Python, TypeScript polyglot. Docker/K8s, GPU inference fleet operations, CI/CD with safety gates, Prometheus/Grafana monitoring.

I'm a US citizen based in California, available for relocation, and deeply motivated to work on the infrastructure that makes Claude's agent capabilities possible.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/4561282008",
        "company": "Anthropic",
        "title": "Staff Software Engineer, Claude Developer Platform (Full Stack)",
        "cover_letter": """Dear Anthropic Hiring Team,

I'm applying for the Claude Developer Platform role because I'm not just a user of this platform — I'm a power user who builds production systems on top of it daily.

What I bring:

Claude Developer Platform Experience: I've built 10+ production MCP servers, integrated Claude Code into autonomous workflows, and pushed the boundaries of what's possible with the API, tool calling, streaming, and agent orchestration.

Full-Stack Engineering: Python/Rust/TypeScript across the stack. I build APIs, web interfaces, database systems, and infrastructure tooling. My projects range from GPU inference fleet management to browser automation engines to ML trading systems.

Developer Tools: I understand developer experience from both sides — as someone who builds dev tools AND as a power user who depends on them. I know what makes a platform delightful vs. frustrating.

Production Systems: 10 years of shipping software. Docker/K8s, CI/CD, monitoring, and the discipline to build things that work reliably at scale.

The opportunity to shape the platform that developers use to build with Claude is exactly where I want to be.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4653827005",
        "company": "Scale AI",
        "title": "Senior Software Engineer, Agentic Data Products",
        "cover_letter": """Dear Scale AI Hiring Team,

I'm applying for the Agentic Data Products role because I build production agentic systems and understand the data infrastructure they require.

What I bring:

Agentic Systems: I've built autonomous agents that orchestrate multi-step workflows — browser automation with MCTS planning, knowledge graph integration, semantic search, and workflow replay. My Wraith browser engine (27K lines Rust) is a production agentic system with 80+ tools.

Data Products: I build data pipelines, SQLite knowledge stores, entity graphs, and embedding-based semantic search. I understand how to structure data for agent consumption and how to build the infrastructure that makes agents reliable.

AI/ML Engineering: 10+ MCP servers, LLM application development, prompt engineering, RAG pipelines, and evaluation frameworks. I work with Claude, GPT, and custom inference stacks daily.

Infrastructure: Rust, Python, TypeScript. Docker/K8s, GPU inference, CI/CD, monitoring. I ship production software.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4658162005",
        "company": "Scale AI",
        "title": "Senior/Staff Machine Learning Engineer, General Agents, Enterprise GenAI",
        "cover_letter": """Dear Scale AI Hiring Team,

I'm applying for the General Agents role because building production agent systems is what I do every day.

My agent engineering experience includes:

- 27K-line Rust browser automation engine with MCTS action planning, behavioral simulation, and multi-step orchestration
- 10+ production MCP servers for Claude Code integration with tool calling and streaming
- Autonomous trading bot with ML prediction models (20x returns, 4 beta testers)
- Job hunting automation system coordinating search, scoring, application, and tracking agents
- Knowledge graph and semantic search systems for agent memory

I understand agent reliability, evaluation, and the infrastructure needed to make agents work in production. I'm a US citizen, available immediately.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/agencywithin/jobs/5056863007",
        "company": "WITHIN",
        "title": "AI Engineer",
        "cover_letter": """Dear WITHIN Hiring Team,

I'm excited about this AI Engineer role. I bring 10 years of software engineering experience with deep focus on AI/ML systems.

My experience includes building 10+ production MCP servers, a 27K-line Rust browser automation engine with AI planning, ML prediction models for autonomous trading (20x returns), and full-stack AI application development.

I work daily with Claude, GPT, LangChain, RAG pipelines, and custom inference stacks. I'm proficient in Python, Rust, and TypeScript with strong infrastructure skills (Docker, K8s, CI/CD, monitoring).

I'm a US citizen based in California, available immediately and excited to contribute.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/5134895008",
        "company": "Anthropic",
        "title": "Senior Staff Software Engineer, API",
        "cover_letter": """Dear Anthropic Hiring Team,

I'm applying for the Senior Staff Software Engineer, API role because I'm a heavy user of Anthropic's API and understand its strengths, limitations, and opportunities for improvement from a practitioner's perspective.

What I bring:

API Design & Usage: I've built 10+ production MCP servers that interface with Claude's API, handling tool calling, streaming, conversation management, and error recovery. I understand the API from the consumer side deeply.

Systems Engineering: 27K lines of production Rust, Python/TypeScript full-stack development, GPU inference fleet operations. I build reliable, performant systems at scale.

AI Infrastructure: Model serving, prompt engineering, RAG pipelines, evaluation frameworks. I understand the full stack from API request to model inference and back.

Production Discipline: 10 years of shipping software with CI/CD, monitoring, and the judgment to make good tradeoffs under constraints.

The opportunity to shape the API that developers worldwide use to build with Claude is deeply motivating.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/4988878008",
        "company": "Anthropic",
        "title": "Staff Software Engineer, Claude Developer Platform (Backend)",
        "cover_letter": """Dear Anthropic Hiring Team,

I'm applying for the Claude Developer Platform Backend role. I build production systems on top of Claude's platform daily and understand what makes developer platforms excellent.

10+ production MCP servers shipped. 27K-line Rust browser engine with agent orchestration. Python/TypeScript/Rust polyglot. Docker/K8s infrastructure. GPU inference fleet ops.

I'm a power user of Claude Code and the developer platform — I know what works, what's missing, and what would make the platform transformative for developers.

US citizen, California based, available for relocation.

Best regards,
Matt Gates
(530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah"""
    },
]


def select_react_dropdown(page, name, value):
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

    body = page.text_content("body")
    if "can't find" in body.lower() or "not found" in body.lower() or "404" in body.lower():
        print(f"[!] Job page not found. SKIPPING.")
        return False

    # Fill text fields
    try:
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name", exact=True).fill("Gates")
        page.get_by_role("textbox", name="Email", exact=True).fill("ridgecellrepair@gmail.com")
    except Exception as e:
        print(f"[!] Error filling name/email: {e}")
        return False

    try: select_react_dropdown(page, "Country", "United States")
    except: print("  - Country dropdown not found")

    try: page.get_by_role("textbox", name="Phone").last.fill("5307863655")
    except: print("  - Phone field not found")

    # Resume
    try:
        page.locator('input#resume[type="file"]').set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded")
    except Exception as e:
        print(f"  [!] Resume upload failed: {e}")

    # Cover letter
    cover_path = os.path.join(os.path.dirname(__file__),
                              f"cover_{company.lower().replace(' ', '_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.txt")
    with open(cover_path, 'w', encoding='utf-8') as f:
        f.write(cover_text)
    try:
        cl_input = page.locator('input#cover_letter[type="file"]')
        if cl_input.count() > 0:
            cl_input.set_input_files(cover_path)
            time.sleep(1)
            print("  - Cover letter uploaded")
        else:
            cl_textarea = page.locator('textarea[id*="cover"], textarea[name*="cover"]')
            if cl_textarea.count() > 0:
                cl_textarea.fill(cover_text)
                print("  - Cover letter filled (textarea)")
    except Exception as e:
        print(f"  - Cover letter: {e}")

    # LinkedIn
    try: page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
    except:
        try: page.get_by_role("textbox", name="LinkedIn").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        except: print("  - LinkedIn not found")

    # Website/GitHub
    try: page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
    except: pass
    try: page.get_by_role("textbox", name="GitHub").fill("https://github.com/suhteevah")
    except: pass

    # Visa
    try: select_react_dropdown(page, "Will you now, or in the future, require Visa sponsorship", "No")
    except:
        try: select_react_dropdown(page, "visa", "No")
        except: pass

    # Work auth
    try: select_react_dropdown(page, "Are you legally authorized to work in the United States", "Yes")
    except: pass

    # EEO
    for field, value in [("Gender", "Male"), ("Hispanic/Latino", "No"),
                         ("Veteran Status", "I am not a protected veteran"),
                         ("Disability Status", "I do not want to answer")]:
        try: select_react_dropdown(page, field, value)
        except: pass

    # Any unfilled required text fields
    try:
        fields = page.locator('input[type="text"][aria-required="true"]').all()
        for field in fields:
            if not field.input_value():
                label = field.get_attribute("aria-label") or ""
                if "authorization" in label.lower(): field.fill("Yes")
                elif "salary" in label.lower(): field.fill("Open to discussion")
                elif "location" in label.lower() or "city" in label.lower(): field.fill("Chico, CA")
                elif "hear" in label.lower(): field.fill("Job board")
    except: pass

    # Screenshot pre-submit
    page.screenshot(path=os.path.join(os.path.dirname(__file__),
                    f"screenshots/pre_{company.lower().replace(' ','_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.png"),
                    full_page=True)

    # Submit
    print("  [*] Submitting...")
    try:
        submit = page.get_by_role("button", name="Submit application")
        submit.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit.click()
        time.sleep(6)
    except:
        try:
            page.locator('button[type="submit"]').click()
            time.sleep(6)
        except:
            print("  [!] No submit button found. FAILED.")
            return False

    # Screenshot post-submit
    page.screenshot(path=os.path.join(os.path.dirname(__file__),
                    f"screenshots/post_{company.lower().replace(' ','_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.png"),
                    full_page=True)

    body = page.text_content("body")
    success = ("thank" in body.lower() or "submitted" in body.lower() or
               "received" in body.lower() or "confirmation" in page.url.lower())
    if "Submit application" not in body:
        success = True

    if success:
        print(f"  === SUCCESS: {title} @ {company} SUBMITTED ===")
    else:
        err_elements = page.locator('[aria-invalid="true"]').all()
        for el in err_elements[:5]:
            label = el.get_attribute("aria-label") or "?"
            print(f"  VALIDATION: {label} is invalid")
        print(f"  [?] Result unclear for {company}.")

    return success


def update_db(url, company, title, success):
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    if success:
        c.execute("UPDATE jobs SET status='applied', applied_date=datetime('now'), notes=? WHERE url=?",
                  (f"Applied via Playwright batch Wave 2. Personalized cover letter.", url))
        if c.rowcount == 0:
            job_id = hashlib.md5(url.encode()).hexdigest()[:16]
            c.execute("""INSERT OR IGNORE INTO jobs (id, source, title, company, url, location,
                         date_found, fit_score, status, applied_date, notes)
                         VALUES (?, 'greenhouse', ?, ?, ?, 'Remote',
                         datetime('now'), 85, 'applied', datetime('now'), 'Applied via batch Wave 2')""",
                      (job_id, title, company, url))
    db.commit()
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
    total = c.fetchone()[0]
    db.close()
    return total


def main():
    os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)
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
    print("WAVE 2 BATCH RESULTS")
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
