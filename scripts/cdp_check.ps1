Start-Sleep -Seconds 3
try {
    $r = Invoke-WebRequest -Uri "http://localhost:9222/json" -TimeoutSec 8
    Write-Host "CDP OK"
    Write-Host $r.Content
} catch {
    Write-Host "CDP not available: $($_.Exception.Message)"
}
