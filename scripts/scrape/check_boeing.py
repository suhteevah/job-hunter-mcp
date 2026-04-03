import sqlite3
con = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM jobs WHERE fit_score IS NULL")
print('Total unscored jobs:', cur.fetchone()[0])
cur.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score IS NULL GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10")
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')
