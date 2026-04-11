# Registers the Job Hunter Orchestrator scheduled task. Idempotent.
# Runs every 30 minutes. See HANDOFF.md for management commands.

$ErrorActionPreference = 'Stop'

$TaskName    = 'JobHunterOrchestrator'
$ProjectRoot = 'J:\job-hunter-mcp'
$VenvPython  = 'J:\job-hunter-mcp\.venv\Scripts\python.exe'
$Script      = 'J:\job-hunter-mcp\scripts\orchestrator\run.py'

if (-not (Test-Path $VenvPython)) {
    Write-Error "Venv python not found: $VenvPython"
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Error "Orchestrator script not found: $Script"
    exit 1
}

Write-Host "Registering scheduled task..."

$Action = New-ScheduledTaskAction -Execute $VenvPython -Argument $Script -WorkingDirectory $ProjectRoot

$Now    = Get-Date
$Start  = $Now.AddMinutes(2)
$Trigger = New-ScheduledTaskTrigger -Once -At $Start -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::FromDays(3650))

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 25) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5)

$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing task found, removing..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'Job Hunter Orchestrator - sniper mode. Scrape + score + shortlist every 30 min. Never auto-applies.' | Out-Null

Write-Host "OK - task registered."
Write-Host "First run scheduled for: $Start"
Write-Host "Logs: J:\job-hunter-mcp\.pipeline\logs\"
Write-Host "Shortlist: J:\job-hunter-mcp\.pipeline\shortlist\current.md"
