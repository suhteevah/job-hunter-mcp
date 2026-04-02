# Launch Chrome with CDP using a temp profile (to avoid lock issues)
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$TempProfile = "C:\Temp\chrome-cdp-profile"

# Create temp dir if needed
New-Item -ItemType Directory -Force -Path $TempProfile | Out-Null

Write-Host "Launching Chrome with CDP on port 9222 (temp profile)..."
$proc = Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=`"$TempProfile`"",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-popup-blocking",
    "about:blank"
) -PassThru -WindowStyle Minimized

Write-Host "Chrome PID: $($proc.Id)"
Start-Sleep -Seconds 5

Write-Host "Testing CDP..."
try {
    $r = Invoke-WebRequest -Uri "http://localhost:9222/json/version" -TimeoutSec 8
    Write-Host "CDP OK: $($r.StatusCode)"
    Write-Host $r.Content
} catch {
    Write-Host "CDP failed: $($_.Exception.Message)"
}
