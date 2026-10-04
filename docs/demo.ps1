# ==============================================================================
# Rclone Cloud Manager - Interactive Demo Recording Script (PowerShell)
# Automates all CLI commands for screen/video demonstrations & screenshots.
# Works out-of-the-box using local demo folders (no cloud credentials required).
# ==============================================================================

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $ProjectRoot

$PythonExe = "$ProjectRoot\venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

function Pause-Step {
    Write-Host ""
    Write-Host "[Press ENTER to proceed to the next step...]" -ForegroundColor Yellow
    [void][System.Console]::ReadLine()
}

Clear-Host
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "        🎬 Rclone Cloud Manager - Live Feature Demo 🎬           " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "This script demonstrates the full workflow for video/screenshot capture."
Pause-Step

# 1. CLI Help
Clear-Host
Write-Host ">>> STEP 1: CLI Overview & Available Subcommands" -ForegroundColor Cyan
Write-Host "$ python src/main.py --help" -ForegroundColor DarkGray
Write-Host ""
& $PythonExe src/main.py --help
Pause-Step

# 2. List Remotes
Clear-Host
Write-Host ">>> STEP 2: Listing Configured Cloud Remotes" -ForegroundColor Cyan
Write-Host "$ python src/main.py list-remotes" -ForegroundColor DarkGray
Write-Host ""
& $PythonExe src/main.py list-remotes
Pause-Step

# 3. Setup Demo Data
$DemoSrc = "$ProjectRoot\demo_data\source"
$DemoDst = "$ProjectRoot\demo_data\destination"

New-Item -ItemType Directory -Force -Path $DemoSrc | Out-Null
New-Item -ItemType Directory -Force -Path $DemoDst | Out-Null
Set-Content -Path "$DemoSrc\report_q3.docx" -Value "Financial Report 2026 - Q3"
Set-Content -Path "$DemoSrc\database_backup.sql" -Value "Database dump payload"
Set-Content -Path "$DemoSrc\photo_01.raw" -Value "Photo raw asset 001"

# 4. Sync Demonstration
Clear-Host
Write-Host ">>> STEP 3: Multi-Cloud / Local Directory Sync" -ForegroundColor Cyan
Write-Host "$ python src/main.py sync demo_data/source demo_data/destination" -ForegroundColor DarkGray
Write-Host ""
& $PythonExe src/main.py sync demo_data/source demo_data/destination
Pause-Step

# 5. Backup Demonstration
Clear-Host
Write-Host ">>> STEP 4: Timestamped Backup (Copy Mode)" -ForegroundColor Cyan
Set-Content -Path "$DemoSrc\update_patch.tar.gz" -Value "New revision asset archive"
Write-Host "$ python src/main.py backup demo_data/source demo_data/destination" -ForegroundColor DarkGray
Write-Host ""
& $PythonExe src/main.py backup demo_data/source demo_data/destination
Pause-Step

# 6. Status Output
Clear-Host
Write-Host ">>> STEP 5: Real-Time Execution Status & Audit Log" -ForegroundColor Cyan
Write-Host "$ python src/main.py status" -ForegroundColor DarkGray
Write-Host ""
& $PythonExe src/main.py status
Pause-Step

# 7. Log Inspection
Clear-Host
Write-Host ">>> STEP 6: Inspection of Daily Rotating Log File" -ForegroundColor Cyan
$LatestLog = Get-ChildItem -Path "$ProjectRoot\logs\rclone_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($LatestLog) {
    Write-Host "Displaying latest lines from: $($LatestLog.FullName)" -ForegroundColor Green
    Write-Host "--------------------------------------------------------"
    Get-Content $LatestLog.FullName -Tail 25
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "🎉 Live Demo Completed Successfully! 🎉" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
