#!/usr/bin/env python3
"""Discover NEW Lever and Ashby job boards for remote-friendly tech companies."""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error

DB_PATH = r"C:\Users\Matt\.job-hunter-mcp\jobs.db"

# --- Companies to skip (already known) ---
KNOWN_LEVER = {s.lower() for s in [
    "Atmosera", "Blue Light Consulting", "Collectly", "Danti", "Extreme Networks",
    "Glass Health", "Jobgether", "Mutt Data", "Plaid", "Spear AI", "SymmetrySystems",
    "anyscale", "atmosera", "brillio-2", "britecore", "jumpcloud", "laminarprojects",
    "latitudeinc", "metabase", "mistral", "neon", "nextech", "plaid", "shieldai",
    "smart-working-solutions", "tinybird", "unknown", "veeva", "voltus", "zerotier",
    # Also skip boards we already found
    "coupa", "wealthfront", "color", "logrocket", "Coda",
]}

KNOWN_ASHBY = {s.lower() for s in [
    "Anyscale", "Baseten", "Beam", "Coder", "Cohere", "Cursor", "Deepgram",
    "ElevenLabs", "Harvey AI", "LangChain", "LiveKit", "Mem", "OpenAI",
    "Perplexity AI", "Pinecone", "Poolside", "Railway", "Reka", "Render",
    "Replit", "Sentry", "Supabase",
]}

# --- New companies to probe ---
# Lever: use many slug variations since companies use inconsistent slugs
LEVER_COMPANIES = [
    # Original list
    "airtable", "auth0", "benchling", "brex", "carta", "chainalysis", "cockroachlabs",
    "contentful", "databricks", "datadog", "dbt-labs", "deel", "discord", "docker",
    "doppler", "elastic", "envoy", "etsy", "eventbrite", "fastly", "fivetran", "fly",
    "fullstory", "getdbt", "gusto", "hashicorp", "hubspot", "intercom", "klaviyo",
    "loom", "lyft", "mux", "netlify", "notion", "okta", "onepassword", "pagerduty",
    "palantir", "postman", "procore", "retool", "rippling", "segment", "snyk",
    "sourcegraph", "splunk", "square", "stripe", "supabase", "temporal", "terraform",
    "tigera", "twilio", "webflow", "wiz", "zapier", "zoom", "zscaler", "1password",
    "asana", "calendly", "canva", "circleci", "cloudflare", "confluent", "coupang",
    "crowdstrike", "duolingo", "figma", "gitlab", "grafana", "grammarly", "instacart",
    "lucid", "mapbox", "marqeta", "miro", "mongodb", "navan", "newrelic", "pendo",
    "productboard", "rudderstack", "samsara", "snowflake", "sonarqube", "toast",
    "workato", "yugabyte", "vercel", "anthropic",
    # Extended: known Lever users + slug variations
    "GoCardless", "gocardless", "Airwallex", "airwallex", "DataStax", "datastax",
    "WeTransfer", "wetransfer", "Ada", "ada-support", "Wolt", "wolt",
    "Remote", "remote-com", "Oyster", "oyster", "oysterhr",
    "deel-careers", "Drata", "drata", "Vanta", "vanta",
    "LaunchDarkly", "launchdarkly", "Harness", "harness", "Chronosphere", "chronosphere",
    "Kong", "kong", "Couchbase", "couchbase", "InfluxData", "influxdata",
    "Timescale", "timescale", "CockroachDB", "cockroachdb", "SingleStore", "singlestore",
    "Starburst", "starburst", "Hex", "hex", "Sigma", "sigma",
    "Lightdash", "lightdash", "Hasura", "hasura",
    "apollographql", "Airbyte", "airbyte", "Meltano", "meltano",
    "mParticle", "mparticle", "Amplitude", "amplitude", "Mixpanel", "mixpanel",
    "Heap", "heap", "PostHog", "posthog", "LogRocket",
    "GrafanaLabs", "grafanalabs", "grafana-labs",
    "datadog-careers", "elastic-co", "splunk-careers", "newrelic-inc", "Dynatrace", "dynatrace",
    "CircleCI", "Buildkite", "buildkite", "Codefresh", "codefresh",
    "harness-io", "RelationalAI", "relationalai", "wandb",
    "huggingface", "scaleai", "scale", "stabilityai", "stability",
    "jasper", "Writer", "writer", "grammarly-inc",
    "notion-so", "coda", "monday", "ClickUp", "clickup",
    "shortcut", "flyio", "fly-io", "render-co",
    "vercel-inc", "netlify-inc", "supabase-inc", "planetscale",
    "neon-inc", "Upstash", "upstash", "fauna", "faunadb",
    # More companies known to use Lever
    "GoFundMe", "gofundme", "Affirm", "affirm", "weave", "census", "descript",
    "materialize", "tailscale", "gitpod", "axiom-co",
    "toast-inc", "Lattice", "lattice", "Automox", "automox",
    "relativity", "lacework", "rapid7", "tanium", "forescout",
    "zscaler-careers", "arista", "freshworks", "newrelic-careers",
    "Hims", "hims", "sentry", "coinbase", "netflix",
    "twitch", "grab", "seatgeek", "spotinst",
    "Verkada", "verkada", "robinhood", "chime", "nerdwallet",
    "peloton", "upstart", "trueaccord", "checkout",
    # Additional tech companies
    "luminar", "niantic", "epic-games", "epicgames", "riot-games", "riotgames",
    "unity", "unity3d", "improbable", "roblox",
    "amd", "nvidia", "intel", "qualcomm",
    "blockfi", "blockchain", "kraken", "gemini", "opensea",
    "alchemy", "polygon", "arbitrum", "optimism",
    "sofi", "plaid-inc", "marqeta-inc", "brex-inc",
    "flexport", "shippo", "project44",
    "sentry-io", "bugsnag", "rollbar",
    "circleci-com", "travisci", "buildkite-com",
    "auth0-inc", "okta-inc", "onelogin",
    "datarobot", "domino-data", "weights-and-biases",
    "tecton", "feast", "tecton-ai",
    "pinecone", "pinecone-io", "weaviate",
    "langchain", "langchain-ai",
    "together", "togetherai", "together-compute",
    "fireworks", "fireworksai",
    "groq", "groq-inc", "cerebras", "cerebras-inc",
    "sambanova", "sambanova-systems",
    "modal-labs", "modal-com",
    "replicate", "replicate-inc",
    "hugging-face",
    "bentoml", "banana-dev", "baseten",
]

