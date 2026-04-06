taskkill /F /IM chrome.exe 2>$null
Write-Output "--- Docker containers ---"
docker ps --format "{{.Names}} {{.Status}}"
Write-Output "`n--- Top RAM consumers ---"
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name, @{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize
Write-Output "`n--- WSL memory ---"
wsl --list --verbose 2>$null
