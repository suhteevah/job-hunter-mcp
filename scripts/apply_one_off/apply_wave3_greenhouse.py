"""Wave 3: Batch apply to Greenhouse jobs via Playwright. Top-priority AI roles."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time
import os
import sqlite3
import hashlib

RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
DB_PATH = os.path.expanduser("~/.job-hunter-mcp/jobs.db")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

JOBS = [
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/5065894008",
        "company": "Anthropic",
        "title": "Senior / Staff+ Software Engineer, Autonomous Agents",
        "cover_file": "cover_anthropic_agents.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/anthropic/jobs/4561282008",
        "company": "Anthropic",
        "title": "Staff Software Engineer, Claude Developer Platform",
        "cover_file": "cover_anthropic_devplatform.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4653827005",
        "company": "Scale AI",
        "title": "Senior Software Engineer, Agentic Data Products",
        "cover_file": "cover_scaleai_agentic.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/scaleai/jobs/4658162005",
        "company": "Scale AI",
        "title": "Senior/Staff ML Engineer, General Agents",
        "cover_file": "cover_scaleai_agents.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/agencywithin/jobs/5056863007",
        "company": "WITHIN",
        "title": "AI Engineer",
        "cover_file": "cover_within_ai.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/assemblyai/jobs/4664764005",
        "company": "AssemblyAI",
        "title": "Senior Software Engineer, Machine Learning",
        "cover_file": "cover_assemblyai_ml.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/ziprecruiter/jobs/5167472",
        "company": "ZipRecruiter",
        "title": "Senior Software Engineer, Machine Learning",
        "cover_file": "cover_ziprecruiter_ml.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/ziprecruiter/jobs/5167480",
        "company": "ZipRecruiter",
        "title": "Staff Software Engineer, Machine Learning",
        "cover_file": "cover_ziprecruiter_staff.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/assemblyai/jobs/4636327005",
        "company": "AssemblyAI",
        "title": "Senior Software Engineer, AI Data",
        "cover_file": "cover_assemblyai_data.txt",
    },
    {
        "url": "https://job-boards.greenhouse.io/planetscale/jobs/4036240009",
        "company": "PlanetScale",
        "title": "Software Engineer - Infrastructure",
        "cover_file": "cover_planetscale.txt",
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
    cover_path = os.path.join(SCRIPT_DIR, job["cover_file"])

    print(f"\n{'='*60}")
    print(f"[*] Applying: {title} @ {company}")
    print(f"[*] URL: {url}")
    print(f"{'='*60}")

    if not os.path.exists(cover_path):
        print(f"  [!] Cover letter not found: {cover_path}. SKIPPING.")
        return False

    page.goto(url, wait_until="networkidle")
    time.sleep(2)

    body = page.text_content("body")
    if "can't find" in body.lower() or "not found" in body.lower() or "no longer" in body.lower():
        print(f"  [!] Job page not found or expired. SKIPPING.")
        return False

    # Fill standard fields
    try:
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name", exact=True).fill("Gates")
        page.get_by_role("textbox", name="Email", exact=True).fill("ridgecellrepair@gmail.com")
    except Exception as e:
        print(f"  [!] Error filling name/email: {e}")
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

    # Cover letter file upload
    try:
        cl_input = page.locator('input#cover_letter[type="file"]')
        if cl_input.count() > 0:
            cl_input.set_input_files(cover_path)
            time.sleep(1)
            print("  - Cover letter uploaded (file)")
        else:
            cl_textarea = page.locator('textarea[id*="cover"], textarea[name*="cover"]')
            if cl_textarea.count() > 0:
                with open(cover_path, 'r', encoding='utf-8') as f:
                    cl_textarea.fill(f.read())
                print("  - Cover letter filled (textarea)")
            else:
                print("  - No cover letter field found")
    except Exception as e:
        print(f"  - Cover letter: {e}")

    # LinkedIn
    try:
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
    except:
        try:
            page.get_by_role("textbox", name="LinkedIn").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        except:
            print("  - LinkedIn field not found")

    # Website / GitHub
    try:
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
    except:
        pass
    try:
        page.get_by_role("textbox", name="GitHub").fill("https://github.com/suhteevah")
    except:
        pass

    # Visa sponsorship
    try:
        select_react_dropdown(page, "Will you now, or in the future, require Visa sponsorship", "No")
    except:
        try:
            select_react_dropdown(page, "visa", "No")
        except:
            pass

    # Work authorization
    try:
        select_react_dropdown(page, "authorized to work", "Yes")
    except:
        pass

    # EEO (voluntary)
    for field, value in [("Gender", "Male"), ("Hispanic/Latino", "No"),
                         ("Veteran Status", "I am not a protected veteran"),
                         ("Disability Status", "I do not want to answer")]:
        try:
            select_react_dropdown(page, field, value)
        except:
            pass

    # Catch-all for unfilled required text fields
    try:
        auth_fields = page.locator('input[type="text"][aria-required="true"]').all()
        for field in auth_fields:
            val = field.input_value()
            if not val:
                label = (field.get_attribute("aria-label") or "").lower()
                if "authorization" in label or "authorized" in label or "legally" in label:
                    field.fill("Yes")
                elif "salary" in label or "compensation" in label:
                    field.fill("Open to discussion")
                elif "location" in label or "city" in label or "where" in label:
                    field.fill("Chico, CA")
                elif "hear" in label or "how did" in label or "source" in label:
                    field.fill("Job board search")
                elif "years" in label or "experience" in label:
                    field.fill("10")
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

    if "Submit application" not in body and "Apply for this job" not in body:
        success = True

    if success:
        print(f"  === SUCCESS: {title} @ {company} SUBMITTED ===")
    else:
        page.screenshot(path=os.path.join(SCRIPT_DIR, f"fail_{company.lower().replace(' ','_')}.png"), full_page=True)
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
                  (f"Applied via Playwright Wave 3 batch. Personalized cover letter.", url))
        if c.rowcount == 0:
            job_id = hashlib.md5(url.encode()).hexdigest()[:16]
            c.execute("""INSERT OR IGNORE INTO jobs (id, source, title, company, url, location, job_type, category,
                         date_found, fit_score, status, applied_date, notes)
                         VALUES (?, 'greenhouse', ?, ?, ?, 'Remote', 'full-time', 'AI/ML',
                         datetime('now'), 85, 'applied', datetime('now'), 'Applied via Wave 3 batch')""",
                      (job_id, title, company, url))
    db.commit()
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
    total = c.fetchone()[0]
    db.close()
    return total

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
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
    print("WAVE 3 BATCH RESULTS")
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