ASHBY_COMPANIES = [
    # Original list
    "ramp", "stripe", "vercel", "notion", "linear", "clerk", "resend", "neon",
    "planetscale", "turso", "drizzle", "prisma", "convex", "stytch", "propelauth",
    "trigger-dev", "inngest", "highlight-io", "airplane-dev", "retool", "mintlify",
    "cal-com", "dub", "plane-so", "hoppscotch", "twenty", "infisical", "formbricks",
    "documenso", "unkey", "langfuse", "helicone", "traceloop", "portkey",
    "weights-biases", "lancedb", "qdrant", "weaviate", "chroma", "milvus", "prefect",
    "dagster", "modal", "replicate", "together-ai", "fireworks-ai", "groq", "cerebras",
    "sambanova", "lepton-ai", "runpod", "lambda", "coreweave", "vast-ai", "salad-cloud",
    # Extended: various capitalization and slug forms
    "Ramp", "Stripe", "Vercel", "Notion", "Linear", "Clerk", "Resend", "Neon",
    "PlanetScale", "Turso", "Drizzle", "Prisma", "Convex", "Stytch",
    "Retool", "Mintlify", "Dub", "Infisical", "Langfuse", "Helicone",
    "Qdrant", "Weaviate", "Chroma", "Milvus", "Prefect", "Dagster", "Modal",
    "Replicate", "Together", "Fireworks", "Groq", "Cerebras", "SambaNova",
    "RunPod", "Lambda", "CoreWeave",
    # More companies that might use Ashby
    "Anthropic", "anthropic", "Scale", "ScaleAI", "scale-ai", "scaleai",
    "AssemblyAI", "assemblyai", "Stability", "stability-ai", "StabilityAI",
    "Midjourney", "midjourney", "Jasper", "jasper-ai", "Writer", "writer",
    "Airtable", "airtable", "Figma", "figma", "Miro", "miro",
    "Webflow", "webflow", "Canva", "canva", "Sourcegraph", "sourcegraph",
    "GitLab", "gitlab", "PostHog", "posthog", "Grafana", "grafana",
    "GrafanaLabs", "grafana-labs", "HashiCorp", "hashicorp", "Snyk", "snyk",
    "LaunchDarkly", "launchdarkly", "Vanta", "vanta", "Drata", "drata",
    "Axonius", "axonius", "Wiz", "wiz", "CrowdStrike", "crowdstrike",
    "SentinelOne", "sentinelone", "Datadog", "datadog",
    "Snowflake", "snowflake", "Databricks", "databricks",
    "dbt-labs", "dbtLabs", "Fivetran", "fivetran", "Airbyte", "airbyte",
    "Starburst", "starburst", "SingleStore", "singlestore",
    "CockroachLabs", "cockroachlabs", "Timescale", "timescale",
    "InfluxData", "influxdata", "Netlify", "netlify", "Fly", "flyio",
    "Upstash", "upstash", "Fauna", "fauna", "Hasura", "hasura",
    "Apollo", "apollographql", "apollo-graphql",
    "Loom", "loom", "Calendly", "calendly", "Rippling", "rippling",
    "Gusto", "gusto", "Deel", "deel", "Remote", "remote",
    "Lattice", "lattice", "BambooHR", "bamboohr",
    "Brex", "brex", "Plaid", "plaid",
    "Discord", "discord", "Twilio", "twilio",
    "Okta", "okta", "Auth0", "auth0",
    "Docker", "docker", "CircleCI", "circleci",
    "Temporal", "temporal", "Buildkite", "buildkite",
    "Tailscale", "tailscale", "Cloudflare", "cloudflare",
    "Fastly", "fastly", "Fly", "fly",
    "Zscaler", "zscaler", "Palo-Alto-Networks", "paloaltonetworks",
    "HuggingFace", "huggingface", "hugging-face",
    "Weights-and-Biases", "wandb",
    "Tecton", "tecton", "BentoML", "bentoml",
    "LangChain", "langchain",
    "Pinecone", "pinecone",
    "Cohere", "cohere",
    "Mosaic", "mosaicml", "Databricks", "databricks",
]

