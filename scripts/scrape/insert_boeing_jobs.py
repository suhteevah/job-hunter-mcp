#!/usr/bin/env python3
import sys
import sqlite3
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\Users\Matt\.job-hunter-mcp\jobs.db'

# All scraped Boeing jobs: url|||title|||location|||date
RAW_JOBS = """
https://jobs.boeing.com/job/hazelwood/software-engineer/185/93432140416|||Software Engineer|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/bengaluru/lead-software-engineer/185/91325367744|||Lead Software Engineer|||Bengaluru, India|||04/01/2026
https://jobs.boeing.com/job/hazelwood/software-engineer/185/92668726048|||Software Engineer|||Hazelwood, Missouri|||03/11/2026
https://jobs.boeing.com/job/bengaluru/software-engineering-manager/185/93260705424|||Software Engineering Manager|||Bengaluru, India|||03/27/2026
https://jobs.boeing.com/job/hazelwood/senior-software-engineer/185/93432140432|||Senior Software Engineer|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/hazelwood/associate-software-engineer/185/93426352528|||Associate Software Engineer|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/el-segundo/devsecops-lead-software-engineer/185/93198198000|||DevSecOps Lead Software Engineer|||El Segundo, California|||03/25/2026
https://jobs.boeing.com/job/gdansk/associate-avionx-software-engineer/185/93426359456|||Associate AvionX Software Engineer|||Gdansk, Poland; and other locations|||03/31/2026
https://jobs.boeing.com/job/long-beach/software-engineer-embedded-embedded/185/91806301248|||Software Engineer-Embedded (Embedded)|||Long Beach, California|||04/01/2026
https://jobs.boeing.com/job/el-segundo/software-engineering-manager/185/93392300752|||Software Engineering Manager|||El Segundo, California|||03/30/2026
https://jobs.boeing.com/job/seoul/junior-senior-software-engineer/185/89859726880|||Junior/Senior Software Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/hazelwood/software-engineering-manager/185/92423505344|||Software Engineering Manager|||Hazelwood, Missouri|||03/27/2026
https://jobs.boeing.com/job/gdansk/intern-software-engineer/185/90651992896|||Intern Software Engineer|||Gdansk, Poland; and other locations|||03/26/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-senior-level/185/87605858384|||Software Engineer - Senior Level|||Annapolis Junction, Maryland|||02/06/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-senior-level/185/93247825520|||Software Engineer - Senior Level|||Annapolis Junction, Maryland|||03/27/2026
https://jobs.boeing.com/job/tukwila/senior-software-engineer-systems/185/92654945312|||Senior Software Engineer - Systems|||Tukwila, Washington|||03/27/2026
https://jobs.boeing.com/job/hazelwood/associate-software-engineer/185/92438390576|||Associate Software Engineer|||Hazelwood, Missouri|||03/05/2026
https://jobs.boeing.com/job/berkeley/senior-software-engineer-developer-virtual/185/93473505776|||Senior Software Engineer- Developer (Virtual)|||Berkeley, Missouri; and other locations|||04/01/2026
https://jobs.boeing.com/job/seoul/associate-experienced-embedded-software-engineer/185/91360195040|||Associate/Experienced Embedded Software Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/huntington-beach/associate-software-engineer-developer/185/93473508960|||Associate Software Engineer - Developer|||Huntington Beach, California|||04/01/2026
https://jobs.boeing.com/job/chantilly/senior-full-stack-software-engineer/185/90624053216|||Senior Full-Stack Software Engineer|||Chantilly, Virginia; and other locations|||03/23/2026
https://jobs.boeing.com/job/daytona-beach/senior-software-engineer/185/92386375632|||Senior Software Engineer|||Daytona Beach, Florida|||03/29/2026
https://jobs.boeing.com/job/berkeley/associate-software-engineer/185/91806312304|||Associate Software Engineer|||Berkeley, Missouri|||03/17/2026
https://jobs.boeing.com/job/brisbane/software-engineer/185/93139915936|||Software Engineer|||Brisbane, Australia|||03/24/2026
https://jobs.boeing.com/job/oklahoma-city/software-engineer-developer-experienced-and-senior/185/92091783056|||Software Engineer-Developer (Experienced and Senior)|||Oklahoma City, Oklahoma|||03/31/2026
https://jobs.boeing.com/job/saint-charles/experienced-embedded-software-engineer/185/89859722128|||Experienced Embedded Software Engineer|||Saint Charles, Missouri|||03/30/2026
https://jobs.boeing.com/job/richardson/experienced-software-engineer-devsecops/185/91877300192|||Experienced Software Engineer-DevSecOps|||Richardson, Texas|||03/19/2026
https://jobs.boeing.com/job/gdansk/experienced-java-software-engineer/185/92254087168|||Experienced Java Software Engineer|||Gdansk, Poland|||04/01/2026
https://jobs.boeing.com/job/gdansk/associate-avionx-software-engineer/185/93426350672|||Associate AvionX Software Engineer|||Gdansk, Poland|||03/31/2026
https://jobs.boeing.com/job/seal-beach/associate-software-engineer-vehicle-management-systems/185/92316588208|||Associate Software Engineer-Vehicle Management Systems|||Seal Beach, California|||03/31/2026
https://jobs.boeing.com/job/ridley-park/software-engineer-developer-associate-or-experienced/185/88574729792|||Software Engineer-Developer (Associate or Experienced)|||Ridley Park, Pennsylvania|||03/25/2026
https://jobs.boeing.com/job/hazelwood/lead-software-engineer-vehicle-management-systems/185/93432138480|||Lead Software Engineer-Vehicle Management Systems|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/seal-beach/experienced-software-engineer-test-and-verification/185/92170928848|||Experienced Software Engineer-Test & Verification|||Seal Beach, California|||03/31/2026
https://jobs.boeing.com/job/bengaluru/lead-software-engineer-embedded/185/93103735952|||Lead Software Engineer-Embedded|||Bengaluru, India|||03/23/2026
https://jobs.boeing.com/job/seoul/associate-experienced-embedded-software-engineer-linux/185/89859442560|||Associate/Experienced Embedded Software Engineer (Linux)|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/berkeley/software-engineer-developer-development/185/93426337920|||Software Engineer-Developer (Development)|||Berkeley, Missouri|||03/31/2026
https://jobs.boeing.com/job/herndon/experienced-senior-java-software-engineer-developer/185/93478815792|||Experienced/Senior Java Software Engineer - Developer|||Herndon, Virginia; and other locations|||04/01/2026
https://jobs.boeing.com/job/gdansk/experienced-avionx-software-engineer/185/93426359552|||Experienced AvionX Software Engineer|||Gdansk, Poland|||03/31/2026
https://jobs.boeing.com/job/daytona-beach/mid-level-software-engineer/185/92362910192|||Mid Level Software Engineer|||Daytona Beach, Florida|||03/29/2026
https://jobs.boeing.com/job/mesa/software-engineering-manager-vertical-lift/185/93009826064|||Software Engineering Manager, Vertical Lift|||Mesa, Arizona|||03/20/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-mid-level/185/87482198624|||Software Engineer - Mid Level|||Annapolis Junction, Maryland|||02/06/2026
https://jobs.boeing.com/job/hazelwood/lead-software-engineer-vehicle-management-systems-remote/185/93432138496|||Lead Software Engineer-Vehicle Management Systems (Remote)|||Hazelwood, Missouri; and other locations|||03/31/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-junior-mid-level/185/93236877440|||Software Engineer Junior/Mid-Level|||Annapolis Junction, Maryland|||03/26/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-junior-level/185/92727654400|||Software Engineer - Junior Level|||Annapolis Junction, Maryland|||03/13/2026
https://jobs.boeing.com/job/annapolis-junction/software-engineer-entry-level/185/92898780256|||Software Engineer - Entry Level|||Annapolis Junction, Maryland|||03/18/2026
https://jobs.boeing.com/job/annapolis-junction/senior-software-engineer-backend/185/93236877312|||Senior Software Engineer - Backend|||Annapolis Junction, Maryland|||03/26/2026
https://jobs.boeing.com/job/bengaluru/experienced-software-engineer-java-full-stack/185/93469395344|||Experienced Software Engineer - Java Full Stack|||Bengaluru, India|||04/01/2026
https://jobs.boeing.com/job/crawley/simulation-software-engineer-entry-level/185/91582989376|||Simulation Software Engineer (Entry level)|||Crawley, United Kingdom|||03/25/2026
https://jobs.boeing.com/job/bristol/software-engineer-experienced-or-senior-level/185/93190493696|||Software Engineer (Experienced or Senior Level)|||Bristol, United Kingdom; and other locations|||03/25/2026
https://jobs.boeing.com/job/oklahoma-city/mid-level-software-engineer-test-and-verification/185/93290680352|||Mid-Level Software Engineer (Test & Verification)|||Oklahoma City, Oklahoma|||03/27/2026
https://jobs.boeing.com/job/bengaluru/associate-software-engineer-full-stack-developer/185/91618391424|||Associate Software Engineer - Full Stack Developer|||Bengaluru, India|||04/01/2026
https://jobs.boeing.com/job/colorado-springs/software-engineer-c2bmc-associate-experienced-or-senior/185/92386398192|||Software Engineer - C2BMC (Associate, Experienced or Senior)|||Colorado Springs, Colorado; and other locations|||03/29/2026
https://jobs.boeing.com/job/annapolis-junction/senior-software-engineer-front-end/185/92849894272|||Senior Software Engineer - Front End|||Annapolis Junction, Maryland|||03/16/2026
https://jobs.boeing.com/job/annapolis-junction/senior-software-engineer-back-end/185/92849894240|||Senior Software Engineer - Back End|||Annapolis Junction, Maryland|||03/16/2026
https://jobs.boeing.com/job/berkeley/f-22-simulation-software-engineer-associate-experienced-and-senior/185/93392329616|||F-22 Simulation Software Engineer (Associate, Experienced, and Senior)|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/bengaluru/experienced-software-engineer-ai-application/185/93218712560|||Experienced Software Engineer - AI Application|||Bengaluru, India|||03/26/2026
https://jobs.boeing.com/job/chantilly/full-stack-software-engineer-associate-experienced/185/93014443072|||Full-Stack Software Engineer (Associate/Experienced)|||Chantilly, Virginia; and other locations|||03/20/2026
https://jobs.boeing.com/job/albuquerque/software-engineer-front-end-developer-experienced-senior/185/92399872048|||Software Engineer, Front End Developer (Experienced/Senior)|||Albuquerque, New Mexico|||03/25/2026
https://jobs.boeing.com/job/albuquerque/software-engineer-hardware-emulation-experienced-or-senior/185/92399872144|||Software Engineer, Hardware Emulation (Experienced or Senior)|||Albuquerque, New Mexico|||03/23/2026
https://jobs.boeing.com/job/albuquerque/software-engineer-database-developer-experienced-or-senior/185/92543107008|||Software Engineer, Database Developer (Experienced or Senior)|||Albuquerque, New Mexico|||03/25/2026
https://jobs.boeing.com/job/berkeley/software-engineer-systems-experienced-and-senior/185/93241569568|||Software Engineer - Systems (Experienced and Senior)|||Berkeley, Missouri|||03/26/2026
https://jobs.boeing.com/job/chantilly/ground-software-engineer-mid-career-millennium-space-systems/185/90184526704|||Ground Software Engineer (Mid Career) - Millennium Space Systems|||Chantilly, Virginia|||03/31/2026
https://jobs.boeing.com/job/brisbane/senior-software-engineer-autonomy/185/93152503552|||Senior Software Engineer - Autonomy|||Brisbane, Australia|||03/24/2026
https://jobs.boeing.com/job/el-segundo/atlassian-software-engineer-millennium-space-systems/185/90431568896|||Atlassian Software Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||02/18/2026
https://jobs.boeing.com/job/berkeley/missions-systems-software-engineer-embedded-associate-experienced-senior/185/91381475872|||Missions Systems Software Engineer - Embedded (Associate, Experienced, Senior)|||Berkeley, Missouri|||03/31/2026
https://jobs.boeing.com/job/richardson/associate-software-engineer-secure-networks-and-protocols/185/91877300160|||Associate Software Engineer- Secure Networks & Protocols|||Richardson, Texas|||03/19/2026
https://jobs.boeing.com/job/chantilly/full-stack-software-engineer-developer-experienced-or-senior/185/92654930032|||Full Stack Software Engineer, Developer (Experienced or Senior)|||Chantilly, Virginia; and other locations|||03/25/2026
https://jobs.boeing.com/job/chantilly/full-stack-software-engineer-developer-associate-or-experienced/185/92581515632|||Full Stack Software Engineer, Developer (Associate or Experienced)|||Chantilly, Virginia; and other locations|||03/25/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/software-engineer-associate-experienced-or-lead/185/93129043568|||Software Engineer (Associate, Experienced or Lead)|||Kirtland, Kirtland Air Force Base Auxiliary Field, New Mexico; and other locations|||03/23/2026
https://jobs.boeing.com/job/bristol/software-engineer-commercial-modification-associate-experienced-or-senior-level/185/92254077952|||Software Engineer - Commercial Modification (Associate, Experienced or Senior level)|||Bristol, United Kingdom; and other locations|||03/31/2026
https://jobs.boeing.com/job/everett/system-software-engineer-common-core-systems-mid-level-or-lead/185/90662809488|||System Software Engineer-Common Core Systems (Mid-Level or Lead)|||Everett, Washington|||03/23/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/embedded-software-engineer-mid-level-or-lead/185/92134095344|||Embedded Software Engineer (Mid-Level or Lead)|||Kirtland, Kirtland Air Force Base Auxiliary Field, New Mexico; and other locations|||03/23/2026
https://jobs.boeing.com/job/el-segundo/software-process-lead-engineer/185/93198197744|||Software Process Lead Engineer|||El Segundo, California|||03/25/2026
https://jobs.boeing.com/job/ridley-park/software-test-engineers-experienced-senior/185/89859741616|||Software Test Engineers (Experienced/Senior)|||Ridley Park, Pennsylvania|||03/20/2026
https://jobs.boeing.com/job/hazelwood/software-systems-engineer/185/91850669472|||Software Systems Engineer|||Hazelwood, Missouri|||03/17/2026
https://jobs.boeing.com/job/hazelwood/senior-ai-integration-project-engineer/185/92702390624|||Senior AI Integration Project Engineer|||Hazelwood, Missouri|||03/30/2026
https://jobs.boeing.com/job/seoul/ai-application-engineer/185/93212525904|||AI Application Engineer|||Seoul, South Korea|||03/30/2026
https://jobs.boeing.com/job/seoul/ai-mlops-engineer/185/89859750752|||AI/MLOps Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/seoul/associate-ai-ml-researcher-sensor-fusion/185/93478815872|||Associate AI/ML Researcher (Sensor Fusion)|||Seoul, South Korea|||04/02/2026
https://jobs.boeing.com/job/seattle/senior-data-and-ai-platform-data-engineer/185/92969184208|||Senior Data & AI Platform Data Engineer|||Seattle, Washington|||03/19/2026
https://jobs.boeing.com/job/seattle/experienced-data-and-ai-platform-cloud-devops-dataops-engineer/185/93159731008|||Experienced Data & AI Platform Cloud DevOps / DataOps Engineer|||Seattle, Washington|||03/24/2026
https://jobs.boeing.com/job/el-segundo/chief-engineer-artificial-intelligence-and-autonomy/185/93281026640|||Chief Engineer, Artificial Intelligence and Autonomy|||El Segundo, California; and other locations|||03/27/2026
https://jobs.boeing.com/job/huntsville/machine-learning-infrastructure-engineer-associate-or-experienced/185/93173911232|||Machine Learning Infrastructure Engineer (Associate or Experienced)|||Huntsville, Alabama|||03/24/2026
https://jobs.boeing.com/job/huntsville/senior-manager-artificial-intelligence/185/93005693344|||Senior Manager, Artificial Intelligence|||Huntsville, Alabama|||03/20/2026
https://jobs.boeing.com/job/bengaluru/lead-digital-engineer-plm/185/93190479424|||Lead Digital Engineer - PLM|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/bengaluru/associate-data-platform-engineer/185/92332104128|||Associate Data Platform Engineer|||Bengaluru, India|||03/09/2026
https://jobs.boeing.com/job/seoul/ml-researcher-computer-vision-sensor-fusion/185/89859750928|||ML Researcher (Computer Vision - Sensor Fusion)|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/bengaluru/experienced-test-and-evaluation-engineer/185/93370427408|||Experienced Test & Evaluation Engineer|||Bengaluru, India|||03/30/2026
https://jobs.boeing.com/job/seoul/ml-researcher-computer-vision-vision-language-model/185/89859750880|||ML Researcher (Computer Vision - Vision Language Model)|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/seoul/fpga-embedded-systems-engineer/185/86134052320|||FPGA/Embedded Systems Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/seattle/senior-cybersecurity-third-party-risk-analyst/185/93021195648|||Senior Cybersecurity Third-Party Risk Analyst|||Seattle, Washington; and other locations|||03/20/2026
https://jobs.boeing.com/job/bengaluru/senior-asic-fpga-verification-engineer/185/92911505408|||Senior ASIC-FPGA Verification Engineer|||Bengaluru, India|||03/20/2026
https://jobs.boeing.com/job/annapolis-junction/chief-architect/185/93130582928|||Chief Architect|||Annapolis Junction, Maryland|||03/24/2026
https://jobs.boeing.com/job/seattle/senior-business-intelligence-and-governance-architect/185/93473509920|||Senior Business Intelligence and Governance Architect|||Seattle, Washington; and other locations|||04/01/2026
https://jobs.boeing.com/job/berkeley/mid-level-computational-electromagnetics-engineer/185/92935537696|||Mid-Level Computational Electromagnetics Engineer|||Berkeley, Missouri|||03/18/2026
https://jobs.boeing.com/job/berkeley/software-manager-mission-systems-autonomy-and-artificial-intelligence-msa2i/185/93392312768|||Software Manager- Mission Systems, Autonomy, and Artificial Intelligence (MSA2I)|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/hazelwood/senior-product-manager/185/93290661712|||Senior Product Manager|||Hazelwood, Missouri; and other locations|||03/27/2026
https://jobs.boeing.com/job/everett/payloads-engineering-manager-automation-and-design-methods/185/93436103952|||Payloads Engineering Manager - Automation and Design Methods|||Everett, Washington|||03/31/2026
https://jobs.boeing.com/job/daytona-beach/senior-product-security-engineer/185/93426359696|||Senior Product Security Engineer|||Daytona Beach, Florida|||04/01/2026
https://jobs.boeing.com/job/berkeley/senior-product-security-engineer/185/93426333472|||Senior Product Security Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/bengaluru/systems-engineering-manager/185/93260704976|||Systems Engineering Manager|||Bengaluru, India|||03/27/2026
https://jobs.boeing.com/job/bengaluru/experienced-full-stack-developer/185/93190494432|||Experienced Full Stack Developer|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/bengaluru/associate-full-stack-developer/185/93190494400|||Associate Full Stack Developer|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/bengaluru/associate-manufacturing-engineer-electrical-electronics/185/93408415072|||Associate Manufacturing Engineer (Electrical/Electronics)|||Bengaluru, India|||03/31/2026
https://jobs.boeing.com/job/neu-isenburg/working-student-werkstudent-strategy-support-m-f-d/185/93103748544|||Working student / Werkstudent - Strategy Support (m/f/d)|||Neu-Isenburg, Germany|||03/23/2026
https://jobs.boeing.com/job/annapolis-junction/senior-level-front-end-developer/185/92463214192|||Senior-Level Front End Developer|||Annapolis Junction, Maryland|||03/06/2026
https://jobs.boeing.com/job/daytona-beach/associate-or-experienced-cloud-and-software-security-engineer/185/93426359632|||Associate or Experienced Cloud and Software Security Engineer|||Daytona Beach, Florida|||04/01/2026
https://jobs.boeing.com/job/berkeley/associate-or-experienced-cloud-and-software-security-engineer/185/93426333408|||Associate or Experienced Cloud and Software Security Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/bengaluru/lead-electro-mechanical-packaging-design-and-analysis-engineer/185/91432290192|||Lead Electro Mechanical Packaging Design & Analysis Engineer|||Bengaluru, India|||03/30/2026
https://jobs.boeing.com/job/el-segundo/static-timing-analysis-sta-engineer-lead-or-senior/185/90326817216|||Static Timing Analysis (STA) Engineer - (Lead or Senior)|||El Segundo, California|||03/23/2026
https://jobs.boeing.com/job/san-antonio/senior-information-technology-business-partner/185/93198199280|||Senior Information Technology Business Partner|||San Antonio, Texas; and other locations|||03/25/2026
https://jobs.boeing.com/job/el-segundo/senior-embedded-linux-and-bsp-software-engineer-avionics-millennium-space-systems/185/90125361776|||Senior Embedded Linux & BSP Software Engineer (Avionics) - Millennium Space Systems|||El Segundo, California; and other locations|||04/01/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/embedded-software-engineer-mid-level-or-lead/185/92134095344|||Embedded Software Engineer (Mid-Level or Lead)|||Kirtland, Kirtland Air Force Base Auxiliary Field, New Mexico; and other locations|||03/23/2026
https://jobs.boeing.com/job/seoul/associate-experienced-embedded-software-engineer/185/91360195040|||Associate/Experienced Embedded Software Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/albuquerque/system-controls-engineer-lead-or-senior/185/88326607648|||System Controls Engineer (Lead or Senior)|||Albuquerque, New Mexico|||03/24/2026
https://jobs.boeing.com/job/miami/visual-systems-specialist-flight-simulation/185/91674064928|||Visual Systems Specialist (Flight Simulation)|||Miami, Florida|||03/24/2026
https://jobs.boeing.com/job/el-segundo/mission-analysis-engineer-mid-career-millennium-space-systems/185/90566869776|||Mission Analysis Engineer (Mid-career) - Millennium Space Systems|||El Segundo, California; and other locations|||03/31/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/matlab-simulink-engineer-associate-or-mid-level/185/93281027072|||Matlab/Simulink Engineer (Associate or Mid-Level)|||Kirtland, Kirtland Air Force Base Auxiliary Field, New Mexico; and other locations|||03/27/2026
https://jobs.boeing.com/job/berkeley/senior-design-and-analysis-engineer/185/89859737632|||Senior Design and Analysis Engineer|||Berkeley, Missouri|||03/27/2026
https://jobs.boeing.com/job/el-segundo/mission-analysis-engineer-millennium-space-systems/185/90431566128|||Mission Analysis Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||03/12/2026
https://jobs.boeing.com/job/saint-charles/design-and-analysis-systems-engineer-experienced-or-senior-level/185/93246226032|||Design and Analysis Systems Engineer, Experienced or Senior Level|||Saint Charles, Missouri|||03/26/2026
https://jobs.boeing.com/job/el-segundo/digital-electronics-circuit-and-unit-hardware-design-engineer-lead-or-senior/185/89859732528|||Digital Electronics Circuit & Unit Hardware Design Engineer (Lead or Senior)|||El Segundo, California|||03/30/2026
https://jobs.boeing.com/job/albuquerque/asic-fpga-design-and-verification-engineer-lead-senior-or-principal/185/92348788864|||ASIC/FPGA Design and Verification Engineer - (Lead, Senior, or Principal)|||Albuquerque, New Mexico|||03/23/2026
https://jobs.boeing.com/job/berkeley/phantom-works-software-architect/185/93198199072|||Phantom Works Software Architect|||Berkeley, Missouri; and other locations|||03/25/2026
https://jobs.boeing.com/job/everett/senior-software-developer/185/93473509712|||Senior Software Developer|||Everett, Washington; and other locations|||04/01/2026
https://jobs.boeing.com/job/berkeley/senior-electrophysics-engr-scien-comm-and-sensor-systems/185/89859736880|||Senior Electrophysics Engr/Scien (Comm & Sensor Systems)|||Berkeley, Missouri; and other locations|||03/31/2026
https://jobs.boeing.com/job/long-beach/systems-engineer-systems-engineering-engineer-general/185/92095591200|||Systems Engineer (Systems Engineering Engineer-General)|||Long Beach, California|||03/17/2026
https://jobs.boeing.com/job/berkeley/manufacturing-engineer-manufacturing-engineer-general/185/91873459584|||Manufacturing Engineer (Manufacturing Engineer-General)|||Berkeley, Missouri|||03/16/2026
https://jobs.boeing.com/job/smithfield/manufacturing-engineer/185/93168328000|||Manufacturing Engineer|||Smithfield, Pennsylvania|||03/24/2026
https://jobs.boeing.com/job/oklahoma-city/systems-engineer/185/93202545296|||Systems Engineer|||Oklahoma City, Oklahoma|||03/25/2026
https://jobs.boeing.com/job/norderstedt/quality-engineer-f-m-d/185/93198199232|||Quality Engineer (f/m/d)|||Norderstedt, Germany|||03/25/2026
https://jobs.boeing.com/job/warsaw/associate-structural-analysis-engineer/185/93410851104|||Associate Structural Analysis Engineer|||Warsaw, Poland|||03/31/2026
https://jobs.boeing.com/job/huntsville/associate-or-mid-level-quality-engineer/185/93164328432|||Associate or Mid-Level Quality Engineer|||Huntsville, Alabama|||03/24/2026
https://jobs.boeing.com/job/huntsville/associate-or-mid-level-quality-engineer/185/93164328400|||Associate or Mid-Level Quality Engineer|||Huntsville, Alabama|||03/24/2026
https://jobs.boeing.com/job/titusville/manufacturing-engineer-mid-level-or-senior/185/88093096432|||Manufacturing Engineer (Mid-Level or Senior)|||Titusville, Florida|||03/26/2026
https://jobs.boeing.com/job/seal-beach/systems-engineer-associate-or-experienced/185/93396982800|||Systems Engineer (Associate or Experienced)|||Seal Beach, California|||03/30/2026
https://jobs.boeing.com/job/oklahoma-city/systems-engineer-experienced-or-lead/185/93202550624|||Systems Engineer (Experienced or Lead)|||Oklahoma City, Oklahoma|||03/25/2026
https://jobs.boeing.com/job/richardson/systems-engineer-lead-or-senior/185/90765650432|||Systems Engineer (Lead or Senior)|||Richardson, Texas|||03/23/2026
https://jobs.boeing.com/job/el-segundo/principal-test-engineer-millennium-space-systems/185/92438390400|||Principal Test Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||03/12/2026
https://jobs.boeing.com/job/el-segundo/build-reliability-engineer-millennium-space-systems/185/91452960032|||Build Reliability Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||03/23/2026
https://jobs.boeing.com/job/el-segundo/sr-test-engineer-millennium-space-systems/185/91110246144|||Sr.Test Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||02/18/2026
https://jobs.boeing.com/job/rzeszow/boeing-defense-and-space-experienced-manufacturing-engineer/185/90920930112|||Boeing Defense and Space Experienced Manufacturing Engineer|||Rzeszow, Poland|||04/01/2026
https://jobs.boeing.com/job/rzeszow/boeing-defense-and-space-associate-manufacturing-engineer/185/90920930080|||Boeing Defense and Space Associate Manufacturing Engineer|||Rzeszow, Poland|||04/01/2026
https://jobs.boeing.com/job/el-segundo/deputy-chief-engineer-millennium-space-systems/185/91381442192|||Deputy Chief Engineer - Millennium Space Systems|||El Segundo, California; and other locations|||04/01/2026
https://jobs.boeing.com/job/ridley-park/facilities-controls-engineer-experienced-or-senior/185/92325884688|||Facilities Controls Engineer (Experienced or Senior)|||Ridley Park, Pennsylvania|||03/20/2026
https://jobs.boeing.com/job/kotsiubynske/intern-student-engineer/185/92562164864|||Intern - Student Engineer|||Kotsiubynske, Ukraine|||03/09/2026
https://jobs.boeing.com/job/berkeley/associate-quality-engineer/185/93457570704|||Associate Quality Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/auburn/associate-quality-engineer/185/93236876032|||Associate Quality Engineer|||Auburn, Washington; and other locations|||03/26/2026
https://jobs.boeing.com/job/el-segundo/spacecraft-systems-engineer-senior-millennium-space-systems/185/92630294528|||Spacecraft Systems Engineer (Senior) - Millennium Space Systems|||El Segundo, California; and other locations|||04/01/2026
https://jobs.boeing.com/job/el-segundo/spacecraft-systems-engineer-experienced-millennium-space-systems/185/92624591824|||Spacecraft Systems Engineer (Experienced) - Millennium Space Systems|||El Segundo, California; and other locations|||03/18/2026
https://jobs.boeing.com/job/bristol/uk-e-7-integrity-management-lead-engineer/185/93380450032|||UK E-7 Integrity Management Lead Engineer|||Bristol, United Kingdom|||03/30/2026
https://jobs.boeing.com/job/hamburg/senior-seat-structures-engineer-m-f-d/185/93190493760|||Senior Seat Structures Engineer (m/f/d)|||Hamburg, Germany|||03/25/2026
https://jobs.boeing.com/job/herndon/devops-engineer-mid-level-senior-or-lead/185/91061051040|||DevOps Engineer (Mid-Level, Senior or Lead)|||Herndon, Virginia|||03/20/2026
https://jobs.boeing.com/job/hazelwood/sr-or-lead-devops-developer/185/93212521024|||Sr. or Lead DevOps Developer|||Hazelwood, Missouri; and other locations|||03/25/2026
https://jobs.boeing.com/job/herndon/devops-developer/185/91458412592|||DevOps Developer|||Herndon, Virginia|||03/09/2026
https://jobs.boeing.com/job/herndon/senior-devops-developer/185/91458412656|||Senior DevOps Developer|||Herndon, Virginia|||03/09/2026
https://jobs.boeing.com/job/seal-beach/associate-devops-developer/185/93457590464|||Associate DevOps Developer|||Seal Beach, California|||04/01/2026
https://jobs.boeing.com/job/seal-beach/entry-level-devops-developer/185/93463697584|||Entry Level DevOps Developer|||Seal Beach, California|||04/01/2026
https://jobs.boeing.com/job/seattle/experienced-data-and-ai-platform-cloud-devops-dataops-engineer/185/93159731008|||Experienced Data & AI Platform Cloud DevOps / DataOps Engineer|||Seattle, Washington|||03/24/2026
https://jobs.boeing.com/job/bengaluru/lead-cloud-devops-developer/185/92196705152|||Lead Cloud DevOps Developer|||Bengaluru, India|||03/30/2026
https://jobs.boeing.com/job/el-segundo/devsecops-lead-software-engineer/185/93198198000|||DevSecOps Lead Software Engineer|||El Segundo, California|||03/25/2026
https://jobs.boeing.com/job/wichita/enterprise-architect/185/89370124400|||Enterprise Architect|||Wichita, Kansas|||02/25/2026
https://jobs.boeing.com/job/hazelwood/senior-cloud-devops-developer/185/89859467744|||Senior Cloud DevOps Developer|||Hazelwood, Missouri|||03/30/2026
https://jobs.boeing.com/job/richardson/experienced-software-engineer-devsecops/185/91877300192|||Experienced Software Engineer-DevSecOps|||Richardson, Texas|||03/19/2026
https://jobs.boeing.com/job/hazelwood/associate-software-engineer/185/93426352528|||Associate Software Engineer|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/hazelwood/associate-software-engineer/185/92438390576|||Associate Software Engineer|||Hazelwood, Missouri|||03/05/2026
https://jobs.boeing.com/job/bengaluru/associate-data-platform-engineer/185/92332104128|||Associate Data Platform Engineer|||Bengaluru, India|||03/09/2026
https://jobs.boeing.com/job/bengaluru/experienced-test-and-evaluation-engineer/185/93370427408|||Experienced Test & Evaluation Engineer|||Bengaluru, India|||03/30/2026
https://jobs.boeing.com/job/herndon/network-engineer/185/91458412640|||Network Engineer|||Herndon, Virginia|||03/09/2026
https://jobs.boeing.com/job/huntsville/machine-learning-infrastructure-engineer-associate-or-experienced/185/93173911232|||Machine Learning Infrastructure Engineer (Associate or Experienced)|||Huntsville, Alabama|||03/24/2026
https://jobs.boeing.com/job/richmond/data-engineer/185/93276625504|||Data Engineer|||Richmond, Canada|||03/27/2026
https://jobs.boeing.com/job/hazelwood/software-systems-engineer/185/91850669472|||Software Systems Engineer|||Hazelwood, Missouri|||03/17/2026
https://jobs.boeing.com/job/long-beach/software-engineer-embedded-embedded/185/91806301248|||Software Engineer-Embedded (Embedded)|||Long Beach, California|||04/01/2026
https://jobs.boeing.com/job/brisbane/senior-software-engineer-autonomy/185/93152503552|||Senior Software Engineer - Autonomy|||Brisbane, Australia|||03/24/2026
https://jobs.boeing.com/job/hazelwood/associate-systems-engineer/185/89859753632|||Associate Systems Engineer|||Hazelwood, Missouri; and other locations|||04/01/2026
https://jobs.boeing.com/job/gdansk/experienced-avionx-software-engineer/185/93426359552|||Experienced AvionX Software Engineer|||Gdansk, Poland|||03/31/2026
https://jobs.boeing.com/job/saint-charles/experienced-embedded-software-engineer/185/89859722128|||Experienced Embedded Software Engineer|||Saint Charles, Missouri|||03/30/2026
https://jobs.boeing.com/job/everett/senior-software-developer/185/93473509712|||Senior Software Developer|||Everett, Washington; and other locations|||04/01/2026
https://jobs.boeing.com/job/el-segundo/software-engineering-manager/185/93392300752|||Software Engineering Manager|||El Segundo, California|||03/30/2026
https://jobs.boeing.com/job/seattle/senior-data-and-ai-platform-data-engineer/185/92969184208|||Senior Data & AI Platform Data Engineer|||Seattle, Washington|||03/19/2026
https://jobs.boeing.com/job/everett/engineering-technical-specialist-mid-level-or-senior/185/91638209232|||Engineering Technical Specialist (Mid-Level or Senior)|||Everett, Washington|||03/31/2026
https://jobs.boeing.com/job/berkeley/f-22-senior-system-integration-engineer/185/92105497696|||F-22 Senior System Integration Engineer|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/hazelwood/systems-engineer-experienced-or-lead/185/89859753328|||Systems Engineer (Experienced or Lead)|||Hazelwood, Missouri; and other locations|||04/01/2026
https://jobs.boeing.com/job/el-segundo/software-systems-engineer-senior-lead/185/82633460064|||Software Systems Engineer (Senior/Lead)|||El Segundo, California|||03/30/2026
https://jobs.boeing.com/job/seal-beach/experienced-software-engineer-test-and-verification/185/92170928848|||Experienced Software Engineer-Test & Verification|||Seal Beach, California|||03/31/2026
https://jobs.boeing.com/job/berkeley/missions-systems-software-engineer-embedded-associate-experienced-senior/185/91381475872|||Missions Systems Software Engineer - Embedded (Associate, Experienced, Senior)|||Berkeley, Missouri|||03/31/2026
https://jobs.boeing.com/job/bristol/software-engineer-experienced-or-senior-level/185/93190493696|||Software Engineer (Experienced or Senior Level)|||Bristol, United Kingdom; and other locations|||03/25/2026
https://jobs.boeing.com/job/seal-beach/associate-software-engineer-vehicle-management-systems/185/92316588208|||Associate Software Engineer-Vehicle Management Systems|||Seal Beach, California|||03/31/2026
https://jobs.boeing.com/job/berkeley/systems-and-project-integration-engineer-mid-level-or-senior/185/91815079264|||Systems and Project Integration Engineer (Mid-Level or Senior)|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/bengaluru/experienced-programmer-analyst-sap-abap-btp/185/93111734976|||Experienced Programmer Analyst- SAP ABAP BTP|||Bengaluru, India|||03/23/2026
https://jobs.boeing.com/job/seal-beach/mid-level-software-application-developer/185/93285048528|||Mid-Level Software Application Developer|||Seal Beach, California|||03/27/2026
https://jobs.boeing.com/job/bengaluru/experienced-software-engineer-java-full-stack/185/93469395344|||Experienced Software Engineer - Java Full Stack|||Bengaluru, India|||04/01/2026
https://jobs.boeing.com/job/berkeley/software-manager-mission-systems-autonomy-and-artificial-intelligence-msa2i/185/93392312768|||Software Manager- Mission Systems, Autonomy, and Artificial Intelligence (MSA2I)|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/port-melbourne/full-stack-developer/185/93364345408|||Full Stack Developer|||Port Melbourne, Australia|||03/30/2026
https://jobs.boeing.com/job/everett/experienced-or-senior-cybersecurity-analyst/185/93396982128|||Experienced or Senior Cybersecurity Analyst|||Everett, Washington; and other locations|||03/30/2026
https://jobs.boeing.com/job/mesa/cybersecurity-information-system-security-officer-isso/185/93478811792|||Cybersecurity - Information System Security Officer (ISSO)|||Mesa, Arizona|||04/01/2026
https://jobs.boeing.com/job/seattle/senior-cybersecurity-third-party-risk-analyst/185/93021195648|||Senior Cybersecurity Third-Party Risk Analyst|||Seattle, Washington; and other locations|||03/20/2026
https://jobs.boeing.com/job/herndon/cybersecurity-information-system-security-manager-issm/185/92902825280|||Cybersecurity - Information System Security Manager (ISSM)|||Herndon, Virginia|||03/27/2026
https://jobs.boeing.com/job/berkeley/cybersecurity-information-system-security-officer-isso/185/90627958720|||Cybersecurity - Information System Security Officer (ISSO)|||Berkeley, Missouri; and other locations|||03/30/2026
https://jobs.boeing.com/job/tukwila/cybersecurity-senior-information-system-security-manager-issm/185/93255481008|||Cybersecurity - Senior Information System Security Manager (ISSM)|||Tukwila, Washington|||03/26/2026
https://jobs.boeing.com/job/tukwila/cybersecurity-senior-information-system-security-manager-issm/185/93255480992|||Cybersecurity - Senior Information System Security Manager (ISSM)|||Tukwila, Washington|||03/26/2026
https://jobs.boeing.com/job/herndon/cybersecurity-senior-information-system-security-manager-issm/185/89859737904|||Cybersecurity - Senior Information System Security Manager (ISSM)|||Herndon, Virginia|||04/01/2026
https://jobs.boeing.com/job/hazelwood/product-security-engineer-mid-level/185/90636653936|||Product Security Engineer, Mid-Level|||Hazelwood, Missouri|||03/26/2026
https://jobs.boeing.com/job/long-beach/experienced-or-senior-or-expert-level-product-security-cyber-security-engineer/185/92708160208|||Experienced or Senior or Expert Level Product Security / Cyber Security Engineer|||Long Beach, California|||03/12/2026
https://jobs.boeing.com/job/hazelwood/product-security-engineer-lead/185/91837726800|||Product Security Engineer (Lead)|||Hazelwood, Missouri|||03/26/2026
https://jobs.boeing.com/job/hazelwood/product-security-engineer/185/90083253056|||Product Security Engineer|||Hazelwood, Missouri|||03/16/2026
https://jobs.boeing.com/job/williamtown/product-security-analyst-cyber-operations-and-compliance-specialist/185/93217778816|||Product Security Analyst - Cyber Operations & Compliance Specialist|||Williamtown, Australia|||03/26/2026
https://jobs.boeing.com/job/el-segundo/software-process-lead-engineer/185/93198197744|||Software Process Lead Engineer|||El Segundo, California|||03/25/2026
https://jobs.boeing.com/job/daytona-beach/senior-product-security-engineer/185/93426359696|||Senior Product Security Engineer|||Daytona Beach, Florida|||04/01/2026
https://jobs.boeing.com/job/berkeley/senior-product-security-engineer/185/93426333472|||Senior Product Security Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/hazelwood/systems-integration-analyst-experienced-or-lead/185/89859722688|||Systems Integration Analyst (Experienced or Lead)|||Hazelwood, Missouri; and other locations|||03/26/2026
https://jobs.boeing.com/job/hazelwood/systems-integration-engineer-experienced-or-lead/185/91310857040|||Systems Integration Engineer (Experienced or Lead)|||Hazelwood, Missouri; and other locations|||03/31/2026
https://jobs.boeing.com/job/daytona-beach/associate-or-experienced-cloud-and-software-security-engineer/185/93426359632|||Associate or Experienced Cloud and Software Security Engineer|||Daytona Beach, Florida|||04/01/2026
https://jobs.boeing.com/job/berkeley/associate-or-experienced-cloud-and-software-security-engineer/185/93426333408|||Associate or Experienced Cloud and Software Security Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/chantilly/ground-software-engineer-mid-career-millennium-space-systems/185/90184526704|||Ground Software Engineer (Mid Career) - Millennium Space Systems|||Chantilly, Virginia|||03/31/2026
https://jobs.boeing.com/job/wichita/cyber-architect-mid-level-or-senior/185/92969633008|||Cyber Architect (Mid-Level or Senior)|||Wichita, Kansas|||03/19/2026
https://jobs.boeing.com/job/aurora/senior-cloud-solution-architect/185/93281005440|||Senior Cloud Solution Architect|||Aurora, Colorado; and other locations|||03/27/2026
https://jobs.boeing.com/job/charleston/product-security-senior-manager/185/93432135312|||Product Security Senior Manager|||Charleston, South Carolina|||03/31/2026
https://jobs.boeing.com/job/colorado-springs/senior-software-architect-space-mission-systems/185/93206788784|||Senior Software Architect, Space Mission Systems|||Colorado Springs, Colorado; and other locations|||03/25/2026
https://jobs.boeing.com/job/amberley/mission-planning-environment-system-administrator/185/93152503488|||Mission Planning Environment - System Administrator|||Amberley, Australia|||03/24/2026
https://jobs.boeing.com/job/richmond/product-line-leader-strategic-asset-lifecycle-management/185/93469396144|||Product Line Leader - Strategic Asset Lifecycle Management|||Richmond, Canada|||04/01/2026
https://jobs.boeing.com/job/englewood/product-line-leader-strategic-asset-lifecycle-management/185/93436106080|||Product Line Leader - Strategic Asset Lifecycle Management|||Englewood, Colorado; and other locations|||04/01/2026
https://jobs.boeing.com/job/tokyo/business-information-security-officer-biso-japan-singapore-korea/185/93198198848|||Business Information Security Officer (BISO)- Japan/Singapore/Korea|||Tokyo, Japan; and other locations|||03/25/2026
https://jobs.boeing.com/job/waddington/cyber-security-analyst/185/92911472096|||Cyber Security Analyst|||Waddington, United Kingdom|||03/31/2026
https://jobs.boeing.com/job/wichita/mid-level-security-architect/185/91874111088|||Mid-Level - Security Architect|||Wichita, Kansas|||02/18/2026
https://jobs.boeing.com/job/wichita/senior-security-architect/185/91874111072|||Senior Security Architect|||Wichita, Kansas|||02/18/2026
https://jobs.boeing.com/job/seattle/it-security-design-specialist/185/91390338976|||IT Security Design Specialist|||Seattle, Washington; and other locations|||03/26/2026
https://jobs.boeing.com/job/brisbane/cyber-business-analyst/185/88405239792|||Cyber Business Analyst|||Brisbane, Australia|||03/27/2026
https://jobs.boeing.com/job/annapolis-junction/information-systems-security-officer-mid-level/185/87482198032|||Information Systems Security Officer - Mid Level|||Annapolis Junction, Maryland|||02/06/2026
https://jobs.boeing.com/job/long-beach/systems-engineer-systems-engineering-engineer-general/185/92095591200|||Systems Engineer (Systems Engineering Engineer-General)|||Long Beach, California|||03/17/2026
https://jobs.boeing.com/job/oklahoma-city/systems-engineer/185/93202545296|||Systems Engineer|||Oklahoma City, Oklahoma|||03/25/2026
https://jobs.boeing.com/job/long-beach/software-engineer-embedded-embedded/185/91806301248|||Software Engineer-Embedded (Embedded)|||Long Beach, California|||04/01/2026
https://jobs.boeing.com/job/seoul/fpga-embedded-systems-engineer/185/86134052320|||FPGA/Embedded Systems Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/bengaluru/lead-software-engineer-embedded/185/93103735952|||Lead Software Engineer-Embedded|||Bengaluru, India|||03/23/2026
https://jobs.boeing.com/job/seoul/associate-experienced-embedded-software-engineer/185/91360195040|||Associate/Experienced Embedded Software Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/seoul/associate-experienced-embedded-software-engineer-linux/185/89859442560|||Associate/Experienced Embedded Software Engineer (Linux)|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/embedded-software-engineer-mid-level-or-lead/185/92134095344|||Embedded Software Engineer (Mid-Level or Lead)|||Kirtland, New Mexico; and other locations|||03/23/2026
https://jobs.boeing.com/job/el-segundo/senior-embedded-linux-and-bsp-software-engineer-avionics-millennium-space-systems/185/90125361776|||Senior Embedded Linux & BSP Software Engineer (Avionics) - Millennium Space Systems|||El Segundo, California; and other locations|||04/01/2026
https://jobs.boeing.com/job/berkeley/senior-electrophysics-engr-scien-comm-and-sensor-systems/185/89859736880|||Senior Electrophysics Engr/Scien (Comm & Sensor Systems)|||Berkeley, Missouri; and other locations|||03/31/2026
https://jobs.boeing.com/job/hazelwood/lead-software-engineer-vehicle-management-systems/185/93432138480|||Lead Software Engineer-Vehicle Management Systems|||Hazelwood, Missouri|||03/31/2026
https://jobs.boeing.com/job/hazelwood/lead-software-engineer-vehicle-management-systems-remote/185/93432138496|||Lead Software Engineer-Vehicle Management Systems (Remote)|||Hazelwood, Missouri; and other locations|||03/31/2026
https://jobs.boeing.com/job/hazelwood/lead-real-time-software-architect/185/92362938720|||Lead Real-Time Software Architect|||Hazelwood, Missouri|||03/23/2026
https://jobs.boeing.com/job/gdansk/experienced-avionx-software-systems-engineer/185/93426349424|||Experienced AvionX Software Systems Engineer|||Gdansk, Poland|||03/31/2026
https://jobs.boeing.com/job/berkeley/senior-design-and-analysis-engineer/185/89859737632|||Senior Design and Analysis Engineer|||Berkeley, Missouri|||03/27/2026
https://jobs.boeing.com/job/kotsiubynske/systems-engineer/185/93120532320|||Systems Engineer|||Kotsiubynske, Ukraine|||03/23/2026
https://jobs.boeing.com/job/bristol/software-engineer-commercial-modification-associate-experienced-or-senior-level/185/92254077952|||Software Engineer - Commercial Modification (Associate, Experienced or Senior level)|||Bristol, United Kingdom; and other locations|||03/31/2026
https://jobs.boeing.com/job/gdansk/associate-avionx-software-engineer/185/93426359456|||Associate AvionX Software Engineer|||Gdansk, Poland; and other locations|||03/31/2026
https://jobs.boeing.com/job/berkeley/senior-market-development-specialist-sales-capture-team/185/93009824848|||Senior Market Development Specialist (Sales/Capture Team)|||Berkeley, Missouri; and other locations|||03/27/2026
https://jobs.boeing.com/job/berkeley/phantom-works-software-architect/185/93198199072|||Phantom Works Software Architect|||Berkeley, Missouri; and other locations|||03/25/2026
https://jobs.boeing.com/job/albuquerque/asic-fpga-design-and-verification-engineer-lead-senior-or-principal/185/92348788864|||ASIC/FPGA Design and Verification Engineer - (Lead, Senior, or Principal)|||Albuquerque, New Mexico|||03/23/2026
https://jobs.boeing.com/job/los-angeles/test-automation-engineer/185/93432143968|||Test Automation Engineer|||Los Angeles, California|||03/31/2026
https://jobs.boeing.com/job/oklahoma-city/mid-level-software-engineer-test-and-verification/185/93290680352|||Mid-Level Software Engineer (Test & Verification)|||Oklahoma City, Oklahoma|||03/27/2026
https://jobs.boeing.com/job/berkeley/senior-software-systems-engineer/185/92059669904|||Senior Software Systems Engineer|||Berkeley, Missouri|||03/27/2026
https://jobs.boeing.com/job/bengaluru/software-engineering-manager/185/93260705424|||Software Engineering Manager|||Bengaluru, India|||03/27/2026
https://jobs.boeing.com/job/bengaluru/senior-asic-fpga-verification-engineer/185/92911505408|||Senior ASIC-FPGA Verification Engineer|||Bengaluru, India|||03/20/2026
https://jobs.boeing.com/job/huntington-beach/associate-software-engineer-developer/185/93473508960|||Associate Software Engineer - Developer|||Huntington Beach, California|||04/01/2026
https://jobs.boeing.com/job/kirtland-kirtland-air-force-base-auxiliary-field/matlab-simulink-engineer-associate-or-mid-level/185/93281027072|||Matlab/Simulink Engineer (Associate or Mid-Level)|||Kirtland, New Mexico; and other locations|||03/27/2026
https://jobs.boeing.com/job/charleston-afb/associate-field-engineer-chs/185/92897196544|||Associate Field Engineer - CHS|||Charleston AFB, South Carolina|||03/25/2026
https://jobs.boeing.com/job/bristol/software-certification-engineer-senior-or-expert-level/185/92254078000|||Software Certification Engineer (Senior or Expert level)|||Bristol, United Kingdom; and other locations|||04/01/2026
https://jobs.boeing.com/job/albuquerque/software-engineer-hardware-emulation-experienced-or-senior/185/92399872144|||Software Engineer, Hardware Emulation (Experienced or Senior)|||Albuquerque, New Mexico|||03/23/2026
https://jobs.boeing.com/job/aurora/senior-cloud-solution-architect/185/93281005440|||Senior Cloud Solution Architect|||Aurora, Colorado; and other locations|||03/27/2026
https://jobs.boeing.com/job/daytona-beach/associate-or-experienced-cloud-and-software-security-engineer/185/93426359632|||Associate or Experienced Cloud and Software Security Engineer|||Daytona Beach, Florida|||04/01/2026
https://jobs.boeing.com/job/berkeley/associate-or-experienced-cloud-and-software-security-engineer/185/93426333408|||Associate or Experienced Cloud and Software Security Engineer|||Berkeley, Missouri|||04/01/2026
https://jobs.boeing.com/job/seattle/senior-cloud-platform-kubernetes-specialist/185/93473502352|||Senior Cloud Platform Kubernetes Specialist|||Seattle, Washington; and other locations|||04/01/2026
https://jobs.boeing.com/job/seoul/junior-senior-software-engineer/185/89859726880|||Junior/Senior Software Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/bengaluru/senior-solutions-architect/185/90860958240|||Senior Solutions Architect|||Bengaluru, India|||03/27/2026
https://jobs.boeing.com/job/el-segundo/senior-network-engineer-millennium-space-systems/185/92957554480|||Senior Network Engineer-Millennium Space Systems|||El Segundo, California; and other locations|||03/19/2026
https://jobs.boeing.com/job/chantilly/senior-full-stack-software-engineer/185/90624053216|||Senior Full-Stack Software Engineer|||Chantilly, Virginia; and other locations|||03/23/2026
https://jobs.boeing.com/job/seoul/ai-mlops-engineer/185/89859750752|||AI/MLOps Engineer|||Seoul, South Korea|||03/27/2026
https://jobs.boeing.com/job/bengaluru/associate-programmer-analyst-net-full-stack/185/93260700320|||Associate Programmer Analyst - .Net Full Stack|||Bengaluru, India|||03/27/2026
https://jobs.boeing.com/job/annapolis-junction/database-engineer-mid-level/185/87482197984|||Database Engineer - Mid Level|||Annapolis Junction, Maryland|||02/06/2026
https://jobs.boeing.com/job/annapolis-junction/database-engineer-entry-level/185/87605858016|||Database Engineer - Entry Level|||Annapolis Junction, Maryland|||02/07/2026
https://jobs.boeing.com/job/daytona-beach/senior-software-engineer/185/92386375632|||Senior Software Engineer|||Daytona Beach, Florida|||03/29/2026
https://jobs.boeing.com/job/berkeley/software-engineer-developer-development/185/93426337920|||Software Engineer-Developer (Development)|||Berkeley, Missouri|||03/31/2026
https://jobs.boeing.com/job/daytona-beach/mid-level-software-engineer/185/92362910192|||Mid Level Software Engineer|||Daytona Beach, Florida|||03/29/2026
https://jobs.boeing.com/job/seattle/network-architecture-and-design-senior-manager/185/93432143920|||Network Architecture and Design Senior Manager|||Seattle, Washington; and other locations|||03/31/2026
https://jobs.boeing.com/job/hazelwood/sr-or-lead-devops-developer/185/93212521024|||Sr. or Lead DevOps Developer|||Hazelwood, Missouri; and other locations|||03/25/2026
https://jobs.boeing.com/job/berkeley/senior-computing-architect/185/93478815824|||Senior Computing Architect|||Berkeley, Missouri; and other locations|||04/01/2026
https://jobs.boeing.com/job/chantilly/full-stack-software-engineer-associate-experienced/185/93014443072|||Full-Stack Software Engineer (Associate/Experienced)|||Chantilly, Virginia; and other locations|||03/20/2026
https://jobs.boeing.com/job/bengaluru/experienced-test-and-evaluation-engineer/185/93370427408|||Experienced Test & Evaluation Engineer|||Bengaluru, India|||03/30/2026
https://jobs.boeing.com/job/bengaluru/associate-software-engineer-full-stack-developer/185/91618391424|||Associate Software Engineer - Full Stack Developer|||Bengaluru, India|||04/01/2026
https://jobs.boeing.com/job/berkeley/f-22-simulation-software-engineer-associate-experienced-and-senior/185/93392329616|||F-22 Simulation Software Engineer (Associate, Experienced, and Senior)|||Berkeley, Missouri|||03/30/2026
https://jobs.boeing.com/job/hazelwood/senior-product-manager/185/93290661712|||Senior Product Manager|||Hazelwood, Missouri; and other locations|||03/27/2026
https://jobs.boeing.com/job/bengaluru/experienced-full-stack-developer/185/93190494432|||Experienced Full Stack Developer|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/bengaluru/associate-full-stack-developer/185/93190494400|||Associate Full Stack Developer|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/bengaluru/lead-digital-engineer-plm/185/93190479424|||Lead Digital Engineer - PLM|||Bengaluru, India|||03/25/2026
https://jobs.boeing.com/job/kent/site-reliability-product-owner/185/92348797888|||Site Reliability Product Owner|||Kent, Washington|||03/25/2026
https://jobs.boeing.com/job/seoul/ai-application-engineer/185/93212525904|||AI Application Engineer|||Seoul, South Korea|||03/30/2026
https://jobs.boeing.com/job/everett/software-and-controls-engineer/185/93202552576|||Software and Controls Engineer|||Everett, Washington|||03/25/2026
https://jobs.boeing.com/job/bengaluru/customer-support-service-engineering-manager/185/93463696496|||Customer Support Service Engineering Manager|||Bengaluru, India|||04/01/2026
""".strip()


