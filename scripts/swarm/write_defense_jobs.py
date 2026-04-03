#!/usr/bin/env python3
"""Write defense contractor jobs to JSON using real scraped URLs."""
import sys
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

jobs = []

# ============================================================
# L3HARRIS JOBS (Radancy, company ID 4832)
# Scraped page 1 from: https://careers.l3harris.com/search-jobs/software%20engineer/4832/1
# Note: Radancy SSR returns unfiltered results - these are all real L3Harris jobs
# ============================================================
l3harris_raw = [
    ("CNC Optical Technician", "Manufacturing", "Toronto, Ontario", "/en/job/toronto/cnc-optical-technician/4832/93390578208"),
    ("Specialist, Technical Training (Maintenance Trainer)", "Engineering, Services", "Rochester, NY", "/en/job/rochester/specialist-technical-training-maintenance-trainer/4832/93200628736"),
    ("Senior Specialist, Trade Compliance", "Legal", "Multiple Locations", "/en/job/palm-bay/senior-specialist-trade-compliance/4832/93269697840"),
    ("Engineering Technician D", "Engineering, Services", "Palm Bay, Brevard, FL", "/en/job/palm-bay/engineering-technician-d/4832/93191370800"),
    ("CNC Optical Technician (Afternoon Shift)", "Manufacturing", "Toronto, Ontario", "/en/job/toronto/cnc-optical-technician-afternoon-shift/4832/93191370768"),
    ("Senior Specialist, Contracts", "Contracts", "Carlstadt, NJ", "/en/job/carlstadt/senior-specialist-contracts/4832/92967558384"),
    ("Principal, Legal Compliance (Ethics & Compliance Officer)", "Legal", "Multiple Locations", "/en/job/melbourne/principal-legal-compliance-ethics-and-compliance-officer/4832/92881375072"),
    ("Global Trade Technical Senior Specialist", "Legal", "Multiple Locations", "/en/job/anaheim/global-trade-technical-senior-specialist/4832/92609468480"),
    ("Associate, Manufacturing Engineer (San Diego, CA)", "Manufacturing", "San Diego, CA", "/en/job/san-diego/associate-manufacturing-engineer-san-diego-ca/4832/92590609104"),
    ("Lead, Supply Chain Management (Demand Planner)", "Supply Chain", "Anaheim, CA", "/en/job/anaheim/lead-supply-chain-management-demand-planner/4832/92667961648"),
    ("Director, Software Engineering", "Engineering", "Multiple Locations", "/en/job/mason/director-software-engineering/4832/93118163904"),
    ("Manager, Manufacturing Engineer", "Manufacturing", "Alpharetta, GA", "/en/job/alpharetta/manager-manufacturing-engineer/4832/92729074176"),
    ("Divisional Controller", "Finance", "Mirabel, Quebec", "/en/job/mirabel/divisional-controller/4832/92707399120"),
    ("Principal, Supply Chain Program Management", "Supply Chain", "Malabar, FL", "/en/job/malabar/principal-supply-chain-program-management/4832/92590608480"),
    ("Principal, Supply Chain Program Management", "Supply Chain", "Palm Bay, Brevard, FL", "/en/job/palm-bay/principal-supply-chain-program-management/4832/92729074064"),
    ("Manager, Subcontracts", "Contracts/Supply Chain", "Malabar, FL", "/en/job/malabar/manager-subcontracts/4832/92590608544"),
    ("Assoc, Manufacturing Engineering (Orlando, FL)", "Manufacturing", "Orlando, FL", "/en/job/orlando/assoc-manufacturing-engineering-orlando-fl/4832/92729074128"),
    ("Lead, Supply Chain Program Manager 1", "Supply Chain", "Hanover, MD", "/en/job/hanover/lead-supply-chain-program-manager-1/4832/92570820048"),
    ("Specialist, Materials Program Management - Supply", "Supply Chain", "Camden, AR", "/en/job/camden/specialist-materials-program-management-supply/4832/92629554112"),
    ("Machinist - 2nd Shift", "Manufacturing", "Orange, VA", "/en/job/orange/machinist-2nd-shift/4832/92417290848"),
    ("Machinist", "Manufacturing", "Orange, VA", "/en/job/orange/machinist/4832/92417290832"),
    ("Sr. Specialist, Embedded Software Developer", "Engineering", "Waterdown, Ontario", "/en/job/waterdown/sr-specialist-embedded-software-developer/4832/92590609408"),
    ("Specialist, Quality Engineer", "Quality & Operational Excellence", "Huntsville, AL", "/en/job/huntsville/specialist-quality-engineer/4832/92417290896"),
    ("Senior Specialist, Software Engineering", "Engineering", "Anaheim, CA", "/en/job/anaheim/senior-specialist-software-engineering/4832/92421471760"),
    ("Senior Manager, Supply Chain Management (Onsite - Fort Wayne IN)", "Supply Chain", "Multiple Locations", "/en/job/fort-wayne/senior-manager-supply-chain-management-onsite-fort-wayne-in/4832/92315570288"),
]

