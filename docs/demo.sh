#!/usr/bin/env bash
# ==============================================================================
# Rclone Cloud Manager - Interactive Demo Recording Script
# Automates all CLI commands for screen/video demonstrations & screenshots.
# Works out-of-the-box using local demo folders (no cloud credentials required).
# ==============================================================================

set -euo pipefail

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Setup Python binary
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python.exe"
else
    PYTHON="python3"
fi

# Visual formatting helper
pause() {
    echo ""
    echo -e "\033[1;33m[Press ENTER to proceed to the next demo step...]\033[0m"
    read -r
}

clear_screen() {
    clear 2>/dev/null || cls 2>/dev/null || true
}

clear_screen
echo "================================================================="
echo "        🎬 Rclone Cloud Manager - Live Feature Demo 🎬           "
echo "================================================================="
echo "This script demonstrates the full workflow for video/screenshot capture."
pause

# ----------------------------------------------------------------------
# 1. CLI Help & Command Discovery
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 1: CLI Overview & Available Subcommands"
echo "$ ${PYTHON} src/main.py --help"
echo ""
"${PYTHON}" src/main.py --help
pause

# ----------------------------------------------------------------------
# 2. List Configured Remotes
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 2: Listing Configured Cloud Remotes"
echo "$ ${PYTHON} src/main.py list-remotes"
echo ""
"${PYTHON}" src/main.py list-remotes
pause

# ----------------------------------------------------------------------
# 3. Prepare Sample Data for Live Sync Demonstration
# ----------------------------------------------------------------------
DEMO_SRC="${PROJECT_ROOT}/demo_data/source"
DEMO_DST="${PROJECT_ROOT}/demo_data/destination"

mkdir -p "${DEMO_SRC}" "${DEMO_DST}"
echo "Financial Report 2026 - Q3" > "${DEMO_SRC}/report_q3.docx"
echo "Database dump payload" > "${DEMO_SRC}/database_backup.sql"
echo "Photo raw asset 001" > "${DEMO_SRC}/photo_01.raw"

# ----------------------------------------------------------------------
# 4. Synchronize Directories (Live Sync with Progress)
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 3: Multi-Cloud / Local Directory Sync"
echo "$ ${PYTHON} src/main.py sync demo_data/source demo_data/destination"
echo ""
"${PYTHON}" src/main.py sync demo_data/source demo_data/destination
pause

# ----------------------------------------------------------------------
# 5. Timestamped Backup Execution
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 4: Timestamped Backup (Copy Mode)"
echo "Adding updated files..."
echo "New revision asset" > "${DEMO_SRC}/update_patch.tar.gz"
echo "$ ${PYTHON} src/main.py backup demo_data/source demo_data/destination"
echo ""
"${PYTHON}" src/main.py backup demo_data/source demo_data/destination
pause

# ----------------------------------------------------------------------
# 6. Check Real-Time Execution Status & Logs
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 5: Real-Time Execution Status & Audit Log"
echo "$ ${PYTHON} src/main.py status"
echo ""
"${PYTHON}" src/main.py status
pause

# ----------------------------------------------------------------------
# 7. View Daily Log File
# ----------------------------------------------------------------------
clear_screen
echo ">>> STEP 6: Inspection of Daily Rotating Log File"
LATEST_LOG=$(ls -t logs/rclone_*.log 2>/dev/null | head -n 1 || true)
if [ -n "${LATEST_LOG}" ]; then
    echo "Displaying latest lines from: ${LATEST_LOG}"
    echo "--------------------------------------------------------"
    tail -n 25 "${LATEST_LOG}"
else
    echo "No log files found."
fi

echo ""
echo "================================================================="
echo "🎉 Live Demo Completed Successfully! 🎉"
echo "You can now capture screenshots or finalize video recordings."
echo "================================================================="
