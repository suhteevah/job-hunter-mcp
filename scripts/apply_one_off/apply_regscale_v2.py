"""Apply to RegScale Senior AI Engineer — v2 with fixed React comboboxes."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import time
import os

URL = "https://job-boards.greenhouse.io/regscale/jobs/5083273007"
RESUME = r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx"
COVER_LETTER_PATH = r"J:\job-hunter-mcp\regscale_cover_letter.txt"

def select_react_dropdown(page, combobox_name, value, partial=False):
    """Handle React-Select combobox: click, type, wait for option, click option."""
    combo = page.get_by_role("combobox", name=combobox_name)
    combo.click()
    time.sleep(0.3)
    combo.fill(value)
    time.sleep(0.8)

    # Find the matching option in the dropdown menu
    if partial:
        option = page.locator('[class*="option"]').filter(has_text=value).first
    else:
        option = page.locator('[class*="option"]').filter(has_text=value).first

    if option.count() > 0 and option.is_visible():
        option.click()
        print(f"  - {combobox_name}: {value} (clicked option)")
    else:
        # Fallback: arrow down + enter
        combo.press("ArrowDown")
        time.sleep(0.2)
        combo.press("Enter")
        print(f"  - {combobox_name}: {value} (ArrowDown+Enter)")
    time.sleep(0.3)

def apply():
    print(f"[*] Starting RegScale application v2...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        print("[*] Filling text fields...")
        page.get_by_role("textbox", name="First Name", exact=True).fill("Matt")
        page.get_by_role("textbox", name="Last Name").fill("Gates")
        page.get_by_role("textbox", name="Email").fill("ridgecellrepair@gmail.com")
        print("  - Name/Email filled")

        print("[*] Setting Country dropdown...")
        select_react_dropdown(page, "Country", "United States")

        # Verify country was set
        country_val = page.locator('#country').input_value()
        print(f"  - Country input value: '{country_val}'")

        # If country is still empty, try clicking the visible option text
        if not country_val or country_val == "":
            print("  [!] Country not set, trying alternative...")
            combo = page.get_by_role("combobox", name="Country")
            combo.click()
            combo.fill("United")
            time.sleep(1)
            # Try to find and click any visible option
            options = page.locator('[class*="option"]').all()
            print(f"  Found {len(options)} dropdown options")
            for opt in options:
                if opt.is_visible():
                    txt = opt.text_content()
                    print(f"    Option: {txt}")
                    if "United States" in txt:
                        opt.click()
                        print(f"  - Clicked: {txt}")
                        break
            time.sleep(0.5)

        page.get_by_role("textbox", name="Phone").last.fill("5307863655")
        print("  - Phone: 5307863655")

        # Resume
        print("[*] Uploading resume...")
        page.locator('input#resume[type="file"]').set_input_files(RESUME)
        time.sleep(1)
        print("  - Resume uploaded")

        # Cover letter
        print("[*] Uploading cover letter...")
        page.locator('input#cover_letter[type="file"]').set_input_files(COVER_LETTER_PATH)
        time.sleep(1)
        print("  - Cover letter uploaded")

        # Website + LinkedIn
        page.get_by_role("textbox", name="Website").fill("https://github.com/suhteevah")
        page.get_by_role("textbox", name="LinkedIn Profile").fill("https://www.linkedin.com/in/matt-michels-b836b260/")
        print("  - Website + LinkedIn filled")

        # Visa sponsorship
        print("[*] Setting Visa sponsorship...")
        select_react_dropdown(page, "Will you now, or in the future, require Visa sponsorship", "No")

        # EEO fields (voluntary but let's fill them)
        print("[*] Setting EEO fields...")
        try:
            select_react_dropdown(page, "Gender", "Male")
        except Exception as e:
            print(f"  - Gender: skipped ({e})")
        try:
            select_react_dropdown(page, "Hispanic/Latino", "No")
        except Exception as e:
            print(f"  - Hispanic: skipped ({e})")
        try:
            select_react_dropdown(page, "Veteran Status", "I am not a protected veteran")
        except Exception as e:
            print(f"  - Veteran: skipped ({e})")
        try:
            select_react_dropdown(page, "Disability Status", "I do not want to answer")
        except Exception as e:
            print(f"  - Disability: skipped ({e})")

        # Final check of required fields
        print("\n[*] Final field check:")
        required = page.locator('[aria-required="true"]').all()
        all_ok = True
        for req in required:
            label = req.get_attribute("aria-label") or req.get_attribute("id") or "?"
            try:
                val = req.input_value()
            except:
                val = "(non-input)"
            status = "OK" if val else "EMPTY"
            if not val:
                all_ok = False
            print(f"  {status}: {label} = '{str(val)[:60]}'")

        page.screenshot(path=r"J:\job-hunter-mcp\regscale_v2_pre_submit.png", full_page=True)

        if not all_ok:
            print("\n[!] Some required fields empty. Checking if we can still submit...")

        # Submit
        print("\n[*] SUBMITTING...")
        submit = page.get_by_role("button", name="Submit application")
        submit.scroll_into_view_if_needed()
        time.sleep(0.5)
        submit.click()
        time.sleep(8)

        # Check result
        body = page.text_content("body")
        page.screenshot(path=r"J:\job-hunter-mcp\regscale_v2_result.png", full_page=True)

        if "thank" in body.lower() or "submitted" in body.lower() or "received" in body.lower() or "application" in body.lower()[:200]:
            print("\n=== SUCCESS: RegScale application SUBMITTED ===")
            browser.close()
            return True

        # Check for validation errors
        errors = page.locator('[class*="error"]').all()
        for err in errors[:10]:
            txt = err.text_content()
            if txt and txt.strip() and len(txt.strip()) < 200:
                print(f"  VALIDATION ERROR: {txt.strip()}")

        print("\n[?] Result unclear. Check regscale_v2_result.png")
        print("[*] Browser stays open 60s for manual inspection...")
        time.sleep(60)
        browser.close()
        return False

if __name__ == "__main__":
    success = apply()
    sys.exit(0 if success else 1)
