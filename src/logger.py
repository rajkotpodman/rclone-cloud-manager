"""
Logging module for Rclone Cloud Manager.
Writes daily rotating log files to logs/rclone_YYYYMMDD.log.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_logs_dir() -> Path:
    """Returns the Path to the logs directory, creating it if necessary."""
    # Resolve relative to project root (parent of src)
    base_dir = Path(__file__).resolve().parent.parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_current_log_path() -> Path:
    """Returns the path for today's log file: logs/rclone_YYYYMMDD.log."""
    logs_dir = get_logs_dir()
    date_str = datetime.now().strftime("%Y%m%d")
    return logs_dir / f"rclone_{date_str}.log"


def setup_logger(name: str = "rclone_manager") -> logging.Logger:
    """Sets up and returns a standard file logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        log_path = get_current_log_path()
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_event(
    command_name: str,
    raw_command: list[str],
    return_code: int,
    stdout: str = "",
    stderr: str = "",
    extra_info: Optional[str] = None,
) -> None:
    """Logs the execution details of an rclone command to the daily log file."""
    logger = setup_logger()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if return_code == 0 else f"FAILED (exit code {return_code})"

    log_entry = [
        f"--- [{timestamp}] COMMAND: {command_name.upper()} | STATUS: {status} ---",
        f"Executed: {' '.join(raw_command)}",
    ]

    if extra_info:
        log_entry.append(f"Info: {extra_info}")
    if stdout.strip():
        log_entry.append(f"STDOUT:\n{stdout.strip()}")
    if stderr.strip():
        log_entry.append(f"STDERR:\n{stderr.strip()}")
    log_entry.append("-" * 60 + "\n")

    message = "\n".join(log_entry)
    if return_code == 0:
        logger.info(message)
    else:
        logger.error(message)


def get_last_sync_log() -> str:
    """Retrieves the most recent sync/backup log entries across all log files."""
    logs_dir = get_logs_dir()
    log_files = sorted(logs_dir.glob("rclone_*.log"), reverse=True)

    if not log_files:
        return "No log files found in logs/ directory."

    # Look through the latest log files for the last command section
    for log_path in log_files:
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                continue

            # Return the last 50 lines or latest block
            blocks = content.split("-" * 60)
            non_empty_blocks = [b.strip() for b in blocks if b.strip()]
            if non_empty_blocks:
                last_block = non_empty_blocks[-1]
                return f"[Source: {log_path.name}]\n{last_block}"
        except Exception as e:
            return f"Error reading log file {log_path.name}: {e}"

    return "No completed sync/backup events found in existing log files."
