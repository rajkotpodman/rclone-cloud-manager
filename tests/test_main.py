"""
Unit tests for CLI commands in src/main.py.
Uses unittest.mock to mock subprocess calls and avoid invoking real rclone.
"""

import argparse
import subprocess
from unittest.mock import patch

from src.logger import get_current_log_path
from src.main import (
    handle_backup,
    handle_list_remotes,
    handle_sync,
)


@patch("subprocess.run")
def test_list_remotes(mock_subproc, capsys):
    """
    1. test_list_remotes() -> mocks subprocess and checks output.
    """
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "listremotes"],
        returncode=0,
        stdout="gdrive:\nonedrive:\ns3:\n",
        stderr="",
    )

    args = argparse.Namespace(command="list-remotes")
    exit_code = handle_list_remotes(args)

    assert exit_code == 0
    mock_subproc.assert_called_once()
    # Check that the rclone command contains 'listremotes'
    called_cmd = mock_subproc.call_args[0][0]
    assert "listremotes" in called_cmd

    captured = capsys.readouterr()
    assert "gdrive:" in captured.out
    assert "onedrive:" in captured.out
    assert "s3:" in captured.out


@patch("subprocess.run")
def test_sync_command_builds_correct_args(mock_subproc):
    """
    2. test_sync_command_builds_correct_args() -> verifies proper argument list.
    """
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "sync", "gdrive:", "onedrive:", "-v"],
        returncode=0,
        stdout="Transferred: 10 / 10, 100%",
        stderr="",
    )

    args = argparse.Namespace(command="sync", src="gdrive:", dst="onedrive:")
    exit_code = handle_sync(args)

    assert exit_code == 0
    mock_subproc.assert_called_once()
    called_cmd = mock_subproc.call_args[0][0]

    assert called_cmd[0] == "rclone"
    assert "sync" in called_cmd
    assert "gdrive:" in called_cmd
    assert "onedrive:" in called_cmd
    assert "-v" in called_cmd


@patch("subprocess.run")
def test_backup_creates_log_file(mock_subproc):
    """
    3. test_backup_creates_log_file() -> verifies backup writes an entry to the daily log.
    """
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "copy", "gdrive:docs", "s3:backup", "-v"],
        returncode=0,
        stdout="Transferred 5 files successfully",
        stderr="",
    )

    args = argparse.Namespace(command="backup", src="gdrive:docs", dst="s3:backup")
    exit_code = handle_backup(args)

    assert exit_code == 0
    mock_subproc.assert_called_once()

    log_path = get_current_log_path()
    assert log_path.exists(), f"Expected log file {log_path} to exist"

    log_content = log_path.read_text(encoding="utf-8")
    assert "COMMAND: BACKUP" in log_content
    assert "gdrive:docs" in log_content
    assert "s3:backup" in log_content
    assert "STATUS: SUCCESS" in log_content


@patch("subprocess.run")
def test_invalid_remote_raises_error(mock_subproc, capsys):
    """
    4. test_invalid_remote_raises_error() -> asserts non-zero exit code on remote failure.
    """
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "sync", "invalid_remote:", "onedrive:", "-v"],
        returncode=1,
        stdout="",
        stderr="Failed to create file system for 'invalid_remote:': didn't find section",
    )

    args = argparse.Namespace(command="sync", src="invalid_remote:", dst="onedrive:")
    exit_code = handle_sync(args)

    assert exit_code != 0
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "failed with exit code 1" in captured.out or "STDERR" in captured.out
