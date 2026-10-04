"""
Flask Web Dashboard for Rclone Cloud Manager.
Provides web-based remote overview, sync triggering, log viewer, and healthcheck API.
"""

from __future__ import annotations

import os
import subprocess
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, List

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")

from src.logger import (  # noqa: E402
    get_current_log_path,
    get_last_sync_log,
    get_logs_dir,
    log_event,
)
from src.main import get_config_flag  # noqa: E402

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
)

EXPECTED_API_KEY = os.getenv("API_KEY", "").strip()

AUTH_ERROR_HTML = """<!DOCTYPE html>
<html><head><title>401 Unauthorized</title>
<style>
body { background: #0a0d14; color: #f8fafc; font-family: sans-serif;
       display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
.box { background: #171f32; padding: 32px; border-radius: 12px;
       border: 1px solid rgba(255,255,255,0.1); max-width: 400px; text-align: center; }
input { width: 100%; padding: 10px; margin: 12px 0; background: #0f1523;
        border: 1px solid #334155; color: #fff; border-radius: 6px; box-sizing: border-box; }
button { padding: 10px 20px; background: #38bdf8; color: #000;
         border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
</style>
</head><body>
<div class="box">
  <h2>🔒 Access Restricted</h2>
  <p>Please enter your API Key to access the Rclone Dashboard:</p>
  <form method="GET" action="{path}">
    <input type="password" name="api_key" placeholder="Enter API Key from .env" required />
    <button type="submit">Authenticate</button>
  </form>
</div>
</body></html>"""


def require_api_key(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to enforce API key authentication via Header, Query, or Form."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not EXPECTED_API_KEY:
            # If no API_KEY configured in environment, allow access
            return f(*args, **kwargs)

        # Check Header, Query parameter, or Form data
        key = (
            request.headers.get("X-API-Key")
            or request.args.get("api_key")
            or request.form.get("api_key")
        )

        if not key or key != EXPECTED_API_KEY:
            if request.path == "/status" or request.is_json:
                return (
                    jsonify(
                        {
                            "error": "Unauthorized",
                            "message": "Invalid or missing API key.",
                        }
                    ),
                    401,
                )
            return AUTH_ERROR_HTML.format(path=request.path), 401

        return f(*args, **kwargs)

    return decorated_function


def get_remotes_list() -> List[str]:
    """Retrieves list of remotes from rclone."""
    try:
        cmd = ["rclone"] + get_config_flag() + ["listremotes"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


@app.route("/", methods=["GET"])
@require_api_key
def dashboard():
    """Route / -> shows list of remotes and last sync status."""
    remotes = get_remotes_list()
    last_status = get_last_sync_log()
    api_key = request.args.get("api_key", EXPECTED_API_KEY)
    return render_template(
        "dashboard.html",
        remotes=remotes,
        last_status=last_status,
        api_key=api_key,
        default_src=remotes[0] if remotes else "gdrive:",
        default_dst=remotes[1] if len(remotes) > 1 else "onedrive:backup",
    )


@app.route("/sync", methods=["POST"])
@require_api_key
def trigger_sync():
    """Route /sync (POST) -> triggers a sync job."""
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    api_key = request.args.get("api_key", EXPECTED_API_KEY)

    if not src or not dst:
        return (
            render_template(
                "dashboard.html",
                remotes=get_remotes_list(),
                last_status=get_last_sync_log(),
                api_key=api_key,
                message="Both source and destination parameters are required.",
                success=False,
            ),
            400,
        )

    cmd = ["rclone"] + get_config_flag() + ["sync", src, dst, "-v"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log_event(
            command_name="web-sync",
            raw_command=cmd,
            return_code=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            extra_info=f"Triggered via Web UI: {src} -> {dst}",
        )
        success = res.returncode == 0
        message = (
            f"Sync completed successfully from {src} to {dst}."
            if success
            else f"Sync failed with exit code {res.returncode}. Check logs below."
        )
    except Exception as e:
        success = False
        message = f"Execution error: {e}"

    remotes = get_remotes_list()
    last_status = get_last_sync_log()
    return render_template(
        "dashboard.html",
        remotes=remotes,
        last_status=last_status,
        api_key=api_key,
        message=message,
        success=success,
        default_src=src,
        default_dst=dst,
    )


@app.route("/logs", methods=["GET"])
@require_api_key
def view_logs():
    """Route /logs -> shows last 50 lines from logs."""
    logs_dir = get_logs_dir()
    log_files = sorted(logs_dir.glob("rclone_*.log"), reverse=True)
    api_key = request.args.get("api_key", EXPECTED_API_KEY)

    if not log_files:
        content = "No log files found in logs/ directory."
        file_name = "None"
    else:
        latest = log_files[0]
        file_name = latest.name
        try:
            lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
            content = (
                "\n".join(lines[-50:]) if lines else "Log file is currently empty."
            )
        except Exception as e:
            content = f"Error reading log file: {e}"

    return render_template(
        "logs.html",
        log_content=content,
        log_file_name=file_name,
        api_key=api_key,
    )


@app.route("/status", methods=["GET"])
@require_api_key
def api_status():
    """Route /status -> JSON API for health check."""
    remotes = get_remotes_list()
    last_log = get_last_sync_log()

    return jsonify(
        {
            "status": "online",
            "service": "rclone-cloud-manager",
            "configured_remotes_count": len(remotes),
            "remotes": remotes,
            "active_log_file": str(get_current_log_path().name),
            "last_operation_summary": (
                last_log.splitlines()[0] if last_log else "No runs yet"
            ),
        }
    )


def start_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Starts the Flask development server."""
    print(f"🚀 Starting Rclone Web Dashboard on http://{host}:{port}")
    if EXPECTED_API_KEY:
        print("🔑 Protected by API Key authentication (configured in .env)")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    start_server(port=port)
