Get-Process | Where-Object { $_.Name -like '*flare*' -or $_.Name -like '*chrome*' -or $_.Name -like '*python*' } | Select-Object Name, Id | Format-Table -AutoSize
