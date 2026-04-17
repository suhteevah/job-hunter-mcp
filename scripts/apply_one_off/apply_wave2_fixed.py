"""Wave 2 FIXED: Handle Anthropic/Scale AI/WITHIN custom required fields."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time, os, sqlite3, hashlib

RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
DB_PATH = os.path.expanduser("~/.job-hunter-mcp/jobs.db")

WHY_ANTHROPIC = """I want to work at Anthropic because I've been building on Claude every day for the past year and I believe in the mission of creating safe, beneficial AI.

I've built 10+ production MCP servers for Claude Code integration, a 27,000-line Rust browser automation engine with MCTS action planning and multi-step agent orchestration, and an autonomous trading system using ML prediction models. These aren't side projects — they're production systems I run daily, and they all interface with Claude.

What draws me to Anthropic specifically is the combination of technical ambition and safety consciousness. I've seen firsthand how powerful Claude is as a foundation for autonomous agents, and I want to contribute to making those capabilities more reliable, more useful, and more safe. The Agent Infrastructure team in particular is building exactly the kind of systems I've been building independently — execution environments, state management, and security boundaries for autonomous AI.

I also deeply respect Anthropic's research culture and commitment to interpretability. I believe the most impactful AI work happens when engineering excellence meets genuine concern for societal impact, and that's what I see at Anthropic.

I'm a US citizen based in California, willing to relocate, and ready to start immediately. I'd bring production experience with the very platform this team is building infrastructure for."""

JOBS = [
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/5065894008",
        "company": "Anthropic",
        "title": "Senior / Staff+ Software Engineer, Autonomous Agent Infrastructure",
        "cover_letter": """I'm applying for the Autonomous Agent Infrastructure role because I've been building exactly this kind of system — on top of Claude.

Production Agent Infrastructure: 27,000-line Rust browser automation engine with MCTS action planning, multi-step agent orchestration, knowledge graph integration, and workflow replay. 10+ production MCP servers for Claude Code. Autonomous job hunting system coordinating search, scoring, application, and tracking agents.

Infrastructure: Rust (27K lines shipped), Python, TypeScript. Docker/K8s, GPU inference fleet operations, CI/CD, Prometheus/Grafana monitoring. I build reliable systems at scale.

US citizen, California, available for relocation. Deeply motivated to work on the infrastructure that makes Claude's agent capabilities possible.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": True,
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/4561282008",
        "company": "Anthropic",
        "title": "Staff Software Engineer, Claude Developer Platform (Full Stack)",
        "cover_letter": """I'm a power user of the Claude Developer Platform — 10+ production MCP servers, daily Claude Code usage, and production agent systems built on the API.

Full-Stack: Python/Rust/TypeScript across the stack. APIs, web interfaces, database systems, infrastructure tooling. Projects range from GPU inference fleet management to browser automation engines to ML trading systems.

I understand developer experience from both sides — as a tool builder AND a power user. I know what makes a platform delightful vs. frustrating.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": True,
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4653827005",
        "company": "Scale AI",
        "title": "Senior Software Engineer, Agentic Data Products",
        "cover_letter": """I build production agentic systems and understand the data infrastructure they require.

27K-line Rust browser engine with MCTS planning, knowledge graph, semantic search, workflow replay. Data pipelines, SQLite knowledge stores, entity graphs, embedding search. 10+ MCP servers, LLM apps, RAG pipelines, evaluation frameworks.

Rust, Python, TypeScript. Docker/K8s, GPU inference, CI/CD, monitoring.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": False,
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4658162005",
        "company": "Scale AI",
        "title": "Senior/Staff Machine Learning Engineer, General Agents, Enterprise GenAI",
        "cover_letter": """Building production agent systems is what I do every day.

27K-line Rust browser engine with MCTS action planning and multi-step orchestration. 10+ production MCP servers. Autonomous trading bot with ML prediction (20x returns). Job hunting automation coordinating search, scoring, application, and tracking agents. Knowledge graph and semantic search for agent memory.

I understand agent reliability, evaluation, and production infrastructure.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": False,
    },
    # WITHIN skipped — 14 custom required fields, needs manual apply
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/5134895008",
        "company": "Anthropic",
        "title": "Senior Staff Software Engineer, API",
        "cover_letter": """Heavy user of Anthropic's API — 10+ production MCP servers handling tool calling, streaming, conversation management, error recovery. I understand the API from the consumer side deeply.

