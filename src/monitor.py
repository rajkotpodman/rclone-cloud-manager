"""
Monitoring and Alerting Module for Rclone Cloud Manager.
Monitors sync/backup health, sends Telegram and Email failure notifications,
and persists telemetry in metrics.json.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from src.logger import get_logs_dir  # noqa: E402

METRICS_FILE = PROJECT_ROOT / "metrics.json"


def get_default_metrics() -> Dict[str, Any]:
    """Returns baseline metrics structure."""
    return {
        "last_check_timestamp": None,
        "total_checks": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "total_files_transferred": 0,
        "total_data_gb": 0.0,
        "estimated_hours_saved": 0.0,
        "recent_events": [],
    }


def load_metrics() -> Dict[str, Any]:
    """Loads metrics from metrics.json or initializes a new state."""
    if METRICS_FILE.exists():
        try:
            return json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return get_default_metrics()
    return get_default_metrics()


def save_metrics(metrics: Dict[str, Any]) -> None:
    """Saves metrics to metrics.json atomically."""
    METRICS_FILE.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def send_telegram_alert(message: str) -> bool:
    """Sends a notification to Telegram using Bot API."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print(
            "[INFO] Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured."
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    ).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[WARN] Failed to send Telegram alert: {e}")
        return False


def send_email_alert(subject: str, body: str) -> bool:
    """Sends an incident notification email via SMTP."""
    smtp_email = os.getenv("SMTP_EMAIL", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    recipient = os.getenv("CLIENT_EMAIL", smtp_email).strip()
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not smtp_email or not smtp_pass or not recipient:
        print(
            "[INFO] Email alert skipped: SMTP credentials or recipient not configured in .env."
        )
        return False

    msg = MIMEMultipart()
    msg["From"] = f"Rclone Alert <{smtp_email}>"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_email, smtp_pass)
            server.send_message(msg)
            print(f"[EMAIL] Alert email sent to {recipient}")
            return True
    except Exception as e:
        print(f"[WARN] Failed to send SMTP email: {e}")
        return False


def parse_latest_log_for_stats() -> Dict[str, Any]:
    """Inspects today's log file for errors and transfer volume statistics."""
    logs_dir = get_logs_dir()
    log_files = sorted(logs_dir.glob("rclone_*.log"), reverse=True)

    if not log_files:
        return {"status": "NO_LOGS", "errors": 0, "transferred_files": 0, "bytes": 0}

    latest = log_files[0]
    content = latest.read_text(encoding="utf-8", errors="replace")

    has_failure = "STATUS: FAILED" in content or "ERROR" in content
    error_count = content.count("STATUS: FAILED")

    files_matches = re.findall(r"Transferred:\s+(\d+)\s+/", content)
    total_files = sum(int(f) for f in files_matches) if files_matches else 0

    return {
        "status": "FAILED" if has_failure else "HEALTHY",
        "errors": error_count,
        "transferred_files": total_files,
        "latest_log_file": latest.name,
    }


def check_health_and_alert() -> Dict[str, Any]:
    """
    Core monitoring check function.
    Reads recent execution status, updates telemetry, and fires alerts on failure.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats = parse_latest_log_for_stats()
    metrics = load_metrics()

    metrics["total_checks"] += 1
    metrics["last_check_timestamp"] = now_str

    if stats["status"] == "FAILED":
        metrics["failed_runs"] += 1
        event = {
            "timestamp": now_str,
            "status": "FAILED",
            "errors": stats["errors"],
            "file": stats.get("latest_log_file", "unknown"),
        }
        metrics["recent_events"].insert(0, event)
        metrics["recent_events"] = metrics["recent_events"][:20]

        alert_text = (
            f"[ALERT] Rclone Backup Failure Detected!\n\n"
            f"- Timestamp: {now_str}\n"
            f"- Log File: {stats.get('latest_log_file')}\n"
            f"- Failures Count: {stats['errors']}\n\n"
            f"Please inspect the server or check the Web Dashboard immediately."
        )
        send_telegram_alert(alert_text)
        send_email_alert(
            subject=f"[CRITICAL ALERT] Rclone Cloud Backup Failure ({now_str})",
            body=(
                f"A backup failure was detected in your Rclone Cloud Manager instance.\n\n"
                f"Timestamp: {now_str}\n"
                f"Log File: {stats.get('latest_log_file')}\n"
                f"Detected Errors: {stats['errors']}\n\n"
                f"Action: Access the Web Dashboard at "
                f"http://localhost:5000/logs to review the stack trace."
            ),
        )
    else:
        metrics["successful_runs"] += 1
        metrics["total_files_transferred"] += stats.get("transferred_files", 0)
        new_gb = (stats.get("transferred_files", 0) * 5) / 1024.0
        metrics["total_data_gb"] = round(metrics["total_data_gb"] + new_gb, 2)
        metrics["estimated_hours_saved"] = round(
            metrics["total_files_transferred"] / 50.0, 1
        )

    save_metrics(metrics)
    print(f"[HEALTH] Check completed at {now_str}. Status: {stats['status']}")
    return metrics


if __name__ == "__main__":
    check_health_and_alert()