for title, category, loc, path in l3harris_raw:
    jobs.append({
        "source": "l3harris",
        "title": title,
        "location": loc,
        "category": category,
        "url": "https://careers.l3harris.com" + path
    })

# ============================================================
# LOCKHEED MARTIN JOBS (Radancy, company ID 694)
# Scraped page 1 from: https://www.lockheedmartinjobs.com/search-jobs/software%20engineer/694/1
# Note: Radancy SSR returns unfiltered results - these are real Lockheed jobs
# ============================================================
lockheed_raw = [
    ("Navigation Engineer", "Engineering", "Marietta, Georgia", "/job/marietta/navigation-engineer/694/93491291184"),
    ("Defensive Systems Engineer - Staff", "Engineering", "Marietta, Georgia", "/job/marietta/defensive-systems-engineer-staff/694/93491288704"),
    ("Executive Administrative Assistant", "Administration", "Multiple Locations", "/job/liverpool/executive-administrative-assistant/694/93233140256"),
    ("We're hiring! Radar, EW and Sensors Engineering Opportunities", "Engineering", "Multiple Locations", "/job/king-of-prussia/we-re-hiring-radar-ew-and-sensors-engineering-opportunities/694/92026937936"),
    ("Cyber Systems Security Engineer Staff", "Engineering/Cybersecurity", "Fort Worth, Texas", "/job/fort-worth/cyber-systems-security-engineer-staff/694/93491283936"),
    ("Inventory/Material Handler, F-35- Level 3", "Operations", "Edwards Air Force Base, California", "/job/edwards-air-force-base/inventory-material-handler-f-35-level-3/694/93491283680"),
    ("Inventory/Material Handler, F-35- Level 3", "Operations", "Edwards Air Force Base, California", "/job/edwards-air-force-base/inventory-material-handler-f-35-level-3/694/93491283664"),
    ("Electronics Engineer III, Missile Avionics, Secret Clearance", "Engineering", "Multiple Locations", "/job/littleton/electronics-engineer-iii-missile-avionics-secret-clearance/694/93491283568"),
    ("Electronics Engineering Manager, Avionics", "Engineering", "Multiple Locations", "/job/littleton/electronics-engineering-manager-avionics/694/93491283472"),
    ("Cyber-AI Engineering Aide", "Engineering/AI", "Fort Worth, Texas", "/job/fort-worth/cyber-ai-engineering-aide/694/93491283440"),
    ("Electronics & Optical Coms Senior Manager", "Engineering", "Multiple Locations", "/job/louisville/electronics-and-optical-coms-senior-manager/694/93491283360"),
    ("Optical Sensor Components Senior Manager", "Engineering", "Multiple Locations", "/job/louisville/optical-sensor-components-senior-manager/694/93491283328"),
    ("Global Supply Chain Business Operations Sr. Manager / Lvl 6 / FL or TX", "Supply Chain", "Multiple Locations", "/job/grand-prairie/global-supply-chain-business-operations-sr-manager-lvl-6-fl-or-tx/694/93491283104"),
    ("Project Engineer IV", "Engineering", "Cape Canaveral, Florida", "/job/cape-canaveral/project-engineer-iv/694/93491283072"),
    ("Performance Management Team (PMT) Analyst / Administrative Support", "Administration", "Camden, Arkansas", "/job/camden/performance-management-team-pmt-analyst-administrative-support/694/93461463200"),
    ("Integrated Program Planner - Level 4", "Program Management", "Littleton, Colorado", "/job/littleton/integrated-program-planner-level-4/694/93491282912"),
    ("Manufacturing Engineer-Lufkin, TX", "Manufacturing", "Lufkin, Texas", "/job/lufkin/manufacturing-engineer-lufkin-tx/694/90758549248"),
    ("Manufacturing Engineer", "Manufacturing", "Camden, Arkansas", "/job/camden/manufacturing-engineer/694/89835340544"),
    ("Sustainment Engineer Associate - SEAD", "Engineering", "Multiple Locations", "/job/hurlburt-field/sustainment-engineer-associate-sead/694/93392603728"),
    ("Flight Simulation Systems Engineer Senior", "Engineering", "Hurlburt Field, Florida", "/job/hurlburt-field/flight-simulation-systems-engineer-senior/694/91631943504"),
    ("Software Engineer Senior", "Engineering/Software", "Hurlburt Field, Florida", "/job/hurlburt-field/software-engineer-senior/694/91631942832"),
    ("Software Engineer", "Engineering/Software", "Hurlburt Field, Florida", "/job/hurlburt-field/software-engineer/694/91631942608"),
    ("Network Engineer", "Engineering/Network", "Hurlburt Field, Florida", "/job/hurlburt-field/network-engineer/694/91565244800"),
    ("Field Engineer", "Engineering", "Moody Air Force Base, Georgia", "/job/moody-air-force-base/field-engineer/694/92356228032"),
    ("Elec Maint Tech II - Hurlburt Field", "Maintenance", "Hurlburt Field, Florida", "/job/hurlburt-field/elec-maint-tech-ii-hurlburt-field/694/92643162784"),
]

