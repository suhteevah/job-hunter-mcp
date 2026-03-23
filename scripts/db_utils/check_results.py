from src import db
import json

s = db.get_stats()
print(json.dumps(s, indent=2))
print()

jobs = db.get_jobs(min_score=20, limit=10)
print("TOP MATCHES (score >= 20):")
for j in jobs:
    print(f"  [{j['fit_score']}] {j['title']} @ {j['company']}")
    print(f"    {j['url']}")
    print(f"    Fit: {j['fit_reason']}")
    print()
