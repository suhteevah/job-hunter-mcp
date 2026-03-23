import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
import time
import sqlite3

APPLICANT = {
    "first_name": "Matt",
    "last_name": "Gates",
    "email": "ridgecellrepair@gmail.com",
    "phone": "5307863655",
    "linkedin": "https://www.linkedin.com/in/matt-michels-b836b260/",
    "github": "https://github.com/suhteevah",
    "location": "Chico, CA, United States",
    "resume_path": r"C:\Users\Matt\Downloads\matt_gates_resume_ai.docx",
}

JOBS = [
    {"id": "43ae03e22e623c65", "company": "Remote People", "title": "Senior AI Engineer", "gh_job_id": "4721961101", "board": "remotepeople", "eu": True},
    {"id": "c6ece1abcf89eb6b", "company": "WITHIN", "title": "AI Engineer", "gh_job_id": "5056863007", "board": "agencywithin"},
    {"id": "9239b915", "company": "Reddit", "title": "Staff Software Engineer, Ads API", "gh_job_id": "7167632", "board": "reddit"},
    {"id": "2fd0f5cd", "company": "ZipRecruiter", "title": "Senior Software Engineer, ML", "gh_job_id": "5167472", "board": "ziprecruiter"},
    {"id": "c41e9bba", "company": "ZipRecruiter", "title": "Staff Software Engineer, ML", "gh_job_id": "5167480", "board": "ziprecruiter"},
    {"id": "64adeb7b", "company": "AssemblyAI", "title": "Senior Software Engineer, ML", "gh_job_id": "4664764005", "board": "assemblyai"},
    {"id": "6dd3e16a", "company": "ClickHouse", "title": "Senior Full Stack Software Engineer - ClickPipes", "gh_job_id": "5777061004", "board": "clickhouse"},
    {"id": "89592306", "company": "ClickHouse", "title": "Senior Software Engineer - Cloud Infrastructure", "gh_job_id": "5819678004", "board": "clickhouse"},
    {"id": "9985b2d4", "company": "ClickHouse", "title": "Senior Software Engineer (TypeScript/Backend)", "gh_job_id": "5802760004", "board": "clickhouse"},
    {"id": "d511f3c6", "company": "Chainguard", "title": "Staff Software Engineer (Sustaining Automation)", "gh_job_id": "4661458006", "board": "chainguard"},
    {"id": "51724ada", "company": "Anthropic", "title": "Senior/Staff+ Software Engineer, Autonomous Agents", "gh_job_id": "5065894008", "board": "anthropic"},
    {"id": "bb5fe21a", "company": "Scale AI", "title": "Senior Software Engineer, Agentic Data Products", "gh_job_id": "4653827005", "board": "scaleai"},
    {"id": "3eaefaf5", "company": "Scale AI", "title": "Senior/Staff ML Engineer, General Agents", "gh_job_id": "4658162005", "board": "scaleai"},
    {"id": "2c36e94d", "company": "Scale AI", "title": "Staff ML Research Engineer, Agent Policy", "gh_job_id": "4625337005", "board": "scaleai"},
    {"id": "bb0d8256", "company": "PlanetScale", "title": "Software Engineer - Infrastructure", "gh_job_id": "4036240009", "board": "planetscale"},
    {"id": "402aaabb", "company": "Airtable", "title": "Software Engineer, Infrastructure (8+ YOE)", "gh_job_id": "8400388002", "board": "airtable"},
    {"id": "9c51b90e", "company": "ClickHouse", "title": "Full Stack Software Engineer - Billing", "gh_job_id": "5584382004", "board": "clickhouse"},
    {"id": "9cf11c13", "company": "ClickHouse", "title": "Full Stack Software Engineer - Control Plane", "gh_job_id": "5587664004", "board": "clickhouse"},
    {"id": "c00b53fb", "company": "Scale AI", "title": "Infrastructure Software Engineer, Enterprise GenAI", "gh_job_id": "4665557005", "board": "scaleai"},
    {"id": "194a92b8", "company": "Scale AI", "title": "ML Research Engineer, Agent Data Foundations", "gh_job_id": "4625345005", "board": "scaleai"},
]

