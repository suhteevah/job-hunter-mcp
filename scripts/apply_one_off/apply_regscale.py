"""Apply to RegScale Senior AI Engineer via Playwright browser automation."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time
import os

URL = "https://job-boards.greenhouse.io/regscale/jobs/5083273007"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"

# Cover letter - personalized for RegScale (MCP server development mentioned in JD!)
COVER_LETTER = """Dear RegScale Hiring Team,

This role is an exact match for my current daily work. You're looking for someone who builds production AI systems end-to-end, designs agent orchestration layers, and develops MCP servers — I do all three, every day.

What I bring that maps directly to your requirements:

MCP Server Development: I've built 10+ production MCP servers in Python and Rust for Claude Code integration, exposing platform capabilities to AI systems exactly as you describe. My Wraith browser project (27K lines of Rust) includes a full MCP server with 80+ tools for browser automation, credential management, and knowledge graph operations.

AI Agent Orchestration: I architect and operate multi-step AI agent systems with tool calling, MCTS action planning, and failure handling. My Kalshi Weather Bot uses ML prediction models for autonomous trading (20x returns, 4 beta testers). I build the agent loop, the tool definitions, and the safety guardrails.

Production AI Infrastructure: I deploy and monitor GPU inference fleets (Tesla P40) with Docker container orchestration, Prometheus/Grafana observability, and CI/CD pipelines with automated testing gates. I understand inference cost optimization, caching strategies, and model selection tradeoffs at scale.

RAG & Knowledge Systems: My projects include vector search, embedding stores with cosine similarity, knowledge graph construction (petgraph), and adaptive caching with per-domain TTL learning — all in production.

I'm a US citizen based in California, available immediately, and comfortable with the full ownership model you describe — reliability, observability, cost management, and ongoing model behavior.

Best regards,
Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655
ridgecellrepair@gmail.com
github.com/suhteevah"""

def apply():
    print(f"[*] Starting RegScale application...")
    print(f"[*] URL: {URL}")
    print(f"[*] Resume: {RESUME}")

    if not os.path.exists(RESUME):
        print(f"[!] Resume not found: {RESUME}")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()

        print("[*] Navigating to RegScale job page...")
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        print("[*] Filling form fields...")

        # First Name
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        print("  - First Name: Matt")

        # Last Name
        page.get_by_role("textbox", name="Last Name").fill("Gates")
        print("  - Last Name: Gates")

        # Email
        page.get_by_role("textbox", name="Email").fill("ridgecellrepair@gmail.com")
        print("  - Email: ridgecellrepair@gmail.com")

        # Country dropdown (React combobox)
        country_combo = page.get_by_role("combobox", name="Country")
        country_combo.click()
        country_combo.fill("United States")
        time.sleep(0.5)
        country_combo.press("Enter")
        time.sleep(0.3)
        print("  - Country: United States")

        # Phone
        page.get_by_role("textbox", name="Phone").last.fill("5307863655")
        print("  - Phone: 5307863655")

        # Resume upload
        print("[*] Uploading resume...")
        resume_input = page.locator('input#resume[type="file"]')
        resume_input.set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded!")

        # Cover letter - write to temp file and upload
        cover_letter_path = os.path.join(os.path.dirname(__file__), "regscale_cover_letter.txt")
        with open(cover_letter_path, 'w', encoding='utf-8') as f:
            f.write(COVER_LETTER)

        cover_input = page.locator('input#cover_letter[type="file"]')
        cover_input.set_input_files(cover_letter_path)
        time.sleep(1)
        print("  - Cover letter uploaded!")

        # Website
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
        print("  - Website: github.com/suhteevah")

        # LinkedIn
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  - LinkedIn: set")

        # Visa sponsorship dropdown
        visa_combo = page.get_by_role("combobox", name="Will you now, or in the future, require Visa sponsorship")
        visa_combo.click()
        visa_combo.fill("No")
        time.sleep(0.5)
        visa_combo.press("Enter")
        time.sleep(0.3)
        print("  - Visa sponsorship: No")

        # EEO fields (voluntary)
        try:
            gender_combo = page.get_by_role("combobox", name="Gender")
            gender_combo.click()
            gender_combo.fill("Male")
            time.sleep(0.3)
            gender_combo.press("Enter")
            time.sleep(0.2)
            print("  - Gender: Male")
        except Exception as e:
            print(f"  - Gender: skipped ({e})")

        try:
            hispanic_combo = page.get_by_role("combobox", name="Hispanic/Latino")
            hispanic_combo.click()
            hispanic_combo.fill("No")
            time.sleep(0.3)
            hispanic_combo.press("Enter")
            time.sleep(0.2)
            print("  - Hispanic/Latino: No")
        except Exception as e:
            print(f"  - Hispanic/Latino: skipped ({e})")

        try:
            vet_combo = page.get_by_role("combobox", name="Veteran Status")
            vet_combo.click()
            vet_combo.fill("I am not")
            time.sleep(0.3)
            vet_combo.press("Enter")
            time.sleep(0.2)
            print("  - Veteran Status: I am not a protected veteran")
        except Exception as e:
            print(f"  - Veteran Status: skipped ({e})")

        try:
            disability_combo = page.get_by_role("combobox", name="Disability Status")
            disability_combo.click()
            disability_combo.fill("I do not want")
            time.sleep(0.3)
            disability_combo.press("Enter")
            time.sleep(0.2)
            print("  - Disability Status: I do not want to answer")
        except Exception as e:
            print(f"  - Disability Status: skipped ({e})")

        # Take screenshot before submit
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "regscale_pre_submit.png"), full_page=True)
        print("[*] Screenshot saved: regscale_pre_submit.png")

        # Submit
        print("[*] Submitting application...")
        page.get_by_role("button", name="Submit application").click()
        time.sleep(5)

        # Check result
        page.screenshot(path=os.path.join(os.path.dirname(__file__), "regscale_post_submit.png"), full_page=True)
        print("[*] Post-submit screenshot saved: regscale_post_submit.png")

        page_text = page.text_content("body")
        if "thank" in page_text.lower() or "submitted" in page_text.lower() or "received" in page_text.lower():
            print("[SUCCESS] Application submitted successfully!")
            browser.close()
            return True
        else:
            print(f"[?] Submit result unclear. Check screenshots.")
            # Keep browser open for 30s to debug
            print("[*] Keeping browser open for 30s for inspection...")
            time.sleep(30)
            browser.close()
            return False

if __name__ == "__main__":
    success = apply()
    if success:
        print("\n=== RegScale application SUBMITTED ===")
    else:
        print("\n=== RegScale application needs manual review ===")
