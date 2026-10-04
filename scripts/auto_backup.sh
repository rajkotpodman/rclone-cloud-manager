#!/usr/bin/env bash
# ==============================================================================
# Rclone Cloud Manager - Daily Automated Backup Script (Linux / macOS)
# Cron Schedule: 0 2 * * * (Runs every day at 02:00 AM)
# ==============================================================================

set -euo pipefail

# Determine script and project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure logs directory exists
LOGS_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOGS_DIR}"
CRON_LOG="${LOGS_DIR}/cron.log"

echo "==========================================================" >> "${CRON_LOG}"
echo "[CRON START] $(date '+%Y-%m-%d %H:%M:%S') - Starting automated daily backup" >> "${CRON_LOG}"

# Use virtual environment python if present, else fallback to python3/python
if [ -f "${PROJECT_ROOT}/venv/bin/python" ]; then
    PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
elif [ -f "${PROJECT_ROOT}/venv/Scripts/python.exe" ]; then
    PYTHON_BIN="${PROJECT_ROOT}/venv/Scripts/python.exe"
else
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

# Execute backup command and append output to cron.log
cd "${PROJECT_ROOT}"
"${PYTHON_BIN}" src/main.py backup gdrive: onedrive: >> "${CRON_LOG}" 2>&1
EXIT_CODE=$?

echo "[CRON END] $(date '+%Y-%m-%d %H:%M:%S') - Backup finished with exit code ${EXIT_CODE}" >> "${CRON_LOG}"
echo "==========================================================" >> "${CRON_LOG}"

exit ${EXIT_CODE}
