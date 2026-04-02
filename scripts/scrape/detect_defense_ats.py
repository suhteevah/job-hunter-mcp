"""Detect ATS and APIs for defense/enterprise companies."""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import urllib.request

# Check Lockheed's jobs page
for url in [
    'https://www.lockheedmartin.com/en-us/careers/jobs.html',
    'https://www.lockheedmartin.com/en-us/careers/jobs.html?search_query=software+engineer',
]:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read(40000).decode('utf-8', errors='replace')
            print('URL:', r.url[:80])
            # Algolia patterns
            app_ids = re.findall(r'appId[\'":\s]+["\']([A-Z0-9]{8,12})["\']', body, re.I)
            print('  Algolia App IDs:', app_ids)
            api_keys = re.findall(r'searchApiKey[\'":\s]+["\']([a-zA-Z0-9]{20,})["\']', body, re.I)
            print('  Algolia API Keys:', api_keys)
            idx_names = re.findall(r'indexName[\'":\s]+["\']([^"\']+)["\']', body, re.I)
            print('  Index names:', idx_names[:5])
            # Look for next.js data
            next_data = re.findall(r'__NEXT_DATA__[^{]*({.*?})\s*</script>', body, re.DOTALL)
            if next_data:
                print('  Next.js data found (len=%d)' % len(next_data[0]))
            # Look for any JSON with jobs
            job_jsons = re.findall(r'"jobs?":\s*(\[[^\]]{0,500}\])', body)
            if job_jsons:
                print('  Job JSON found:', job_jsons[0][:200])
    except Exception as e:
        print(url, 'Error:', str(e)[:60])

print()

# Check L3Harris SAP SuccessFactors API
print('Checking L3Harris SAP SuccessFactors...')
req = urllib.request.Request(
    'https://careers.l3harris.com/en',
    headers={'User-Agent': 'Mozilla/5.0'}
)
try:
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read(20000).decode('utf-8', errors='replace')
        # SAP patterns
        sap_urls = re.findall(r'https://[^"\'<>\s]*sap[^"\'<>\s]*', body, re.I)
        print('SAP URLs:', sap_urls[:3])
        sf_urls = re.findall(r'https://[^"\'<>\s]*successfactor[^"\'<>\s]*', body, re.I)
        print('SF URLs:', sf_urls[:3])
        # Radancy API
        radancy = re.findall(r'https://[^"\'<>\s]*radancy[^"\'<>\s]*', body, re.I)
        print('Radancy URLs:', radancy[:3])
        # Look for jobs JSON endpoint
        job_endpoints = re.findall(r'["\']https?://[^"\']*(?:jobs|positions|search)[^"\']{0,80}["\']', body, re.I)
        print('Job endpoints:', job_endpoints[:5])
except Exception as e:
    print('Error:', str(e)[:60])

print()
# Check Boeing SAP SuccessFactors
print('Checking Boeing...')
req = urllib.request.Request(
    'https://jobs.boeing.com/search-jobs',
    headers={'User-Agent': 'Mozilla/5.0'}
)
try:
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read(20000).decode('utf-8', errors='replace')
        # SAP patterns
        radancy = re.findall(r'https://[^"\'<>\s]*radancy[^"\'<>\s]{0,80}', body, re.I)
        print('Radancy URLs:', radancy[:3])
        # Look for jobs JSON endpoint
        job_endpoints = re.findall(r'data-[a-z-]+=["\']https?://[^"\']*["\']', body)
        print('Data attributes with URLs:', job_endpoints[:5])
        # JSON config
        configs = re.findall(r'window\.[A-Za-z_]+ = ({[^;]{50,}})', body)
        if configs:
            print('Window configs (first 400):', configs[0][:400])
except Exception as e:
    print('Error:', str(e)[:60])
