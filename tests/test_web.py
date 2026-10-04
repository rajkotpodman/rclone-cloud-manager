"""
Unit tests for the Flask Web Dashboard (src/web_app.py).
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from src.web_app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_status_unauthorized(client):
    """Test that accessing /status without API key returns 401."""
    with patch.dict(os.environ, {"API_KEY": "test-key-123"}):
        from src import web_app

        web_app.EXPECTED_API_KEY = "test-key-123"
        res = client.get("/status")
        assert res.status_code == 401
        data = res.get_json()
        assert data["error"] == "Unauthorized"


def test_status_authorized_with_header(client):
    """Test accessing /status with valid X-API-Key header."""
    from src import web_app

    web_app.EXPECTED_API_KEY = "test-key-123"
    res = client.get("/status", headers={"X-API-Key": "test-key-123"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"
    assert "remotes" in data


def test_dashboard_route(client):
    """Test that / renders HTML dashboard."""
    from src import web_app

    web_app.EXPECTED_API_KEY = "test-key-123"
    res = client.get("/?api_key=test-key-123")
    assert res.status_code == 200
    assert b"Rclone Cloud Manager" in res.data
    assert b"Configured Remotes" in res.data


def test_logs_route(client):
    """Test that /logs renders activity logs view."""
    from src import web_app

    web_app.EXPECTED_API_KEY = "test-key-123"
    res = client.get("/logs?api_key=test-key-123")
    assert res.status_code == 200
    assert b"System Activity Logs" in res.data


@patch("subprocess.run")
def test_sync_post_route(mock_subproc, client):
    """Test that POST /sync triggers rclone sync."""
    from src import web_app

    web_app.EXPECTED_API_KEY = "test-key-123"
    mock_subproc.return_value = MagicMock(returncode=0, stdout="Sync OK", stderr="")

    res = client.post(
        "/sync?api_key=test-key-123",
        data={"src": "gdrive:", "dst": "onedrive:"},
    )
    assert res.status_code == 200
    assert b"Sync completed successfully" in res.data
    assert mock_subproc.call_count >= 1
    first_call_cmd = mock_subproc.call_args_list[0][0][0]
    assert "sync" in first_call_cmd
    assert "gdrive:" in first_call_cmd
    assert "onedrive:" in first_call_cmd
