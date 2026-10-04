"""
Unit tests for AI Smart Sync, Anomaly Detection, and Transfer Time Prediction.
"""

from unittest.mock import patch

from src.ai_sync import (
    auto_retry_logic,
    detect_anomalies,
    predict_transfer_time,
    smart_schedule,
)
from src.train_model import train_models


def test_smart_schedule():
    """Verify smart_schedule analyzes telemetry and produces complete recommendation."""
    sched = smart_schedule()
    assert "recommended_hour" in sched
    assert 0 <= sched["recommended_hour"] <= 23
    assert "recommended_time" in sched
    assert "recommended_day" in sched
    assert "daily_cron" in sched
    assert "weekly_cron" in sched
    assert "estimated_offpeak_savings" in sched
    assert "reasoning" in sched
    assert sched["daily_cron"].startswith(f"0 {sched['recommended_hour']}")


def test_detect_anomalies_normal():
    """Test that normal, baseline transfer metrics are not flagged as anomalies."""
    result = detect_anomalies(
        file_count=50, total_size_mb=150.0, duration=8.0, deletions=0
    )
    assert result["is_anomaly"] is False
    assert len(result["reasons"]) == 0
    assert result["file_count"] == 50


def test_detect_anomalies_flagged():
    """Test that mass deletions and volume spikes are flagged and trigger alert logic."""
    with patch("src.ai_sync.send_telegram_alert") as mock_telegram:
        mock_telegram.return_value = True
        result = detect_anomalies(
            file_count=15000,
            total_size_mb=20480.0,  # 20 GB
            duration=12.0,
            deletions=600,
        )
        assert result["is_anomaly"] is True
        assert len(result["reasons"]) > 0
        assert any("spike" in r.lower() for r in result["reasons"])
        assert any("deletion" in r.lower() for r in result["reasons"])
        mock_telegram.assert_called_once()


def test_predict_transfer_time():
    """Test that transfer duration prediction produces positive, realistic values."""
    time_small = predict_transfer_time(file_count=10, total_size_mb=25.0)
    time_large = predict_transfer_time(file_count=500, total_size_mb=5000.0)

    assert isinstance(time_small, float)
    assert isinstance(time_large, float)
    assert time_small > 0
    assert time_large > time_small


def test_auto_retry_logic():
    """Test exponential backoff increases delay with jitter."""
    delay_1 = auto_retry_logic(1)
    delay_2 = auto_retry_logic(2)
    delay_3 = auto_retry_logic(3)

    assert 1.0 <= delay_1 <= 4.0
    assert delay_2 > delay_1
    assert delay_3 > delay_2

    # Test max delay cap
    delay_max = auto_retry_logic(10, max_delay=30.0)
    assert delay_max <= 32.0


def test_train_models(tmp_path):
    """Test model training and artifact persistence."""
    fake_logs = tmp_path / "logs"
    fake_logs.mkdir()
    sample_entry = (
        "[2026-10-04 12:00:00] [INFO] --- "
        "[2026-10-04 12:00:00] COMMAND: SYNC | STATUS: SUCCESS ---\n"
        "Transferred: 50.0 MiB / 50.0 MiB, 100%, 10 MiB/s, ETA 0s\n"
        "Transferred: 25 / 25, 100%\n"
        "Elapsed time: 5.0s\n"
        "Deleted: 0\n"
        "------------------------------------------------------------\n"
    )
    (fake_logs / "test.log").write_text(sample_entry, encoding="utf-8")

    iso, reg, df = train_models(logs_dir=fake_logs)
    assert iso is not None
    assert reg is not None
    assert len(df) > 0
