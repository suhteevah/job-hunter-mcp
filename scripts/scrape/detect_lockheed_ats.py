"""Find Lockheed Martin's Algolia job search config."""
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import urllib.request

req = urllib.request.Request(
    'https://www.lockheedmartin.com/en-us/careers/index.html',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)
with urllib.request.urlopen(req, timeout=10) as r:
    body = r.read(50000).decode('utf-8', errors='replace')

print('Body size:', len(body))

# Find Algolia config
algolia_apps = re.findall(r'[Aa]pplication[Ii]d[\'":\s]+["\']([A-Z0-9]{8,12})["\']', body)
print('Algolia App IDs:', algolia_apps)

algolia_keys = re.findall(r'[Aa]pi[Kk]ey[\'":\s]+["\']([a-f0-9]{16,40})["\']', body)
print('Algolia API Keys:', algolia_keys)

indices = re.findall(r'indexName[\'":\s]+["\']([^"\']+)["\']', body, re.I)
print('Index names:', indices)

# Look for search API calls
api_calls = re.findall(r'https://[A-Z0-9]+-dsn\.algolia\.net[^"\'<>\s]*', body)
print('Algolia API calls:', api_calls)

# Check for other job search APIs
search_urls = re.findall(r'https://[^"\'<>\s]*(?:job|career|search|recruit)[^"\'<>\s]*api[^"\'<>\s]*', body, re.I)
print('Search API URLs:', search_urls[:5])

# Print JS file references that might contain config
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', body)
print('JS files:', [f for f in js_files if 'career' in f.lower() or 'job' in f.lower() or 'algolia' in f.lower()][:10])