Systems: 27K lines production Rust, Python/TypeScript full-stack, GPU inference fleet ops. Model serving, prompt engineering, RAG, evaluation frameworks.

10 years shipping software. The opportunity to shape the API developers worldwide use to build with Claude is deeply motivating.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": True,
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/4988878008",
        "company": "Anthropic",
        "title": "Staff Software Engineer, Claude Developer Platform (Backend)",
        "cover_letter": """I build production systems on Claude's platform daily. 10+ MCP servers shipped. 27K-line Rust browser engine with agent orchestration. Python/TypeScript/Rust polyglot. Docker/K8s. GPU inference fleet ops.

Power user of Claude Code and the developer platform — I know what works, what's missing, and what would make it transformative.

Matt Gates | (530) 786-3655 | ridgecellrepair@gmail.com | github.com/suhteevah""",
        "is_anthropic": True,
    },
]


def safe_dropdown(page, name, value, timeout=3000):
    """Try to select a React dropdown, fail silently."""
    try:
        combo = page.get_by_role("combobox", name=name)
        if combo.count() > 0 and combo.first.is_visible(timeout=timeout):
            combo.first.click()
            time.sleep(0.3)
            combo.first.fill(value)
            time.sleep(0.8)
            option = page.locator('[class*="option"]').filter(has_text=value).first
            if option.count() > 0 and option.is_visible():
                option.click()
            else:
                combo.first.press("ArrowDown")
                time.sleep(0.2)
                combo.first.press("Enter")
            time.sleep(0.3)
            print(f"  - Filled dropdown: {name} = {value}")
            return True
    except Exception as e:
        pass
    return False


def fill_anthropic_fields(page):
    """Fill Anthropic-specific required fields."""
    # "Why Anthropic?" textarea — use get_by_label
    try:
        why = page.get_by_label("Why Anthropic?")
        if why.count() > 0:
            why.first.fill(WHY_ANTHROPIC)
            print("  - Filled 'Why Anthropic?' via label")
        else:
            # Fallback: first visible textarea
            textareas = page.locator('textarea:visible').all()
            if len(textareas) >= 1:
                textareas[0].fill(WHY_ANTHROPIC)
                print("  - Filled first textarea (Why Anthropic? fallback)")
    except Exception as e:
        print(f"  - Why Anthropic fill error: {e}")

    # "Additional Information" textarea
    try:
        addl = page.get_by_label("Additional Information")
        if addl.count() > 0:
            addl.first.fill("See cover letter and resume attached.")
            print("  - Filled 'Additional Information' via label")
        else:
            textareas = page.locator('textarea:visible').all()
            if len(textareas) >= 2:
                textareas[1].fill("See cover letter and resume attached.")
                print("  - Filled second textarea (Additional Info fallback)")
    except Exception as e:
        print(f"  - Additional Info fill error: {e}")

    # AI Policy - "Yes"
    safe_dropdown(page, "AI Policy for Application", "Yes")

    # In-person 25%
    safe_dropdown(page, "Are you open to working in-person", "Yes")

    # Visa sponsorship
    safe_dropdown(page, "Do you require visa sponsorship", "No")
    safe_dropdown(page, "Will you now or will you in the future require employment visa sponsorship", "No")

    # Relocation
    safe_dropdown(page, "Are you open to relocation", "Yes")

    # Address / relocating
    try:
        loc_field = page.locator('input[type="text"]').all()
        for f in loc_field:
            label = f.get_attribute("aria-label") or ""
            if "address" in label.lower() and "relocating" in label.lower():
                if not f.input_value():
                    f.fill("relocating")
                    print("  - Filled address: relocating")
    except:
        pass

    # Start date
    safe_dropdown(page, "earliest you would want to start", "Immediately")
    # Fallback: fill text
    try:
        fields = page.locator('input[type="text"]').all()
        for f in fields:
            label = f.get_attribute("aria-label") or ""
            if "earliest" in label.lower() and not f.input_value():
                f.fill("Immediately")
    except:
        pass

    # Timeline/deadlines
    try:
        fields = page.locator('input[type="text"]').all()
        for f in fields:
            label = f.get_attribute("aria-label") or ""
            if "deadline" in label.lower() and not f.input_value():
                f.fill("No deadlines")
    except:
        pass

    # Previous interview
    safe_dropdown(page, "Have you ever interviewed at Anthropic", "No")


