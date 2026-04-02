$ErrorActionPreference = 'Continue'
$python = "J:\job-hunter-mcp\.venv\Scripts\python.exe"
$script = "J:\job-hunter-mcp\scripts\swarm\indeed_defense_chrome_scrape.py"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$log = "J:\job-hunter-mcp\scripts\swarm\logs\indeed_defense_chrome_$ts.txt"

Write-Host "Starting Indeed defense/hardware Chrome scrape..."
& $python $script 2>&1 | Tee-Object -FilePath $log
Write-Host "Done. Log: $log"
