# Kill all Chrome instances, then relaunch with user profile + CDP debug port
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$UserDataDir = "C:\Users\Matt\AppData\Local\Google\Chrome\User Data"

Write-Host "Killing all Chrome processes..."
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Write-Host "Launching Chrome with user profile + CDP port 9222..."
$proc = Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$UserDataDir`"",
    "--profile-directory=Default",
    "--no-first-run",
    "--no-default-browser-check",
    "https://www.indeed.com"
) -PassThru

Write-Host "Chrome PID: $($proc.Id)"
Write-Host "Waiting 8 seconds for Chrome to start..."
Start-Sleep -Seconds 8

Write-Host "Testing CDP..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:9222/json/version" -TimeoutSec 10
    Write-Host "CDP OK: $($r.StatusCode)"
} catch {
    Write-Host "CDP failed: $($_.Exception.Message)"
}
