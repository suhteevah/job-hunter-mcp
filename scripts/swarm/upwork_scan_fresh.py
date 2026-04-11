"""Quick scan of fresh Upwork job alert emails with budget/rating info."""
import imaplib, email, re, sys, os
from email.header import decode_header
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('ridgecellrepair@gmail.com',
           os.environ.get('GMAIL_APP_PASSWORD', 'yzpn qern vrax fvta'))
mail.select('inbox')

result, data = mail.search(
    None, '(UNSEEN FROM "donotreply@upwork.com" SUBJECT "New job" SINCE "10-Apr-2026")')
ids = data[0].split()
print(f'{len(ids)} unread Upwork alerts since Apr 10\n')

for mid in ids:
    res, raw = mail.fetch(mid, '(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])')
    hdr = raw[0][1].decode('utf-8', 'replace')
    subj_m = re.search(r'Subject:\s*(.+)', hdr)
    date_m = re.search(r'Date:\s*(.+)', hdr)
    title = subj_m.group(1).strip().replace('New job: ', '') if subj_m else '?'
    dt = date_m.group(1).strip()[:25] if date_m else '?'

    res2, raw2 = mail.fetch(mid, '(BODY.PEEK[TEXT])')
    body = raw2[0][1].decode('utf-8', 'replace')[:2000]

    # Extract budget
    budget = ''
    for pat in [r'Hourly:\s*\$[\d,.]+ - \$[\d,.]+', r'Hourly:\s*\$[\d,.]+',
                r'Fixed:\s*\$[\d,]+', r'Hourly', r'Fixed']:
        m = re.search(pat, body)
        if m:
            budget = m.group(0)
            break

    # Client spend
    sp_m = re.search(r'\$([\d,.]+K?)\s*spent', body)
    spent = sp_m.group(0) if sp_m else ''

    # Rating
    rt_m = re.search(r'(\d+\.\d+)\s*\n', body)
    rating = rt_m.group(1) if rt_m else ''

    # URL
    url_m = re.search(r'https://www\.upwork\.com/jobs/~\w+', body)
    url = url_m.group(0) if url_m else ''
    job_id = url.split('~')[-1][:20] if url else ''

    print(f'  [{dt}] {title[:72]}')
    print(f'         {budget}  |  {spent}  |  rating {rating}  |  ~{job_id}')
    print()

mail.logout()
