$procs = Get-CimInstance Win32_Process -Filter 'Name="chrome.exe"'
foreach ($p in $procs) {
    if ($p.CommandLine -like "*remote-debugging*") {
        Write-Host "PID $($p.ProcessId): $($p.CommandLine.Substring(0, [Math]::Min(200, $p.CommandLine.Length)))"
    }
}
if (-not ($procs | Where-Object { $_.CommandLine -like "*remote-debugging*" })) {
    Write-Host "No Chrome process found with --remote-debugging flag"
}