for title, category, loc, path in lockheed_raw:
    jobs.append({
        "source": "lockheed",
        "title": title,
        "location": loc,
        "category": category,
        "url": "https://www.lockheedmartinjobs.com" + path
    })

# ============================================================
# MITRE JOBS (Phenom/Workday via careers.mitre.org)
# Scraped 3 keyword searches: software engineer, cybersecurity engineer, AI engineer
# URLs are real Workday apply links from careers.mitre.org
# ============================================================
mitre_raw = [
    # Software Engineer search (25 results)
    ("Senior Software Engineer", "Software Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Senior-Software-Engineer_R116302-1/apply"),
    ("Senior Embedded Software Engineer", "Software Engineering/Embedded", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Senior-Embedded-Software-Engineer_R116321-1/apply"),
    ("Model-Based Software Systems Engineer", "Software Engineering/Systems", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Model-Based-Software-Systems-Engineer_R115762-2/apply"),
    ("Lead Agentic Software Engineer", "Software Engineering/AI", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Lead-Agentic-Software-Engineer_R116301-1/apply"),
    ("Software Systems Engineering Intern--Omaha, NE", "Software Engineering/Intern", "Bellevue, Nebraska", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bellevue-NE/Software-Systems-Engineering-Intern--Omaha--NE_R115929/apply"),
    ("Software Engineering Intern - Orlando, Fl", "Software Engineering/Intern", "Orlando, Florida", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Orlando-FL/Software-Engineering-Intern---Orlando--Fl_R115933/apply"),
    ("Entry Level - Associate Software Developer", "Software Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Entry-Level---Associate-Software-Developer_R115842-1/apply"),
    ("Internships in Computer Science or Software Engineering", "Software Engineering/Intern", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Internships-in-Computer-Science-or-Software-Engineering_R115479/apply"),
    ("Entry Level - Software Engineering or Computer Science", "Software Engineering", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Entry-Level---Software-Engineering-or-Computer-Science_R115689-1/apply"),
    ("Software Developer Intern--Colorado Springs, CO and Tampa, FL locations", "Software Engineering/Intern", "Colorado Springs, Colorado", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Colorado-Springs-CO/Software-Developer-Intern--Colorado-Springs--CO-and-Tampa--FL-locations_R115845/apply"),
    ("Systems Engineer", "Systems Engineering", "Quantico, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Quantico-VA/Systems-Engineer_R116057-1/apply"),
    ("Communications Engineer", "Communications Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Communications-Engineer_R116231-2/apply"),
    ("Communications Engineer", "Communications Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Communications-Engineer_R116225-2/apply"),
    ("Systems Engineer", "Systems Engineering", "Quantico, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Quantico-VA/Systems-Engineer_R116044-1/apply"),
    ("Optical Engineer", "Engineering/Optics", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Optical-Engineer_R116190-1/apply"),
    ("Communications Engineer", "Communications Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Communications-Engineer_R116237-2/apply"),
    ("Lead Network Engineer", "Network Engineering", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Lead-Network-Engineer_R115992-1/apply"),
    ("AEHF Communications Engineer", "Communications Engineering/Satellite", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/AEHF-Communications-Engineer_R116193-1/apply"),
    ("Senior Reliability Engineer", "Engineering/Reliability", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Senior-Reliability-Engineer_R116243-1/apply"),
    ("Nuclear Operations Engineer", "Engineering/Nuclear", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Nuclear-Operations-Engineer_R116218-1/apply"),
    ("Data Solution Engineer", "Data Engineering", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Data-Solution-Engineer_R116275-1/apply"),
    ("Intermediate Systems Engineer", "Systems Engineering", "Huntsville, Alabama", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Huntsville-AL/Intermediate-Systems-Engineer_R116241-1/apply"),
    ("Senior Cybersecurity Engineer", "Cybersecurity Engineering", "Fort Meade - Annapolis Junction, Maryland", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Fort-Meade---Annapolis-Junction-MD/Senior-Cybersecurity-Engineer_R116312-1/apply"),
    ("AEHF Communications Engineer", "Communications Engineering/Satellite", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/AEHF-Communications-Engineer_R116199-1/apply"),
    ("Senior Radar Engineer", "Engineering/Radar", "Huntsville, Alabama", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Huntsville-AL/Senior-Radar-Engineer_R116236-1/apply"),
    # Cybersecurity Engineer search (unique ones not already in sw eng search)
    ("Applied Cybersecurity Engineer (Intelligence Center)", "Cybersecurity Engineering", "Chantilly, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Chantilly-VA/Applied-Cybersecurity-Engineer--Intelligence-Center-_R116224-2/apply"),
    ("Internships in Cybersecurity and Information Security", "Cybersecurity/Intern", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Internships-in-Cybersecurity-and-Information-Security_R115475/apply"),
    ("Lead Cyber Security Engineer", "Cybersecurity Engineering", "Huntsville, Alabama", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Huntsville-AL/Lead-Cyber-Security-Engineer_R116241-2/apply"),
    ("Lead Systems Engineer", "Systems Engineering", "Bedford, Massachusetts", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Bedford-MA/Lead-Systems-Engineer_R116260-1/apply"),
    ("Associate Systems Engineer", "Systems Engineering", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Associate-Systems-Engineer_R115862-1/apply"),
    ("Lead Cryptography Engineer", "Cryptography/Cybersecurity", "El Segundo, California", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/El-Segundo-CA/Lead-Cryptography-Engineer_R116208-1/apply"),
    ("Lead Cryptographic Cyber Security Engineer", "Cybersecurity/Cryptography", "San Diego, California", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/San-Diego-CA/Lead-Cryptographic-Cyber-Security-Engineer_R116288-1/apply"),
    ("Zero Trust Cyber Security Engineer", "Cybersecurity Engineering", "San Antonio, Texas", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/San-Antonio-TX/Zero-Trust-Cyber-Security-Engineer_R116297-1/apply"),
    ("PACAF Senior Systems Engineer", "Systems Engineering", "Honolulu, Hawaii", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Honolulu-HI/PACAF-Senior-Systems-Engineer_R116214-1/apply"),
    # AI Engineer search (unique ones not already captured)
    ("Senior AI Research Engineer", "AI Engineering/Research", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Senior-AI-Research-Engineer_R116307-1/apply"),
    ("Intermediate AI Research Engineer", "AI Engineering/Research", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Intermediate-AI-Research-Engineer_R116308-1/apply"),
    ("Intermediate AI Research Engineer", "AI Engineering/Research", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Intermediate-AI-Research-Engineer_R116309-2/apply"),
    ("AI SME", "AI/Policy", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/AI-SME_R116285-1/apply"),
    ("AI Program Manager", "AI/Program Management", "Gaithersburg, Maryland", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Gaithersburg-MD/AI-Program-Manager_R116276-1/apply"),
    ("AI Policy SME", "AI/Policy", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/AI-Policy-SME_R116286-1/apply"),
    ("AI, Autonomy & Data Director", "AI/Leadership", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/AI--Autonomy---Data-Director_R116218-2/apply"),
    ("Lead Autonomous Systems Engineer", "AI/Autonomous Systems", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Lead-Autonomous-Systems-Engineer_R116295-1/apply"),
    ("Senior Autonomous Systems Engineer", "AI/Autonomous Systems", "Huntsville, Alabama", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Huntsville-AL/Senior-Autonomous-Systems-Engineer_R116296-1/apply"),
    ("Lead Autonomous Systems Engineer", "AI/Autonomous Systems", "Huntsville, Alabama", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/Huntsville-AL/Lead-Autonomous-Systems-Engineer_R116294-1/apply"),
    ("Entry Level - Systems/Mechanical/Aerospace Engineer", "Systems Engineering", "McLean, Virginia", "https://mitre.wd5.myworkdayjobs.com/MITRE/job/McLean-VA/Entry-Level---Systems-Mechanical-Aerospace-Engineer_R115690-1/apply"),
]

# Deduplicate MITRE by URL
seen_urls = set()
for title, category, loc, url in mitre_raw:
    if url not in seen_urls:
        seen_urls.add(url)
        jobs.append({
            "source": "mitre",
            "title": title,
            "location": loc,
            "category": category,
            "url": url
        })

data = {
    "scraped_at": "2026-04-02",
    "jobs": jobs
}

out_path = r'J:\job-hunter-mcp\scripts\swarm\defense_jobs.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

l3h = sum(1 for j in jobs if j['source'] == 'l3harris')
lkd = sum(1 for j in jobs if j['source'] == 'lockheed')
mit = sum(1 for j in jobs if j['source'] == 'mitre')
print(f"Written {len(jobs)} jobs to {out_path}")
print(f"  L3Harris: {l3h}")
print(f"  Lockheed: {lkd}")
print(f"  MITRE: {mit}")
