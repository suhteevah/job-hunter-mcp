$ErrorActionPreference = 'Continue'
$python = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
$script = "J:\job-hunter-mcp\scripts\scrape\indeed_defense_hardware_scrape.py"
$log = "J:\job-hunter-mcp\scripts\swarm\logs\scrape_defense_run.txt"

Write-Host "Starting Indeed defense/hardware scrape..."
& $python $script 2>&1 | Tee-Object -FilePath $log
Write-Host "Scrape complete. Log: $log"
