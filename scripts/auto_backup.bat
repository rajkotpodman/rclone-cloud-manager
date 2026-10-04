@echo off
rem ==============================================================================
rem Rclone Cloud Manager - Daily Automated Backup Batch Script (Windows)
rem Scheduled via Windows Task Scheduler (Daily at 02:00 AM)
rem ==============================================================================

rem Navigate to project root directory (one level up from scripts)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"

rem Ensure logs directory exists
if not exist "%PROJECT_ROOT%\logs" (
    mkdir "%PROJECT_ROOT%\logs"
)
set "CRON_LOG=%PROJECT_ROOT%\logs\cron.log"

echo ========================================================== >> "%CRON_LOG%"
echo [TASK START] %DATE% %TIME% - Starting automated daily backup >> "%CRON_LOG%"

rem Set Python executable (prefer project venv)
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

rem Execute backup command and append output to cron.log
"%PYTHON_EXE%" "%PROJECT_ROOT%\src\main.py" backup gdrive: onedrive: >> "%CRON_LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo [TASK END] %DATE% %TIME% - Backup finished with exit code %EXIT_CODE% >> "%CRON_LOG%"
echo ========================================================== >> "%CRON_LOG%"

exit /b %EXIT_CODE%
