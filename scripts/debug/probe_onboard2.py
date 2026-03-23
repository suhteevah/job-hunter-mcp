"""Probe OnBoard combobox options using aria-labelledby."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import time
from playwright.sync_api import sync_playwright

URL = "https://job-boards.greenhouse.io/onboardmeetings/jobs/5813540004"

def probe_combobox(page, field_id, label):
    print(f"\n=== OPTIONS FOR: {label} (#{field_id}) ===")
    try:
        inp = page.locator(f"#{field_id}")
        inp.scroll_into_view_if_needed()
        time.sleep(0.3)
        # Close any open dropdown first
        page.keyboard.press("Escape")
        time.sleep(0.3)
        inp.click()
        time.sleep(0.5)
        # Don't fill - just click to open the dropdown
        # Read aria-controls or the listbox associated with this specific input
        listbox_id = inp.evaluate("e => e.getAttribute('aria-controls') || e.getAttribute('aria-owns') || ''")
        print(f"  aria-controls: {listbox_id}")

        if listbox_id:
            options = page.locator(f"#{listbox_id} [role='option'], #{listbox_id} li").all()
        else:
            # Fallback: find listbox that appeared near this input
            options = page.locator(f"#{field_id}-listbox [role='option'], #{field_id}-listbox li").all()

        for i, opt in enumerate(options):
            try:
                txt = opt.inner_text().strip()
                val = opt.evaluate("e => e.getAttribute('data-value') || e.getAttribute('value') || ''")
                print(f"  [{i}] '{txt}' (val='{val}')")
            except:
                pass

        if not options:
            # Try to dump all visible listbox/option content
            all_opts = page.evaluate("""() => {
                const listboxes = document.querySelectorAll('[role="listbox"]');
                const result = [];
                listboxes.forEach((lb, i) => {
                    const opts = lb.querySelectorAll('[role="option"], li');
                    const items = [];
                    opts.forEach(o => items.push(o.textContent.trim()));
                    result.push({id: lb.id, class: lb.className, count: items.length, items: items.slice(0, 20)});
                });
                return result;
            }""")
            print(f"  All visible listboxes: {all_opts}")

        page.keyboard.press("Escape")
        time.sleep(0.3)
    except Exception as e:
        print(f"  [ERR] {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        page.set_default_timeout(15000)
        page.goto(URL, wait_until="networkidle")
        time.sleep(2)

        # First close the phone dropdown if it appeared
        page.keyboard.press("Escape")
        time.sleep(0.3)

        probe_combobox(page, "question_15505052004", "Work Authorization")
        probe_combobox(page, "question_15505055004", "How did you hear")
        probe_combobox(page, "question_15505054004", "Personal pronouns")
        probe_combobox(page, "question_15505053004", "Sponsorship")
        probe_combobox(page, "question_15627841004", "LinkedIn profile")

        browser.close()

if __name__ == "__main__":
    main()
