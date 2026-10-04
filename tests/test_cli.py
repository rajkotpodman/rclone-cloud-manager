"""
Unit tests for CLI argument parsing and command handlers in src/main.py.
"""

import subprocess
from unittest.mock import patch

from src.main import build_parser, run_rclone_command


def test_parser_list_remotes():
    parser = build_parser()
    args = parser.parse_args(["list-remotes"])
    assert args.command == "list-remotes"


def test_parser_sync():
    parser = build_parser()
    args = parser.parse_args(["sync", "gdrive:docs", "onedrive:backup"])
    assert args.command == "sync"
    assert args.src == "gdrive:docs"
    assert args.dst == "onedrive:backup"


def test_parser_backup():
    parser = build_parser()
    args = parser.parse_args(["backup", "gdrive:photos", "s3:vault"])
    assert args.command == "backup"
    assert args.src == "gdrive:photos"
    assert args.dst == "s3:vault"


def test_parser_status():
    parser = build_parser()
    args = parser.parse_args(["status"])
    assert args.command == "status"


@patch("src.main.subprocess.run")
def test_run_rclone_command_success(mock_subproc):
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "version"],
        returncode=0,
        stdout="rclone v1.75.1\n",
        stderr="",
    )

    exit_code = run_rclone_command(["version"], command_label="version")
    assert exit_code == 0
    mock_subproc.assert_called_once()


@patch("src.main.subprocess.run")
def test_run_rclone_command_failure(mock_subproc):
    mock_subproc.return_value = subprocess.CompletedProcess(
        args=["rclone", "copy", "a", "b"],
        returncode=1,
        stdout="",
        stderr="Failed to find remote",
    )

    exit_code = run_rclone_command(["copy", "a", "b"], command_label="backup")
    assert exit_code == 1


@patch("src.main.subprocess.run", side_effect=FileNotFoundError("rclone not found"))
def test_run_rclone_command_missing_executable(mock_subproc):
    exit_code = run_rclone_command(["listremotes"], command_label="list-remotes")
    assert exit_code == 127
