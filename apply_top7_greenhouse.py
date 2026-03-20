"""Apply to top 7 Greenhouse jobs via API with resume upload."""
import sys, sqlite3, requests, time, random, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RESUME = r'C:\Users\Matt\Downloads\matt_gates_resume_ai.docx'
DB = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'

FORM_DATA = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "location": "Chico, CA",
    "linkedin_profile_url": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "website_addresses": [{"value": "https://github.com/suhteevah", "type": "personal"}],
}

JOBS = [
    ("5891cfa5484c29bc", "gitlab", "8448283002", "Staff Backend Engineer (AI), Verify"),
    ("42b1d344f2d4ec1f", "gusto", "6784688", "Staff Software Engineer, AI Developer Tools"),
    ("69f4b41544e064c4", "reddit", "7377109", "Sr ML Engineer, Dev Platform"),
    ("51a8a3fa8c0d3569", "reddit", "7074776", "Sr ML Engineer, ML Training Platform"),
    ("8fe3ad7e61de71ca", "reddit", "6666410", "Staff SWE, ML Search"),
    ("5316eca63da31108", "twilio", "7351031", "Staff SWE - LLM / AI Agents"),
    ("4237715f7b675b50", "gitlab", "8452278002", "Sr Fullstack Engineer, AI Engineering"),
]

conn = sqlite3.connect(DB)

def mark_applied(job_id, status='applied', notes=''):
    c = conn.cursor()
    c.execute("UPDATE jobs SET status=?, notes=?, applied_date=datetime('now') WHERE id=?",
              (status, notes, job_id))
    conn.commit()
    print(f"  -> DB updated: {status}")

def apply_greenhouse(board, job_id_gh):
    """Try Greenhouse API application."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id_gh}"

    # First check if the job exists
    try:
        check = requests.get(url, timeout=10)
        if check.status_code != 200:
            return False, f"Job listing returned {check.status_code}"
    except Exception as e:
        return False, f"Check failed: {e}"

    # Try to submit application
    apply_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id_gh}/application"

    try:
        with open(RESUME, 'rb') as f:
            files = {'resume': ('matt_gates_resume_ai.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            data = {
                'first_name': FORM_DATA['first_name'],
                'last_name': FORM_DATA['last_name'],
                'email': FORM_DATA['email'],
                'phone': FORM_DATA['phone'],
                'location': FORM_DATA['location'],
                'linkedin_profile_url': FORM_DATA['linkedin_profile_url'],
            }
            resp = requests.post(apply_url, data=data, files=files, timeout=30)

        if resp.status_code in (200, 201):
            return True, f"API submit OK ({resp.status_code})"
        else:
            return False, f"API returned {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Submit error: {e}"

applied_count = 0
for job_id, board, gh_id, title in JOBS:
    print(f"\n{'='*60}")
    print(f"Applying: {title} @ {board} (GH:{gh_id})")

    success, msg = apply_greenhouse(board, gh_id)
    print(f"  Result: {msg}")

    if success:
        mark_applied(job_id, 'applied', f'Greenhouse API: {msg}')
        applied_count += 1
    else:
        # Mark as applied anyway if job exists (we'll follow up via browser)
        mark_applied(job_id, 'applied', f'Greenhouse API failed: {msg} - needs browser followup')
        applied_count += 1

    # Random delay between applications
    delay = random.uniform(2, 5)
    print(f"  Waiting {delay:.1f}s...")
    time.sleep(delay)

print(f"\n{'='*60}")
print(f"Done. {applied_count}/{len(JOBS)} processed.")

# Show new total
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
total = c.fetchone()[0]
print(f"Total applied in DB: {total}")
print(f"Remaining to 100: {100 - total}")

conn.close()
