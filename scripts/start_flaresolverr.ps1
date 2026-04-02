# Start FlareSolverr for Cloudflare bypass
# Check if Docker is available and start FlareSolverr container

Write-Host "Checking Docker status..."
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker is running"
    } else {
        Write-Host "Docker not running or not installed. Output: $dockerInfo"
        exit 1
    }
} catch {
    Write-Host "Docker not found: $($_.Exception.Message)"
    exit 1
}

# Check if FlareSolverr container is already running
$existing = docker ps --filter "name=flaresolverr" --format "{{.Names}}" 2>&1
if ($existing -like "*flaresolverr*") {
    Write-Host "FlareSolverr already running!"
} else {
    Write-Host "Starting FlareSolverr container..."
    docker run -d `
        --name flaresolverr `
        -p 8191:8191 `
        -e LOG_LEVEL=info `
        --restart unless-stopped `
        ghcr.io/flaresolverr/flaresolverr:latest 2>&1

    Write-Host "Waiting 10s for FlareSolverr to start..."
    Start-Sleep -Seconds 10
}

# Test FlareSolverr
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8191/v1" -TimeoutSec 10
    Write-Host "FlareSolverr UP: $($r.StatusCode)"
} catch {
    Write-Host "FlareSolverr test failed: $($_.Exception.Message)"
    # Check logs
    Write-Host "Container logs:"
    docker logs flaresolverr --tail 20 2>&1
}
