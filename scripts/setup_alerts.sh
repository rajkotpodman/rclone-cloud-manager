#!/usr/bin/env bash
# ==============================================================================
# Rclone Cloud Manager - Alerting & Monitoring Setup Script
# Prompts for Telegram / SMTP credentials and registers automated cron checks.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

echo "=========================================================="
echo "🔔 Rclone Cloud Manager - Monitoring & Alerting Setup 🔔"
echo "=========================================================="

# Create .env if missing
if [ ! -f "${ENV_FILE}" ]; then
    cp "${PROJECT_ROOT}/.env.example" "${ENV_FILE}"
    echo "✓ Initialized .env from template."
fi

echo ""
echo "Enter your Telegram Bot details (Leave blank to skip):"
read -r -p "Telegram Bot Token: " TG_TOKEN
read -r -p "Telegram Chat ID:   " TG_CHAT_ID

if [ -n "${TG_TOKEN}" ]; then
    sed -i.bak "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${TG_TOKEN}|" "${ENV_FILE}" 2>/dev/null || \
    sed -i "" "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${TG_TOKEN}|" "${ENV_FILE}"
fi

if [ -n "${TG_CHAT_ID}" ]; then
    sed -i.bak "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=${TG_CHAT_ID}|" "${ENV_FILE}" 2>/dev/null || \
    sed -i "" "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=${TG_CHAT_ID}|" "${ENV_FILE}"
fi

echo ""
echo "Enter Email Notification details (Leave blank to skip):"
read -r -p "SMTP Email (Sender): " SMTP_EMAIL
read -r -s -p "SMTP App Password:    " SMTP_PASS
echo ""
read -r -p "Client Email (Recipient): " CLIENT_EMAIL

if [ -n "${SMTP_EMAIL}" ]; then
    sed -i.bak "s|^SMTP_EMAIL=.*|SMTP_EMAIL=${SMTP_EMAIL}|" "${ENV_FILE}" 2>/dev/null || \
    sed -i "" "s|^SMTP_EMAIL=.*|SMTP_EMAIL=${SMTP_EMAIL}|" "${ENV_FILE}"
fi

if [ -n "${SMTP_PASS}" ]; then
    sed -i.bak "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${SMTP_PASS}|" "${ENV_FILE}" 2>/dev/null || \
    sed -i "" "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=${SMTP_PASS}|" "${ENV_FILE}"
fi

if [ -n "${CLIENT_EMAIL}" ]; then
    sed -i.bak "s|^CLIENT_EMAIL=.*|CLIENT_EMAIL=${CLIENT_EMAIL}|" "${ENV_FILE}" 2>/dev/null || \
    sed -i "" "s|^CLIENT_EMAIL=.*|CLIENT_EMAIL=${CLIENT_EMAIL}|" "${ENV_FILE}"
fi

# Clean backup file if created
rm -f "${ENV_FILE}.bak"

echo ""
echo "✓ Credentials saved to ${ENV_FILE}"

# Register Crontab Entries
PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
if [ ! -f "${PYTHON_BIN}" ]; then
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

MONITOR_CRON="0 * * * * cd ${PROJECT_ROOT} && ${PYTHON_BIN} src/monitor.py >> logs/cron.log 2>&1"
REPORT_CRON="0 9 * * 1 cd ${PROJECT_ROOT} && ${PYTHON_BIN} src/report.py >> logs/cron.log 2>&1"

echo ""
echo "Adding Cron Schedules:"
echo "1. Hourly Health & Alert Check: 0 * * * *"
echo "2. Weekly Executive Report:     0 9 * * 1 (Mondays at 9:00 AM)"

(crontab -l 2>/dev/null | grep -v "src/monitor.py" | grep -v "src/report.py" ; echo "${MONITOR_CRON}" ; echo "${REPORT_CRON}") | crontab -

echo ""
echo "=========================================================="
echo "🎉 Monitoring, Telegram alerts, and weekly reporting ready! 🎉"
echo "=========================================================="
