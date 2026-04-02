import sqlite3
conn = sqlite3.connect('C:/Users/Matt/.job-hunter-mcp/jobs.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", c.fetchall())
c.execute("PRAGMA table_info(jobs)")
print("Jobs schema:", c.fetchall())
conn.close()
