# Kill ALL chrome with remote-debugging-port=9222, start fresh with temp profile
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$TempDir = "C:\Temp\chrome-scrape-profile-$([int](Get-Date -UFormat %s))"

Write-Host "Killing any Chrome with port 9222..."
$procs = Get-CimInstance Win32_Process -Filter 'Name="chrome.exe"'
foreach ($p in $procs) {
    if ($p.CommandLine -like "*remote-debugging-port=9222*" -and $p.CommandLine -notlike "*--type=*") {
        Write-Host "  Killing PID $($p.ProcessId)"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
Write-Host "Temp profile: $TempDir"

Write-Host "Launching Chrome with fresh profile + CDP port 9222..."
$proc = Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$TempDir`"",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-sync",
    "--disable-extensions",
    "about:blank"
) -PassThru -WindowStyle Hidden

Write-Host "Chrome PID: $($proc.Id)"
Write-Host "Waiting 10 seconds..."
Start-Sleep -Seconds 10

Write-Host "Testing CDP on 127.0.0.1:9222..."
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 8 -UseBasicParsing
    Write-Host "CDP OK: $($r.StatusCode)"
    Write-Host $r.Content.Substring(0, [Math]::Min(300, $r.Content.Length))
} catch {
    Write-Host "CDP failed: $($_.Exception.Message)"
    # Try alternate
    try {
        $r2 = Invoke-WebRequest -Uri "http://localhost:9222/json" -TimeoutSec 5 -UseBasicParsing
        Write-Host "CDP (json) OK"
    } catch {
        Write-Host "CDP json also failed"
    }
}
