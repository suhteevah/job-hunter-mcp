import json, sys
sys.stdout.reconfigure(encoding='utf-8')
from src import db

jobs = db.get_jobs(min_score=60, limit=20)
for j in jobs:
    print(json.dumps({
        "id": j["id"],
        "title": j["title"],
        "company": j["company"],
        "score": j["fit_score"],
        "url": j["url"],
        "description": (j.get("description") or "")[:800]
    }, ensure_ascii=True))
    print("---")