def generate_cover_letter(company, title):
    letters = {
        "Remote People": "With 10 years of experience building production AI/ML systems including LLM-based applications, RAG pipelines, and autonomous agents, I am excited about the {} role at {}. I have deployed end-to-end ML solutions on cloud infrastructure using Python and FastAPI, and my background in data pipelines and vector databases aligns well with your focus on integrating AI across the organization to power borderless teams.".format(title, company),
        "WITHIN": "I am drawn to WITHIN's innovative approach to performance marketing. With 10 years of software engineering and deep experience in AI/ML systems, I bring expertise in building LLM-powered applications, RAG architectures, and autonomous agents that could help transform WITHIN's advertising intelligence capabilities. I have personally built and deployed production ML systems that achieved measurable business outcomes.",
        "Reddit": "As an engineer with 10 years of experience, I am excited about the {} role at Reddit. I have built scalable API systems, data pipelines, and ML-powered features that serve millions of users. My experience with distributed systems and cloud infrastructure would be a strong fit for Reddit's Ads API team.".format(title),
        "ZipRecruiter": "I am excited about the {} role at ZipRecruiter. With 10 years of software engineering experience including deep work in ML systems, I have built production recommendation engines, NLP pipelines, and scalable data infrastructure. I am passionate about using ML to improve job matching and hiring outcomes.".format(title),
        "AssemblyAI": "I am drawn to AssemblyAI's mission of making AI accessible through speech-to-text and audio intelligence APIs. With 10 years of engineering experience including ML model deployment, real-time inference pipelines, and cloud infrastructure, I would love to contribute to building AssemblyAI's next generation of AI-powered audio products.",
        "ClickHouse": "I am excited about the {} role at ClickHouse. With 10 years of experience building high-performance data systems, distributed infrastructure, and full-stack applications, I have deep expertise in TypeScript, cloud platforms, and scalable backend architectures that align well with ClickHouse's engineering needs.".format(title),
        "Chainguard": "I am passionate about software supply chain security and excited about the {} role at Chainguard. With 10 years of engineering experience including infrastructure automation, CI/CD systems, and cloud-native development, I would bring strong skills in building reliable, secure automation at scale.".format(title),
        "Anthropic": "I am deeply passionate about building safe, beneficial AI systems, and the {} role at Anthropic is my dream opportunity. I have spent years building autonomous agent systems, LLM-powered applications, and RAG pipelines. My hands-on experience with agent orchestration, tool use, and real-world AI deployment makes me a strong fit for Anthropic's autonomous agents team.".format(title),
        "Scale AI": "I am excited about the {} role at Scale AI. With 10 years of experience building ML infrastructure, data pipelines, and agent-based AI systems, I have worked extensively on training data quality, model evaluation, and scaling AI workloads. I am passionate about Scale AI's mission to accelerate AI development.".format(title),
        "PlanetScale": "I am drawn to PlanetScale's mission of making databases accessible and scalable for everyone. With 10 years of experience in infrastructure engineering, distributed systems, and database management, I bring deep expertise in building reliable, high-performance data systems at scale.",
        "Airtable": "I am excited about the {} role at Airtable. With over 10 years of infrastructure engineering experience, I have built scalable cloud systems, data pipelines, and platform services. My background in distributed systems and developer tooling aligns well with Airtable's engineering challenges.".format(title),
    }
    return letters.get(company, "With 10 years of software engineering experience including AI/ML systems, cloud infrastructure, and full-stack development, I am excited about the {} role at {}. I bring deep expertise in building production systems at scale.".format(title, company))

