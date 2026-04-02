# Launch Chrome with remote debugging port for CDP access
# Uses existing user profile so cookies/session are preserved
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$UserDataDir = "C:\Users\Matt\AppData\Local\Google\Chrome\User Data"

# Kill existing Chrome first to free up the profile lock
Write-Host "Closing existing Chrome processes..."
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Launching Chrome with CDP debug port 9222..."
Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$UserDataDir`"",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "https://www.indeed.com"
) -WindowStyle Minimized

Start-Sleep -Seconds 4
Write-Host "Chrome launched. Testing CDP..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:9222/json" -TimeoutSec 5
    Write-Host "CDP OK: $($r.StatusCode)"
} catch {
    Write-Host "CDP check: $($_.Exception.Message)"
}
