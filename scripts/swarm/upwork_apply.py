"""Quick Upwork proposal submit via Chrome CDP."""
import sys, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

JOB_URL = sys.argv[1] if len(sys.argv) > 1 else None
MAX_CONNECTS = 10

COVER_LETTER = """Hi - this role is an exact match for my daily work. I build Claude-powered systems professionally and can hit the ground running on your implementation.

What I bring:
- Built 10+ production MCP servers for Claude Code integration (Python and Rust)
- Deep experience with Claude API, prompt engineering, and workflow automation
- Created autonomous agent systems using Claude for document processing and decision support
- Python SDK and Node SDK integration, FastAPI services, Docker deployments
- Currently building Wraith Browser - a 27K-line Rust AI agent orchestration platform
- Built Kalshi Weather Bot - autonomous trading system with 20x returns

I am US-based (California), available immediately, and comfortable working async.

- Matt Gates
Technical Director, Ridge Cell Repair LLC
(530) 786-3655"""

if not JOB_URL:
    print("Usage: python upwork_apply.py <job_url>")
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = browser.contexts[0]
    page = [pg for pg in ctx.pages if 'upwork' in pg.url.lower()][0]

    page.goto(JOB_URL, timeout=20000)
    time.sleep(4)
    print(f"Title: {page.title()[:80]}")

    text = page.evaluate('() => document.body.innerText')
    cm = re.search(r'(\d+)\s*Connects', text)
    connects = int(cm.group(1)) if cm else -1
    print(f"Connects: {connects}")

    if connects > MAX_CONNECTS:
        print(f"SKIP: {connects} > {MAX_CONNECTS}")
        browser.close()
        sys.exit(0)

    if 'already submitted' in text.lower() or 'withdraw' in text.lower():
        print("Already applied!")
        browser.close()
        sys.exit(0)

    # Click Apply
    btn = page.query_selector('button:has-text("Apply now"), a:has-text("Apply now")')
    if not btn:
        print("No Apply button")
        browser.close()
        sys.exit(1)

    btn.click()
    time.sleep(5)
    print(f"Form: {page.url[:80]}")

    # Fill cover letter
    for ta in page.query_selector_all('textarea'):
        ta.click()
        time.sleep(0.3)
        ta.fill(COVER_LETTER)
        print("Cover letter filled")
        break

    # Rate frequency dropdown (select or combobox)
    for sel in page.query_selector_all('select'):
        opts = sel.evaluate('el => Array.from(el.options).map(o => o.text)')
        if any('never' in o.lower() for o in opts):
            sel.select_option(label='Never')
            print("Frequency: Never")

    # Combobox version
    for cb in page.query_selector_all('[role="combobox"]'):
        label = cb.evaluate('el => (el.closest("div")?.querySelector("label")?.textContent || "").toLowerCase()')
        if 'frequency' in label or 'increase' in label:
            cb.click()
            time.sleep(1)
            opt = page.query_selector('[role="option"]:has-text("Never"), li:has-text("Never")')
            if opt:
                opt.click()
                print("Combobox frequency: Never")
                time.sleep(0.5)

    time.sleep(2)

    # Check errors
    errors = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
            .map(e => e.textContent.trim()).filter(t => t.length > 0 && t.length < 200);
    }""")
    if errors:
        print(f"ERRORS: {errors}")

    # Submit
    submit = None
    for b in page.query_selector_all('button'):
        t = b.text_content().strip().lower()
        if 'send' in t and 'connect' in t:
            submit = b
            break
    if not submit:
        for b in page.query_selector_all('button'):
            t = b.text_content().strip().lower()
            if 'send' in t or 'submit' in t:
                submit = b
                break

    if submit:
        disabled = submit.get_attribute('disabled')
        btn_text = submit.text_content().strip()
        print(f"Submit: \"{btn_text}\" disabled={disabled}")
        if not disabled:
            submit.click()
            time.sleep(6)
            print(f"Final: {page.url[:80]}")
            final_text = page.evaluate('() => document.body.innerText')
            if 'submitted' in final_text.lower():
                print(">>> PROPOSAL SUBMITTED <<<")
            else:
                # Check for post-submit errors
                errs = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
                        .map(e => e.textContent.trim()).filter(t => t.length > 0);
                }""")
                if errs:
                    print(f"Post-submit errors: {errs[:3]}")
                else:
                    print("Status unclear - check Chrome")
        else:
            print("Button disabled - missing required field")
            # Print all visible form fields for debugging
            fields = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input:not([type=hidden]), textarea, select, [role=combobox]'))
                    .map(e => ({tag: e.tagName, name: e.name, required: e.required, value: e.value?.substring(0,30)}));
            }""")
            for f in fields:
                print(f"  {f}")
    else:
        print("No submit button found")

    browser.close()