def parse_date(date_str):
    """Parse MM/DD/YYYY to YYYY-MM-DD"""
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    try:
        dt = datetime.strptime(date_str.strip(), '%m/%d/%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')


def extract_job_id(url):
    """Extract numeric job ID from Boeing URL"""
    m = re.search(r'/185/(\d+)$', url)
    return m.group(1) if m else None


def main():
    con = sqlite3.connect(DB_PATH, timeout=60)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=60000')
    cur = con.cursor()

    # Ensure jobs table exists (in case it's a fresh DB)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            source TEXT,
            date_posted TEXT,
            description TEXT,
            score REAL,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    con.commit()

    inserted = 0
    skipped = 0
    errors = 0

    lines = [l.strip() for l in RAW_JOBS.split('\n') if l.strip()]
    seen_urls = set()

    for line in lines:
        parts = line.split('|||')
        if len(parts) < 2:
            continue
        url = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ''
        location = parts[2].strip() if len(parts) > 2 else ''
        date_raw = parts[3].strip() if len(parts) > 3 else ''

        if not url or not title:
            continue

        # Deduplicate within this batch
        if url in seen_urls:
            skipped += 1
            continue
        seen_urls.add(url)

        date_posted = parse_date(date_raw)

        try:
            cur.execute('''
                INSERT OR IGNORE INTO jobs (title, company, location, url, source, date_posted, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, 'Boeing', location, url, 'boeing', date_posted, 'new'))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f'ERROR inserting {url}: {e}')
            errors += 1

    con.commit()
    con.close()

    print(f'Boeing jobs insert complete:')
    print(f'  Inserted: {inserted}')
    print(f'  Skipped (dupes): {skipped}')
    print(f'  Errors: {errors}')
    print(f'  Total lines processed: {len(lines)}')


if __name__ == '__main__':
    main()
