import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
db = sqlite3.connect(r'C:\Users\Matt\.job-hunter-mcp\jobs.db')
c = db.cursor()

c.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' AND source LIKE 'greenhouse%' GROUP BY source ORDER BY COUNT(*) DESC")
print('Greenhouse viable (auto-applyable):')
t = 0
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')
    t += r[1]
print(f'  TOTAL GH: {t}')

c.execute("SELECT source, COUNT(*) FROM jobs WHERE fit_score >= 60 AND status='new' AND source NOT LIKE 'greenhouse%' GROUP BY source ORDER BY COUNT(*) DESC LIMIT 15")
print('\nOther viable (discovery only):')
t2 = 0
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')
    t2 += r[1]
print(f'  TOTAL OTHER: {t2}')

print(f'\nGRAND TOTAL VIABLE: {t + t2}')