def answer_question(label, field_name, field_type, values, company):
    """Determine the best answer for a question based on its label and available values."""
    ll = label.lower()
    fn = field_name.lower() if field_name else ""

    # Standard fields handled by top-level params
    if fn in ("first_name", "last_name", "email", "phone", "resume", "resume_text", "cover_letter", "cover_letter_text"):
        return None  # handled separately

    # Text input questions
    if field_type in ("input_text", "textarea", "input_hidden"):
        if "linkedin" in ll:
            return APPLICANT["linkedin"]
        if "github" in ll or "portfolio" in ll or "website" in ll:
            return APPLICANT["github"]
        if "personal email" in ll:
            return APPLICANT["email"]
        if "salary" in ll or "compensation" in ll or "pay" in ll:
            return "$150,000 USD"
        if "location" in ll or "city" in ll or "based" in ll or "where" in ll:
            return APPLICANT["location"]
        if "year" in ll and ("experience" in ll or "ai" in ll or "ml" in ll):
            return "10"
        if "refer" in ll:
            return "No"
        if "how did you" in ll and ("find" in ll or "hear" in ll):
            return "Greenhouse job board"
        if "current" in ll and "company" in ll:
            return "Self-employed / Freelance"
        if "facebook" in ll or "instagram" in ll or "twitter" in ll or "social" in ll:
            return "N/A"
        if "connection" in ll or "client" in ll or "partner" in ll:
            return "N/A"
        if "cover" in ll:
            return generate_cover_letter(company, "this role")
        if "additional" in ll or "anything else" in ll:
            return generate_cover_letter(company, "this role")
        # Catch-all for unknown required text fields
        return None

    # Select/radio questions
    if field_type in ("multi_value_single_select", "multi_value_multi_select"):
        if not values:
            return None

        # Work authorization
        if "authorized" in ll or "authorization" in ll or "lawfully" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if "do not require" in vl or ("authorized" in vl and "do not" in vl):
                    return v["value"]
            for v in values:
                vl = v.get("label", "").lower()
                if "yes" in vl and "not" not in vl:
                    return v["value"]
            return values[0]["value"]

        # Sponsorship
        if "sponsor" in ll or "visa" in ll or "immigration" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if vl == "no" or "will not" in vl or "do not" in vl:
                    return v["value"]
            return values[0]["value"]

        # Remote/hybrid
        if "hybrid" in ll or "remote" in ll or "office" in ll or "in-person" in ll or "on-site" in ll:
            for v in values:
                if v.get("label", "").lower() == "yes":
                    return v["value"]
            return values[0]["value"]

        # Dog-friendly, AI comfort, etc - say yes
        if "dog" in ll or "comfortable" in ll or "ai usage" in ll:
            for v in values:
                if v.get("label", "").lower() == "yes":
                    return v["value"]
            return values[0]["value"]

        # Client connection - say no
        if "connection" in ll or "client" in ll:
            for v in values:
                if v.get("label", "").lower() == "no":
                    return v["value"]
            return values[0]["value"]

        # ML experience questions - pick the strongest positive answer
        if "ml" in ll or "machine learning" in ll or "ai" in ll or "deploy" in ll or "production" in ll or "pipeline" in ll or "measurable" in ll:
            # Look for the most positive/strongest answer
            for v in values:
                vl = v.get("label", "").lower()
                if "yes" in vl or "personally built" in vl or "owned" in vl or "measurable outcome" in vl or "distributed" in vl or "production-grade" in vl:
                    return v["value"]
            return values[-1]["value"]  # Often the strongest is last

        # "I agree" / privacy / consent
        if "agree" in ll or "privacy" in ll or "consent" in ll or "acknowledge" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if "agree" in vl or "yes" in vl or "i agree" in vl:
                    return v["value"]
            return values[0]["value"]

        # Worked at ML company
        if "worked at" in ll and ("company" in ll or "department" in ll):
            for v in values:
                if v.get("label", "").lower() == "yes":
                    return v["value"]
            return values[-1]["value"]

        # Gender/race/veteran/disability - decline
        if "gender" in ll or "race" in ll or "veteran" in ll or "disability" in ll or "ethnicity" in ll:
            for v in values:
                vl = v.get("label", "").lower()
                if "decline" in vl or "prefer not" in vl:
                    return v["value"]
            return values[-1]["value"]

        # Default: pick first value for required, None for optional
        return values[0]["value"]

    return None

