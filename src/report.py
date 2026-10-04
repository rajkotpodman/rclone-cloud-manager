"""
Weekly Executive Auto-Reporting Module.
Generates comprehensive HTML reports summarizing data volume,
transfers, failure counts, and time saved, and sends them via email.
"""

from __future__ import annotations

import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

from jinja2 import Template

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

from src.monitor import load_metrics  # noqa: E402


def generate_weekly_report_html(metrics: Dict[str, Any]) -> str:
    """Renders a modern, responsive HTML report for executive review."""
    template_path = PROJECT_ROOT / "templates" / "report_email.html"
    template_str = template_path.read_text(encoding="utf-8")
    tmpl = Template(template_str)

    now_str = datetime.now().strftime("%B %d, %Y")
    total_files = metrics.get("total_files_transferred", 0)
    total_gb = metrics.get("total_data_gb", 0.0)
    failed_runs = metrics.get("failed_runs", 0)
    hours_saved = metrics.get("estimated_hours_saved", 0.0)
    successful_runs = metrics.get("successful_runs", 0)

    total_jobs = successful_runs + failed_runs
    success_rate = (
        round((successful_runs / total_jobs) * 100, 1) if total_jobs > 0 else 100.0
    )

    return tmpl.render(
        now_str=now_str,
        total_files=total_files,
        total_gb=total_gb,
        failed_runs=failed_runs,
        hours_saved=hours_saved,
        success_rate=success_rate,
    )


def save_report_to_disk(html_content: str) -> Path:
    """Saves the generated report into the reports/ folder."""
    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    report_file = reports_dir / f"weekly_report_{date_str}.html"
    report_file.write_text(html_content, encoding="utf-8")
    return report_file


def send_report_email(html_content: str) -> bool:
    """Dispatches the weekly report to the client via email."""
    smtp_email = os.getenv("SMTP_EMAIL", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    recipient = os.getenv("CLIENT_EMAIL", "").strip()
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not smtp_email or not smtp_pass or not recipient:
        print("[INFO] Report email skipped: SMTP credentials or CLIENT_EMAIL missing.")
        return False

    date_str = datetime.now().strftime("%B %d, %Y")
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Cloud Automation Reports <{smtp_email}>"
    msg["To"] = recipient
    msg["Subject"] = (
        f"[REPORT] Weekly Cloud Backup & Sync Performance Report ({date_str})"
    )
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_email, smtp_pass)
            server.send_message(msg)
            print(f"[EMAIL] Weekly report successfully dispatched to {recipient}")
            return True
    except Exception as e:
        print(f"[WARN] Failed to deliver weekly report email: {e}")
        return False


def run_weekly_report() -> None:
    """Main execution function for weekly reporting."""
    print("[REPORT] Generating weekly executive cloud automation report...")
    metrics = load_metrics()
    html = generate_weekly_report_html(metrics)
    saved_path = save_report_to_disk(html)
    print(f"[REPORT] Report saved to: {saved_path}")
    send_report_email(html)


if __name__ == "__main__":
    run_weekly_report()
