import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from flaresolverr_indeed import IndeedSession
session = IndeedSession()
html = session.get_page('https://www.indeed.com/jobs?q=AI+engineer+python&l=remote&sort=date')

# Find data-jk patterns
jks = re.findall(r'data-jk=["\']([a-f0-9]+)["\']', html)
unique_jks = list(set(jks))
print(f'data-jk found: {len(jks)} total, {len(unique_jks)} unique -> {unique_jks[:5]}')

# Find jobTitle patterns
titles = re.findall(r'jobTitle[^>]*>([^<]{3,80})<', html)
print(f'jobTitle matches: {titles[:10]}')

# Find the mosaic structure
cards = re.findall(r'class="[^"]*job_seen_beacon[^"]*"', html)
print(f'job_seen_beacon: {len(cards)}')

cardlist = re.findall(r'class="[^"]*cardOutline[^"]*"', html)
print(f'cardOutline: {len(cardlist)}')

rc = re.findall(r'class="[^"]*resultContent[^"]*"', html)
print(f'resultContent: {len(rc)}')

# Try to find job data in script tags (JSON)
script_data = re.findall(r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});', html, re.DOTALL)
print(f'mosaic JSON blocks: {len(script_data)}')

# Check for jobcard JSON data
json_blocks = re.findall(r'"jobkey"\s*:\s*"([a-f0-9]+)"', html)
print(f'jobkey in JSON: {len(json_blocks)} -> {json_blocks[:5]}')

# Dump a sample card area
if unique_jks:
    jk = unique_jks[0]
    idx = html.find(f'data-jk="{jk}"')
    if idx >= 0:
        sample = html[max(0,idx-200):idx+2000]
        print(f'\n--- Sample around data-jk="{jk}" ---')
        print(sample[:3000])

session.close()
