# Wait for file dialog to appear, then type the path and press Enter
Add-Type -AssemblyName System.Windows.Forms
Start-Sleep -Seconds 2

# Type the file path into the file dialog's filename field
[System.Windows.Forms.SendKeys]::SendWait("C:\Users\Matt\Downloads\matt_gates_resume_ai.docx")
Start-Sleep -Milliseconds 500

# Press Enter to confirm
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
