"""
Unit tests for Advanced Use Cases and Monitoring.
"""

from unittest.mock import patch

from src.advanced import (
    bandwidth_sync,
    bisync_folders,
    crypt_backup,
    failover_chain,
    mount_remote,
    versioned_sync,
)
from src.monitor import get_default_metrics


@patch("src.advanced.run_rclone_command", return_value=0)
def test_crypt_backup(mock_run):
    code = crypt_backup("/data/finance", "secret-drive:vault")
    assert code == 0
    mock_run.assert_called_once()
    assert "copy" in mock_run.call_args[0][0]


@patch("src.advanced.run_rclone_command", return_value=0)
def test_mount_remote(mock_run):
    code = mount_remote("gdrive:", "/mnt/gdrive")
    assert code == 0
    mock_run.assert_called_once()
    assert "mount" in mock_run.call_args[0][0]


@patch("src.advanced.run_rclone_command", return_value=0)
def test_bisync_folders(mock_run):
    code = bisync_folders("gdrive:shared", "onedrive:shared", resync=True)
    assert code == 0
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert "bisync" in called_args
    assert "--resync" in called_args


@patch("src.advanced.run_rclone_command", return_value=0)
def test_bandwidth_sync(mock_run):
    code = bandwidth_sync("src:", "dst:", bwlimit="09:00,10M 18:00,off")
    assert code == 0
    mock_run.assert_called_once()
    assert "--bwlimit=09:00,10M 18:00,off" in mock_run.call_args[0][0]


@patch("src.advanced.run_rclone_command", return_value=0)
def test_versioned_sync(mock_run):
    code = versioned_sync("src:", "dst:", custom_timestamp="20261004_120000")
    assert code == 0
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert "--backup-dir=dst:_versions/20261004_120000" in called_args


@patch("src.advanced.run_rclone_command", side_effect=[0, 0])
def test_failover_chain_success(mock_run):
    code = failover_chain("gdrive:", "s3:", "b2:")
    assert code == 0
    assert mock_run.call_count == 2


def test_monitor_default_metrics():
    metrics = get_default_metrics()
    assert metrics["total_checks"] == 0
    assert metrics["failed_runs"] == 0
    assert isinstance(metrics["recent_events"], list)
