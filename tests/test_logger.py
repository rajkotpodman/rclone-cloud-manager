"""
Unit tests for the logger module.
"""

from datetime import datetime
from pathlib import Path

from src.logger import get_current_log_path, get_last_sync_log, get_logs_dir, log_event


def test_get_logs_dir(tmp_path: Path):
    """Test that get_logs_dir returns a directory and creates it if needed."""
    logs_dir = get_logs_dir()
    assert logs_dir.exists()
    assert logs_dir.is_dir()


def test_get_current_log_path():
    """Test that current log file path follows the rclone_YYYYMMDD.log convention."""
    log_path = get_current_log_path()
    today_str = datetime.now().strftime("%Y%m%d")
    assert log_path.name == f"rclone_{today_str}.log"


def test_log_event_and_get_last_sync_log():
    """Test logging an event and retrieving it via get_last_sync_log."""
    test_cmd = ["rclone", "test", "dummy"]
    log_event(
        command_name="test-cmd",
        raw_command=test_cmd,
        return_code=0,
        stdout="Sample output test",
        stderr="",
        extra_info="Extra test info",
    )

    last_log = get_last_sync_log()
    assert "COMMAND: TEST-CMD" in last_log
    assert "STATUS: SUCCESS" in last_log
    assert "Sample output test" in last_log
    assert "Extra test info" in last_log
