$action = New-ScheduledTaskAction -Execute "J:\job-hunter-mcp\run_scheduler.bat" -WorkingDirectory "J:\job-hunter-mcp"
$trigger = New-ScheduledTaskTrigger -Once -At "06:00" -RepetitionInterval (New-TimeSpan -Hours 4)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "JobHunterMCP" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Scheduled task registered successfully!"
