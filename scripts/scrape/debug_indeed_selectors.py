"""Debug script to check Indeed page structure and find working selectors."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import re, time

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://localhost:9222')
    ctx = browser.contexts[0]
    page = ctx.pages[0]

    page.goto('https://www.indeed.com/jobs?q=software+engineer&l=remote&filter=0',
              timeout=20000, wait_until='domcontentloaded')
    time.sleep(4)

    cur_url = page.url
    print('Current URL:', cur_url[:100])
    print('Page title:', page.title())

    html = page.content()
    print('HTML size:', len(html))

    # Check job keys
    jks = re.findall(r'data-jk=["\']([a-f0-9]{16})["\']', html)
    print('Job keys found:', len(jks), jks[:3])

    if '__cf_chl' in html or 'cf_chl' in cur_url:
        print('CF CHALLENGE ACTIVE')
    else:
        print('No CF challenge detected')

    # Try selectors
    for sel in ['[data-jk]', '.jobCard_mainContent', '.tapItem',
                '.job_seen_beacon', 'a[id^=job_]', '[class*=JobCard]',
                '[data-mobtk]', 'li[class*=css-]', '.css-1m4cuuf']:
        try:
            count = page.locator(sel).count()
            if count > 0:
                print(f'  SELECTOR HIT: {sel} -> {count} elements')
        except Exception:
            pass

    # Print first 2000 chars of body
    print('Body snippet:', html[500:2500])
    browser.close()
