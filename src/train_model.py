"""
Model Training Module for Rclone Cloud Manager.
Parses historical logs from logs/ directory, extracts transfer metrics,
and trains Machine Learning models (IsolationForest & LinearRegression).
Saves models to models/anomaly.pkl and models/transfer_time.pkl.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

LOGS_DIR = PROJECT_ROOT / "logs"
MODELS_DIR = PROJECT_ROOT / "models"
ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly.pkl"
TRANSFER_MODEL_PATH = MODELS_DIR / "transfer_time.pkl"


def parse_bytes_str(size_str: str, unit: str) -> float:
    """Converts a size and unit (KiB, MiB, GiB, etc.) to MegaBytes (MB)."""
    val = float(size_str.replace(",", ""))
    unit = unit.upper()
    if "G" in unit:
        return val * 1024.0
    elif "M" in unit:
        return val
    elif "K" in unit:
        return val / 1024.0
    elif "B" in unit:
        return val / (1024.0 * 1024.0)
    return val


def parse_duration_seconds(duration_str: str) -> float:
    """Parses duration strings like '1m23s', '45.2s', '2h10m' into seconds."""
    s = duration_str.strip().lower()
    total_sec = 0.0

    hours = re.search(r"(\d+(?:\.\d+)?)\s*h", s)
    if hours:
        total_sec += float(hours.group(1)) * 3600.0

    mins = re.search(r"(\d+(?:\.\d+)?)\s*m", s)
    if mins:
        total_sec += float(mins.group(1)) * 60.0

    secs = re.search(r"(\d+(?:\.\d+)?)\s*s", s)
    if secs:
        total_sec += float(secs.group(1))

    if total_sec == 0.0:
        try:
            return float(s)
        except ValueError:
            return 1.0

    return max(0.5, total_sec)


def extract_metrics_from_logs(logs_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Parses all log files in logs_dir and extracts structured records.
    Returns list of dicts with: timestamp, file_count, total_bytes (MB), duration, status
    """
    target_dir = logs_dir or LOGS_DIR
    records: List[Dict[str, Any]] = []

    if not target_dir.exists():
        return records

    log_files = sorted(target_dir.glob("*.log"))

    for log_path in log_files:
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        blocks = re.split(r"-{40,}", content)

        for block in blocks:
            b = block.strip()
            if not b:
                continue

            header_pat = (
                r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\].*?"
                r"COMMAND:\s*([\w-]+)\s*\|\s*STATUS:\s*([A-Za-z0-9_ ()]+)"
            )
            header_match = re.search(header_pat, b)
            timestamp = datetime.now()
            status_str = "SUCCESS"
            command_name = "SYNC"

            if header_match:
                try:
                    timestamp = datetime.strptime(
                        header_match.group(1), "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    pass
                command_name = header_match.group(2).upper()
                status_str = header_match.group(3).upper()

            is_success = 1 if "SUCCESS" in status_str else 0

            size_mb = 0.0
            file_count = 0
            duration_sec = 0.0
            deletions = 0

            trans_size_match = re.search(
                r"Transferred:\s+([\d.,]+)\s*([KMGTPE]?i?B)\s*/", b, re.IGNORECASE
            )
            if trans_size_match:
                size_mb = parse_bytes_str(
                    trans_size_match.group(1), trans_size_match.group(2)
                )

            trans_files_match = re.search(
                r"Transferred:\s+(\d+)\s*/\s*(\d+)", b, re.IGNORECASE
            )
            if trans_files_match:
                file_count = int(trans_files_match.group(2))

            elapsed_match = re.search(
                r"Elapsed time:\s*([0-9a-zA-Z.]+)", b, re.IGNORECASE
            )
            if elapsed_match:
                duration_sec = parse_duration_seconds(elapsed_match.group(1))

            deleted_match = re.search(r"Deleted:\s*(\d+)", b, re.IGNORECASE)
            if deleted_match:
                deletions = int(deleted_match.group(1))

            if "COMMAND" in b or size_mb > 0 or file_count > 0:
                if duration_sec <= 0:
                    duration_sec = 1.5 if is_success else 3.0

                records.append(
                    {
                        "timestamp": timestamp,
                        "command": command_name,
                        "file_count": max(1, file_count) if size_mb > 0 else file_count,
                        "total_bytes": round(size_mb, 2),
                        "duration": round(duration_sec, 2),
                        "status": is_success,
                        "deletions": deletions,
                    }
                )

    return records


def generate_synthetic_baseline(count: int = 120) -> List[Dict[str, Any]]:
    """Generates historical multi-cloud sync distribution data for baseline training."""
    np.random.seed(42)
    baseline: List[Dict[str, Any]] = []

    for i in range(count):
        files = int(np.random.gamma(shape=3.0, scale=35.0)) + 2
        avg_file_mb = np.random.uniform(0.5, 12.0)
        size_mb = round(files * avg_file_mb, 2)

        speed_mb_s = np.random.uniform(18.0, 42.0)
        overhead = files * 0.035
        duration = round(
            (size_mb / speed_mb_s) + overhead + np.random.normal(1.0, 0.3), 2
        )
        duration = max(0.8, duration)

        deletions = int(np.random.poisson(lam=0.4))

        day_offset = int(i / (count / 30))
        hour = np.random.choice(
            [2, 3, 4, 13, 15, 23], p=[0.35, 0.30, 0.15, 0.05, 0.05, 0.10]
        )
        ts = datetime(2026, 9, 1 + (day_offset % 28), hour, np.random.randint(0, 59))

        baseline.append(
            {
                "timestamp": ts,
                "command": "SYNC",
                "file_count": files,
                "total_bytes": size_mb,
                "duration": duration,
                "status": 1,
                "deletions": deletions,
            }
        )

    return baseline


def train_models(
    logs_dir: Optional[Path] = None, force_baseline: bool = False
) -> Tuple[IsolationForest, LinearRegression, pd.DataFrame]:
    """
    Trains IsolationForest for anomaly detection and LinearRegression for transfer time.
    Saves models to models/anomaly.pkl and models/transfer_time.pkl.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    real_records = extract_metrics_from_logs(logs_dir)

    transfer_records = [
        r
        for r in real_records
        if r.get("total_bytes", 0) > 0 or r.get("file_count", 0) > 1
    ]
    records = list(real_records)
    if len(transfer_records) < 20 or force_baseline:
        synthetic = generate_synthetic_baseline(count=120)
        records.extend(synthetic)

    df = pd.DataFrame(records)

    # 1. IsolationForest
    anomaly_features = ["file_count", "total_bytes", "duration", "deletions"]
    X_anomaly = df[anomaly_features].copy()

    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
    )
    iso_forest.fit(X_anomaly)

    # 2. Linear Regression
    reg_features = ["file_count", "total_bytes"]
    X_reg = df[reg_features].copy()
    y_reg = df["duration"].copy()

    lin_reg = LinearRegression()
    lin_reg.fit(X_reg, y_reg)

    # 3. Save models
    joblib.dump(iso_forest, ANOMALY_MODEL_PATH)
    joblib.dump(lin_reg, TRANSFER_MODEL_PATH)

    print(f"[AI-TRAIN] Trained IsolationForest on {len(df)} samples.")
    print(
        f"[AI-TRAIN] Trained LinearRegression (R^2: {lin_reg.score(X_reg, y_reg):.3f})."
    )
    print("[AI-TRAIN] Saved models to:")
    print(f"  - {ANOMALY_MODEL_PATH}")
    print(f"  - {TRANSFER_MODEL_PATH}")

    return iso_forest, lin_reg, df


def main() -> None:
    print("=" * 60)
    print(" Rclone Cloud Manager - ML Model Training Pipeline")
    print("=" * 60)
    train_models()


if __name__ == "__main__":
    main()