# Filter out already-known (case-insensitive)
LEVER_COMPANIES = list(dict.fromkeys(c for c in LEVER_COMPANIES if c.lower() not in KNOWN_LEVER))
ASHBY_COMPANIES = list(dict.fromkeys(c for c in ASHBY_COMPANIES if c.lower() not in KNOWN_ASHBY))

# Deduplicate case-insensitively
seen_lever = set()
deduped_lever = []
for c in LEVER_COMPANIES:
    if c.lower() not in seen_lever:
        seen_lever.add(c.lower())
        deduped_lever.append(c)
LEVER_COMPANIES = deduped_lever

seen_ashby = set()
deduped_ashby = []
for c in ASHBY_COMPANIES:
    if c.lower() not in seen_ashby:
        seen_ashby.add(c.lower())
        deduped_ashby.append(c)
ASHBY_COMPANIES = deduped_ashby


def make_id(source: str, source_id: str) -> str:
    return hashlib.sha256(f"{source}:{source_id}".encode()).hexdigest()[:16]


def probe_lever(company: str) -> list[dict] | None:
    """Return list of job dicts if board exists, else None."""
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='replace'))
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    return None


def probe_ashby(company: str) -> list[dict] | None:
    """Return list of job dicts if board exists, else None.
    Uses the updated GraphQL query with jobPostings field."""
    url = "https://jobs.ashbyhq.com/api/non-user-graphql"
    payload = json.dumps({
        "variables": {"organizationHostedJobsPageName": company},
        "query": (
            "{ jobBoard: jobBoardWithTeams("
            'organizationHostedJobsPageName: "' + company.replace('"', '\\"') + '"'
            ") { jobPostings { id title locationName employmentType } } }"
        ),
    }).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode('utf-8', errors='replace'))
            if raw.get("errors"):
                return None
            board = raw.get("data", {}).get("jobBoard")
            if not board:
                return None
            postings = board.get("jobPostings") or []
            return postings if postings else None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"    [RATE LIMITED on {company}, waiting 30s...]")
            time.sleep(30)
            # Retry once
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = json.loads(resp.read().decode('utf-8', errors='replace'))
                    if raw.get("errors"):
                        return None
                    board = raw.get("data", {}).get("jobBoard")
                    if not board:
                        return None
                    postings = board.get("jobPostings") or []
                    return postings if postings else None
            except Exception:
                return None
        return None
    except Exception:
        return None


