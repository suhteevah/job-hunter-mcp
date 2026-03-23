import sys, os, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = conn.cursor()

# Show all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])

# Check for api_keys table schema
for table in ['api_keys', 'config', 'settings']:
    try:
        c.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
        row = c.fetchone()
        if row: print(f"\n{table} schema: {row[0]}")
        c.execute(f"SELECT * FROM {table} LIMIT 5")
        for r in c.fetchall():
            print(f"  {r}")
    except Exception as e:
        pass

# Check env for RAPIDAPI_KEY
rk = os.environ.get('RAPIDAPI_KEY', '')
print(f"\nRAPIDAPI_KEY env: {'SET (' + rk[:15] + '...)' if rk else 'NOT SET'}")

# Check config.py for the key
try:
    sys.path.insert(0, r'J:\job-hunter-mcp\src')
    from config import RAPIDAPI_KEY
    print(f"config.RAPIDAPI_KEY: {RAPIDAPI_KEY[:15]}..." if RAPIDAPI_KEY else "config.RAPIDAPI_KEY: empty")
except Exception as e:
    print(f"config import: {e}")

# Also check secrets.json
import json
try:
    with open(r'J:\job-hunter-mcp\secrets.json') as f:
        secrets = json.load(f)
    for k,v in secrets.items():
        print(f"secrets.json: {k} = {str(v)[:15]}...")
except Exception as e:
    print(f"secrets.json: {e}")

conn.close()
