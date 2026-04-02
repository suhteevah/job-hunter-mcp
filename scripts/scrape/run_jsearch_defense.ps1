$ErrorActionPreference = 'Continue'
$python = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
$script = "J:\job-hunter-mcp\scripts\scrape\jsearch_defense_hardware_scrape.py"
$log = "J:\job-hunter-mcp\scripts\swarm\logs\jsearch_defense_run.txt"

Write-Host "Starting JSearch defense/hardware scrape..."
& $python $script 2>&1 | Tee-Object -FilePath $log
Write-Host "Done. Log: $log"