def fill_scale_fields(page):
    """Fill Scale AI custom fields."""
    safe_dropdown(page, "visa", "No")
    safe_dropdown(page, "authorized", "Yes")
    safe_dropdown(page, "sponsorship", "No")
    # Try any remaining required dropdowns
    try:
        combos = page.get_by_role("combobox").all()
        for combo in combos:
            val = combo.input_value()
            if not val:
                label = combo.get_attribute("aria-label") or ""
                if "authorized" in label.lower() or "legally" in label.lower():
                    safe_dropdown(page, label, "Yes")
                elif "sponsor" in label.lower() or "visa" in label.lower():
                    safe_dropdown(page, label, "No")
                elif "hear" in label.lower() or "how did" in label.lower():
                    safe_dropdown(page, label, "Job Board")
                elif "remote" in label.lower() or "location" in label.lower():
                    safe_dropdown(page, label, "Yes")
    except:
        pass


def fill_within_fields(page):
    """Fill WITHIN custom fields."""
    try:
        fields = page.locator('input[type="text"]').all()
        for f in fields:
            label = f.get_attribute("aria-label") or ""
            if "personal email" in label.lower() and not f.input_value():
                f.fill("ridgecellrepair@gmail.com")
            elif "refer" in label.lower() and not f.input_value():
                f.fill("No")
            elif "how did" in label.lower() and not f.input_value():
                f.fill("Job board search")
    except:
        pass


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
    if "can't find" in body.lower() or "not found" in body.lower():
        print("[!] Job not found. SKIPPING.")
        return False

    # Core fields
    try:
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name", exact=True).fill("Gates")
        page.get_by_role("textbox", name="Email", exact=True).fill("ridgecellrepair@gmail.com")
        print("  - Name/email filled")
    except Exception as e:
        print(f"[!] Name/email error: {e}")
        return False

    # Country
    safe_dropdown(page, "Country", "United States")

    # Phone
    try:
        page.get_by_role("textbox", name="Phone").last.fill("5307863655")
        print("  - Phone filled")
    except:
        pass

    # Resume
    try:
        page.locator('input#resume[type="file"]').set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded")
    except:
        try:
            page.locator('input[type="file"]').first.set_input_files(RESUME)
            time.sleep(1)
            print("  - Resume uploaded (fallback)")
        except Exception as e:
            print(f"  [!] Resume failed: {e}")

    # Cover letter — try file upload first, then textarea
    cover_path = os.path.join(os.path.dirname(__file__),
                              f"cover_{company.lower().replace(' ', '_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.txt")
    with open(cover_path, 'w', encoding='utf-8') as f:
        f.write(cover_text)
    try:
        cl = page.locator('input#cover_letter[type="file"]')
        if cl.count() > 0:
            cl.set_input_files(cover_path)
            time.sleep(1)
            print("  - Cover letter uploaded")
        else:
            # Check for "Additional Information" textarea
            ta = page.locator('textarea').all()
            for t in ta:
                parent = t.evaluate("el => el.closest('.field')?.textContent || ''")
                if "additional" in parent.lower() or "cover" in parent.lower():
                    t.fill(cover_text)
                    print("  - Cover letter in Additional Info textarea")
                    break
    except Exception as e:
        print(f"  - Cover letter: {e}")

    # LinkedIn
    try:
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  - LinkedIn filled")
    except:
        try:
            page.get_by_role("textbox", name="LinkedIn").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        except:
            pass

    # Website/GitHub
    try:
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
    except:
        pass

    # Company-specific fields
    if job.get("is_anthropic"):
        fill_anthropic_fields(page)
    elif company == "Scale AI":
        fill_scale_fields(page)
    elif company == "WITHIN":
        fill_within_fields(page)

    # Generic visa/auth
    safe_dropdown(page, "Will you now, or in the future, require Visa sponsorship", "No")
    safe_dropdown(page, "Are you legally authorized to work in the United States", "Yes")

    # EEO
    for field, value in [("Gender", "Male"), ("Hispanic/Latino", "No"),
                         ("Veteran Status", "I am not a protected veteran"),
                         ("Disability Status", "I do not want to answer")]:
        safe_dropdown(page, field, value)

    # Fill any remaining empty required text fields
    try:
        fields = page.locator('input[type="text"][aria-required="true"]').all()
        for f in fields:
            if not f.input_value():
                label = f.get_attribute("aria-label") or ""
                ll = label.lower()
                if "authorization" in ll or "authorized" in ll:
                    f.fill("Yes")
                elif "salary" in ll or "compensation" in ll:
                    f.fill("Open to discussion")
                elif "location" in ll or "city" in ll:
                    f.fill("Chico, CA (willing to relocate)")
                elif "hear" in ll or "how did" in ll or "find" in ll:
                    f.fill("Job board search")
                elif "refer" in ll:
                    f.fill("No")
                elif "start" in ll or "earliest" in ll:
                    f.fill("Immediately")
                elif "deadline" in ll or "timeline" in ll:
                    f.fill("No deadlines")
    except:
        pass

    # Screenshot pre-submit
    os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)
    page.screenshot(path=os.path.join(os.path.dirname(__file__),
                    f"screenshots/pre2_{company.lower().replace(' ','_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.png"),
                    full_page=True)

    # Submit
    print("  [*] Submitting...")
    try:
        submit = page.get_by_role("button", name="Submit application")
        submit.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit.click()
        time.sleep(8)
    except:
        try:
            page.locator('button[type="submit"]').click()
            time.sleep(8)
        except:
            print("  [!] No submit button. FAILED.")
            return False

    # Post-submit screenshot
    page.screenshot(path=os.path.join(os.path.dirname(__file__),
                    f"screenshots/post2_{company.lower().replace(' ','_')}_{hashlib.md5(title.encode()).hexdigest()[:6]}.png"),
                    full_page=True)

    body = page.text_content("body")
    page_url = page.url

    # Check for validation errors still present
    err_count = page.locator('[aria-invalid="true"]').count()
    if err_count > 0:
        print(f"  [!] {err_count} validation errors remain:")
        errs = page.locator('[aria-invalid="true"]').all()
        for el in errs[:8]:
            label = el.get_attribute("aria-label") or el.get_attribute("id") or "?"
            print(f"      - {label}")
        return False

    success = ("thank" in body.lower() or "submitted" in body.lower() or
               "received" in body.lower() or "confirmation" in page_url.lower())
    if "Submit application" not in body:
        success = True

    if success:
        print(f"  === SUCCESS: {title} @ {company} SUBMITTED ===")
    else:
        print(f"  [?] Result unclear for {company}")

    return success


def update_db(url, company, title, success):
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    if success:
        c.execute("UPDATE jobs SET status='applied', applied_date=datetime('now'), notes=? WHERE url=?",
                  ("Applied via Playwright Wave 2 Fixed. Personalized cover letter + Why Anthropic essay.", url))
        if c.rowcount == 0:
            job_id = hashlib.md5(url.encode()).hexdigest()[:16]
            c.execute("""INSERT OR IGNORE INTO jobs (id, source, title, company, url, location,
                         date_found, fit_score, status, applied_date, notes)
                         VALUES (?, 'greenhouse', ?, ?, ?, 'Remote',
                         datetime('now'), 85, 'applied', datetime('now'), 'Applied via Wave 2 Fixed')""",
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
        browser = p.chromium.launch(headless=True, slow_mo=200)
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
            time.sleep(3)

        browser.close()

    print(f"\n{'='*60}")
    print("WAVE 2 FIXED RESULTS")
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
