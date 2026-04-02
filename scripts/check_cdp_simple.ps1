try {
    $r = Invoke-WebRequest -Uri "http://localhost:9222/json/version" -TimeoutSec 5
    Write-Host "CDP OK: $($r.StatusCode)"
    Write-Host $r.Content
} catch {
    Write-Host "CDP not on 9222"
}

try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:9223/json/version" -TimeoutSec 5
    Write-Host "CDP on 9223: $($r2.StatusCode)"
} catch {
    Write-Host "CDP not on 9223"
}
