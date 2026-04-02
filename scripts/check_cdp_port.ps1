try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -TimeoutSec 5 -UseBasicParsing
    Write-Host "CDP OK on 9222"
    Write-Host $r.Content.Substring(0, [Math]::Min(300, $r.Content.Length))
} catch {
    Write-Host "CDP 9222 failed: $($_.Exception.Message)"
}
