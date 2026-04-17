"""Probe OnBoard combobox options for Work Authorization and How did you hear."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import time
from playwright.sync_api import sync_playwright

URL = "https://job-boards.greenhouse.io/onboardmeetings/jobs/5813540004"

def probe_combobox(page, field_id, label):
    """Click combobox and read all options."""
    print(f"\n=== OPTIONS FOR: {label} (#{field_id}) ===")
    try:
        inp = page.locator(f"#{field_id}")
        inp.scroll_into_view_if_needed()
        time.sleep(0.3)
        inp.click()
        time.sleep(0.3)
        inp.fill("")  # clear to show all options
        time.sleep(1.0)

        # Read all listbox options
        options = page.locator(f"[id='{field_id}-listbox'] li, ul[role='listbox'] li").all()
        if not options:
            # Try broader selector
            options = page.locator("[role='listbox'] li, [role='option']").all()

        for i, opt in enumerate(options):
            try:
                txt = opt.inner_text().strip()
                print(f"  [{i}] '{txt}'")
            except:
                pass

        if not options:
            print("  (no options found)")

        # Close by pressing Escape
        inp.press("Escape")
        time.sleep(0.3)
    except Exception as e:
        print(f"  [ERR] {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=200)
        page = browser.new_page()
        page.set_default_timeout(15000)
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        probe_combobox(page, "question_15505052004", "Work Authorization")
        probe_combobox(page, "question_15505055004", "How did you hear about this job")
        probe_combobox(page, "question_15505054004", "Personal pronouns")
        probe_combobox(page, "question_15505053004", "Sponsorship")
        probe_combobox(page, "question_15627841004", "LinkedIn profile")

        browser.close()

if __name__ == "__main__":
    main()
