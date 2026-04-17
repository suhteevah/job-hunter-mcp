"""Check RegScale form state and retry submit if needed."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time

URL = "https://job-boards.greenhouse.io/regscale/jobs/5083273007"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
COVER_LETTER_PATH = r"J:\job-hunter-mcp\regscale_cover_letter.txt"

def check_and_submit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=300)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        # Fill everything again (fresh page)
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name").fill("Gates")
        page.get_by_role("textbox", name="Email").fill("ridgecellrepair@gmail.com")

        # Country
        country = page.get_by_role("combobox", name="Country")
        country.click()
        country.fill("United States")
        time.sleep(0.5)
        country.press("Enter")
        time.sleep(0.3)

        # Phone
        page.get_by_role("textbox", name="Phone").last.fill("5307863655")

        # Resume
        page.locator('input#resume[type="file"]').set_input_files(RESUME)
        time.sleep(1)

        # Cover letter
        page.locator('input#cover_letter[type="file"]').set_input_files(COVER_LETTER_PATH)
        time.sleep(1)

        # Website + LinkedIn
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")

        # Visa
        visa = page.get_by_role("combobox", name="Will you now, or in the future, require Visa sponsorship")
        visa.click()
        visa.fill("No")
        time.sleep(0.3)
        visa.press("Enter")
        time.sleep(0.3)

        # Scroll to bottom and check for errors
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # Check for any error messages
        errors = page.locator('[class*="error"], [aria-invalid="true"], [class*="Error"]').all()
        print(f"[*] Found {len(errors)} error elements")
        for err in errors[:10]:
            txt = err.text_content()
            if txt and txt.strip():
                print(f"  ERROR: {txt.strip()}")

        # Check required fields
        required = page.locator('[aria-required="true"]').all()
        print(f"\n[*] Required fields ({len(required)}):")
        for req in required:
            label = req.get_attribute("aria-label") or req.get_attribute("id") or "unknown"
            val = req.input_value() if req.evaluate("el => el.tagName") == "INPUT" else ""
            filled = "OK" if val else "EMPTY"
            print(f"  {filled}: {label} = '{val[:50]}'")

        # Screenshot the form area
        page.screenshot(path=r"J:\job-hunter-mcp\regscale_debug.png", full_page=True)

        # Try clicking submit
        print("\n[*] Clicking Submit application...")
        submit_btn = page.get_by_role("button", name="Submit application")
        submit_btn.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit_btn.click()
        time.sleep(5)

        # Check for success
        body = page.text_content("body")
        if "thank" in body.lower() or "submitted" in body.lower() or "received" in body.lower():
            print("\n[SUCCESS] Application submitted!")
            page.screenshot(path=r"J:\job-hunter-mcp\regscale_success.png")
            browser.close()
            return True

        # Check for new errors after submit
        print("\n[*] Checking for errors after submit attempt...")
        errors_after = page.locator('[class*="error"]').all()
        for err in errors_after[:10]:
            txt = err.text_content()
            if txt and txt.strip() and len(txt.strip()) < 200:
                print(f"  POST-SUBMIT ERROR: {txt.strip()}")

        page.screenshot(path=r"J:\job-hunter-mcp\regscale_after_submit.png", full_page=True)
        print("[*] Keeping browser open for 60s...")
        time.sleep(60)
        browser.close()
        return False

if __name__ == "__main__":
    check_and_submit()