def apply_greenhouse(job, applicant):
    board = job["board"]
    job_id = job["gh_job_id"]
    eu = job.get("eu", False)
    company = job["company"]
    title = job["title"]

    print("\n" + "=" * 60)
    print("APPLYING: {} - {}".format(company, title))
    print("Job ID: {} | Board: {}".format(job_id, board))
    print("=" * 60)

    # Step 1: Get questions from API
    if eu:
        api_base = "https://boards-api.eu.greenhouse.io/v1/boards"
    else:
        api_base = "https://boards-api.greenhouse.io/v1/boards"

    api_url = "{}/{}/jobs/{}".format(api_base, board, job_id)

    try:
        resp = requests.get(api_url, params={"questions": "true"}, timeout=15)
        if resp.status_code != 200:
            return False, "API returned {} fetching job questions".format(resp.status_code)
        job_data = resp.json()
        questions = job_data.get("questions", [])
    except Exception as e:
        return False, "Failed to fetch job: {}".format(e)

    print("  Found {} questions".format(len(questions)))

    # Step 2: Build form data
    form_data = {}
    cover_letter = generate_cover_letter(company, title)
    resume_file = None

    for q in questions:
        q_label = q.get("label", "")
        q_required = q.get("required", False)
        fields = q.get("fields", [])

        for field in fields:
            fname = field.get("name", "")
            ftype = field.get("type", "")
            fvalues = field.get("values", [])

            # Handle standard fields
            if fname == "first_name":
                form_data[fname] = applicant["first_name"]
                print("  {} = {}".format(fname, applicant["first_name"]))
                continue
            if fname == "last_name":
                form_data[fname] = applicant["last_name"]
                print("  {} = {}".format(fname, applicant["last_name"]))
                continue
            if fname == "email":
                form_data[fname] = applicant["email"]
                print("  {} = {}".format(fname, applicant["email"]))
                continue
            if fname == "phone":
                form_data[fname] = applicant["phone"]
                print("  {} = {}".format(fname, applicant["phone"]))
                continue
            if fname == "resume":
                resume_file = True  # handled separately in multipart
                print("  resume = (file upload)")
                continue
            if fname == "resume_text":
                form_data[fname] = ""  # empty, we upload the file
                continue
            if fname == "cover_letter":
                form_data[fname] = cover_letter
                print("  cover_letter = {}...".format(cover_letter[:60]))
                continue
            if fname == "cover_letter_text":
                form_data[fname] = cover_letter
                print("  cover_letter_text = {}...".format(cover_letter[:60]))
                continue

            # Handle custom questions
            answer = answer_question(q_label, fname, ftype, fvalues, company)

            if answer is not None:
                form_data[fname] = answer
                answer_str = str(answer)
                print("  {} = {}".format(fname, answer_str[:80]))
            elif q_required:
                # Required but we could not determine answer
                print("  [WARN] Required question unanswered: {} ({})".format(q_label[:60], fname))
                # Give a generic answer
                if ftype in ("input_text", "textarea"):
                    form_data[fname] = "N/A"
                    print("    -> defaulting to N/A")

    # Step 3: Submit via POST
    submit_url = "{}/{}/jobs/{}/candidates".format(api_base, board, job_id)

    files = {}
    resume_path = applicant["resume_path"]
    if os.path.exists(resume_path):
        files["resume"] = ("matt_gates_resume_ai.docx", open(resume_path, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    else:
        print("  [WARN] Resume file not found: {}".format(resume_path))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    print("\n  Submitting to: {}".format(submit_url))
    print("  Form fields: {}".format(len(form_data)))

    try:
        resp = requests.post(submit_url, data=form_data, files=files, headers=headers, timeout=30)
        status = resp.status_code
        body = resp.text[:500]
        print("  Response: {} {}".format(status, body[:200]))

        if status in (200, 201):
            print("  >>> SUCCESS <<<")
            return True, "Submitted (HTTP {})".format(status)
        elif status == 400:
            print("  >>> FAILED (400 Bad Request) <<<")
            return False, "HTTP 400: {}".format(body)
        elif status == 422:
            print("  >>> FAILED (422 Unprocessable) <<<")
            return False, "HTTP 422: {}".format(body)
        else:
            print("  >>> FAILED ({}) <<<".format(status))
            return False, "HTTP {}: {}".format(status, body)
    except Exception as e:
        print("  >>> ERROR: {} <<<".format(e))
        return False, str(e)
    finally:
        if "resume" in files:
            files["resume"][1].close()

def update_db(job_id, status):
    try:
        db_path = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        conn.close()
        print("  DB: {} -> {}".format(job_id, status))
    except Exception as e:
        print("  DB error: {}".format(e))

# MAIN
results = []
for job in JOBS:
    success, msg = apply_greenhouse(job, APPLICANT)
    results.append({"job": job, "success": success, "msg": msg})

    # Update DB
    if success:
        update_db(job["id"], "applied")
    else:
        update_db(job["id"], "apply_failed")

    # Brief pause between applications
    time.sleep(1)

# Summary
print("\n\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)
succeeded = [r for r in results if r["success"]]
failed = [r for r in results if not r["success"]]
print("Succeeded: {} / {}".format(len(succeeded), len(results)))
print("Failed: {} / {}".format(len(failed), len(results)))

if succeeded:
    print("\nSUCCESSFUL:")
    for r in succeeded:
        print("  [OK] {} - {}".format(r["job"]["company"], r["job"]["title"]))

if failed:
    print("\nFAILED:")
    for r in failed:
        print("  [FAIL] {} - {}: {}".format(r["job"]["company"], r["job"]["title"], r["msg"][:100]))

# Write results file
results_path = r"J:\job-hunter-mcp\swarm_greenhouse_results.md"
with open(results_path, "w", encoding="utf-8") as f:
    f.write("# Greenhouse Application Results\n\n")
    f.write("Date: 2026-03-20\n\n")
    f.write("## Summary\n")
    f.write("- Total: {}\n".format(len(results)))
    f.write("- Succeeded: {}\n".format(len(succeeded)))
    f.write("- Failed: {}\n\n".format(len(failed)))

    f.write("## Successful Applications\n")
    for r in succeeded:
        f.write("- {} - {} (id={})\n".format(r["job"]["company"], r["job"]["title"], r["job"]["id"]))

    f.write("\n## Failed Applications\n")
    for r in failed:
        f.write("- {} - {} (id={})\n".format(r["job"]["company"], r["job"]["title"], r["job"]["id"]))
        f.write("  - Error: {}\n".format(r["msg"][:200]))

print("\nResults written to: {}".format(results_path))
