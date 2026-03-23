import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from flaresolverr_indeed import IndeedSession
session = IndeedSession()
html = session.get_page('https://www.indeed.com/jobs?q=AI+engineer+python&l=remote&sort=date')

# Check for embedded job descriptions in mosaic data
mosaic = re.findall(
    r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*({.*?});\s*</script>',
    html, re.DOTALL
)
print(f"Mosaic blocks: {len(mosaic)}")

if mosaic:
    try:
        data = json.loads(mosaic[0])
        # Explore structure
        print(f"Top keys: {list(data.keys())[:10]}")
        meta = data.get('metaData', {})
        print(f"metaData keys: {list(meta.keys())[:15]}")
        results = data.get('results', data.get('jobList', data.get('cards', [])))
        if isinstance(results, list):
            print(f"Results: {len(results)}")
            if results:
                print(f"First result keys: {list(results[0].keys())[:20]}")
                r = results[0]
                print(f"  title: {r.get('title', r.get('displayTitle', 'N/A'))}")
                print(f"  company: {r.get('company', r.get('companyName', 'N/A'))}")
                desc = r.get('snippet', r.get('description', r.get('jobSnippet', '')))
                print(f"  snippet: {str(desc)[:200]}")
        else:
            print(f"results type: {type(results)}")
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f"  list key '{k}': {len(v)} items, first type: {type(v[0])}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(mosaic[0][:500])

# Also check for vjs inline data
vjs = re.findall(r'var defined_job_result = ({.*?});', html, re.DOTALL)
print(f"\nvjs inline data blocks: {len(vjs)}")

# Check for jobmap
jobmap = re.findall(r'jobmap\[(\d+)\]\s*=\s*({.*?});', html, re.DOTALL)
print(f"jobmap entries: {len(jobmap)}")

session.close()
