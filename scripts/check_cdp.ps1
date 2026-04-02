for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:9222/json/version" -TimeoutSec 3
        Write-Host "CDP UP at attempt $i : $($r.StatusCode)"
        Write-Host $r.Content
        break
    } catch {
        Write-Host "Attempt $i : $($_.Exception.Message)"
    }
}
