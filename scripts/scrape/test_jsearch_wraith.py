import sys, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "845423ab1emshdc9d0de9746fcdbp175051jsnde0ca0fd970f"

resp = requests.get(
    "https://jsearch.p.rapidapi.com/search",
    headers={
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    },
    params={"query": "AI automation engineer remote", "num_pages": "1"},
    timeout=15,
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json().get("data", [])
    print(f"Jobs returned: {len(data)}")
    for j in data[:5]:
        title = j.get("job_title", "?")
        company = j.get("employer_name", "?")
        url = j.get("job_apply_link", "?")
        print(f"  {title} @ {company}")
        print(f"    {url}")
else:
    print(f"Error: {resp.text[:500]}")