def insert_jobs(conn: sqlite3.Connection, jobs_to_insert: list[dict]) -> int:
    """Insert jobs, return count of newly inserted."""
    inserted = 0
    cur = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for j in jobs_to_insert:
        jid = make_id(j["source"], j["source_id"])
        try:
            cur.execute(
                """INSERT OR IGNORE INTO jobs
                   (id, source, source_id, title, company, url, location,
                    salary, job_type, category, description, tags,
                    date_posted, date_found, fit_score, fit_reason,
                    status, notes, cover_letter, applied_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    jid, j["source"], j["source_id"], j["title"], j["company"],
                    j["url"], j.get("location", ""), j.get("salary", ""),
                    j.get("job_type", ""), j.get("category", ""),
                    "", "",  # description, tags
                    j.get("date_posted", ""), now,
                    0.0, "", "new", "", "", "",
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


def main():
    conn = sqlite3.connect(DB_PATH)

    total_new = 0
    lever_boards = []
    ashby_boards = []

    # --- Lever ---
    print(f"=== Probing {len(LEVER_COMPANIES)} Lever boards ===")
    for i, company in enumerate(LEVER_COMPANIES):
        jobs = probe_lever(company)
        status = f"[{i+1}/{len(LEVER_COMPANIES)}] Lever/{company}"
        if jobs is None:
            print(f"  {status}: no board")
            continue

        total_jobs = len(jobs)
        remote_jobs = [
            j for j in jobs
            if "remote" in (j.get("categories", {}).get("location", "") or "").lower()
            or "remote" in (j.get("text", "") or "").lower()
        ]

        to_insert = []
        for j in jobs:
            loc = j.get("categories", {}).get("location", "") or ""
            to_insert.append({
                "source": "lever",
                "source_id": j.get("id", ""),
                "title": j.get("text", "Unknown"),
                "company": company,
                "url": j.get("hostedUrl", f"https://jobs.lever.co/{company}/{j.get('id','')}"),
                "location": loc,
                "job_type": j.get("categories", {}).get("commitment", ""),
                "category": j.get("categories", {}).get("team", ""),
                "date_posted": "",
            })

        inserted = insert_jobs(conn, to_insert)
        total_new += inserted
        lever_boards.append((company, total_jobs, len(remote_jobs), inserted))
        print(f"  {status}: {total_jobs} jobs ({len(remote_jobs)} remote-tagged), {inserted} NEW inserted")
        time.sleep(0.3)

    # --- Ashby ---
    print(f"\n=== Probing {len(ASHBY_COMPANIES)} Ashby boards ===")
    for i, company in enumerate(ASHBY_COMPANIES):
        jobs = probe_ashby(company)
        status = f"[{i+1}/{len(ASHBY_COMPANIES)}] Ashby/{company}"
        if jobs is None:
            print(f"  {status}: no board")
            continue

        total_jobs = len(jobs)
        remote_jobs = [
            j for j in jobs
            if "remote" in (j.get("locationName", "") or "").lower()
            or "remote" in (j.get("title", "") or "").lower()
        ]

        to_insert = []
        for j in jobs:
            loc = j.get("locationName", "") or ""
            to_insert.append({
                "source": "ashby",
                "source_id": j.get("id", ""),
                "title": j.get("title", "Unknown"),
                "company": company,
                "url": f"https://jobs.ashbyhq.com/{company}/{j.get('id','')}",
                "location": loc,
                "job_type": j.get("employmentType", ""),
                "category": "",
                "date_posted": "",
            })

        inserted = insert_jobs(conn, to_insert)
        total_new += inserted
        ashby_boards.append((company, total_jobs, len(remote_jobs), inserted))
        print(f"  {status}: {total_jobs} jobs ({len(remote_jobs)} remote-tagged), {inserted} NEW inserted")
        time.sleep(1.0)  # Slower for Ashby to avoid rate limiting

    # --- Summary ---
    print("\n" + "=" * 60)
    print("DISCOVERY SUMMARY")
    print("=" * 60)

    if lever_boards:
        print(f"\nLever boards found: {len(lever_boards)}")
        for company, total, remote, new in sorted(lever_boards, key=lambda x: -x[1]):
            print(f"  {company:30s}  {total:4d} jobs  {remote:3d} remote  {new:4d} new")
    else:
        print("\nNo new Lever boards found.")

    if ashby_boards:
        print(f"\nAshby boards found: {len(ashby_boards)}")
        for company, total, remote, new in sorted(ashby_boards, key=lambda x: -x[1]):
            print(f"  {company:30s}  {total:4d} jobs  {remote:3d} remote  {new:4d} new")
    else:
        print("\nNo new Ashby boards found.")

    print(f"\nTOTAL NEW JOBS INSERTED: {total_new}")

    # Final DB count
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    print(f"Total jobs in DB now: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
