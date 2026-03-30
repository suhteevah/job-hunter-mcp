param([string]$query)
$output = & 'J:\wraith-browser\target\release\openclaw-browser.exe' search $query --max-results 15 2>&1
$output | Select-String -Pattern '^\d+\.' | ForEach-Object { $_.Line }
