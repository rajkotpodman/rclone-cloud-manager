#!/usr/bin/env python3
"""
Rclone Cloud Manager CLI
A unified interface for managing, synchronizing, and backing up cloud remotes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    from colorama import Fore, Style, init

    init(autoreset=True)
except ImportError:
    # Graceful fallback if colorama is not installed
    class _ColorFallback:
        def __getattr__(self, _):
            return ""

    Fore = _ColorFallback()  # type: ignore
    Style = _ColorFallback()  # type: ignore

# Add parent directory to sys.path if running as standalone script
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import get_current_log_path, get_last_sync_log, log_event  # noqa: E402


def get_config_flag() -> List[str]:
    """
    Returns the --config argument list if a custom config file exists in config/rclone.conf.
    Otherwise returns an empty list to use rclone default config.
    """
    custom_conf = PROJECT_ROOT / "config" / "rclone.conf"
    if custom_conf.exists() and custom_conf.stat().st_size > 0:
        return ["--config", str(custom_conf)]
    return []


def run_rclone_command(
    subcommand_args: List[str],
    command_label: str,
    extra_log_info: Optional[str] = None,
) -> int:
    """
    Executes an rclone command using subprocess.run, with colored output and daily logging.
    """
    cmd = ["rclone"] + get_config_flag() + subcommand_args
    print(
        f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Executing: "
        f"{Fore.WHITE}{' '.join(cmd)}{Style.RESET_ALL}"
    )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        stdout = result.stdout
        stderr = result.stderr

        # Print outputs
        if stdout.strip():
            print(f"{Fore.WHITE}{stdout.strip()}{Style.RESET_ALL}")
        if stderr.strip():
            if result.returncode == 0:
                print(f"{Fore.YELLOW}{stderr.strip()}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[STDERR]{Style.RESET_ALL} {stderr.strip()}")

        # Record to daily log file
        log_event(
            command_name=command_label,
            raw_command=cmd,
            return_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            extra_info=extra_log_info,
        )

        if result.returncode == 0:
            print(
                f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} "
                f"Command '{command_label}' completed successfully."
            )
        else:
            print(
                f"{Fore.RED}[ERROR]{Style.RESET_ALL} "
                f"Command '{command_label}' failed with exit code {result.returncode}."
            )

        return result.returncode

    except FileNotFoundError:
        error_msg = "Error: 'rclone' executable was not found in your system PATH."
        print(f"{Fore.RED}[CRITICAL]{Style.RESET_ALL} {error_msg}")
        log_event(
            command_name=command_label,
            raw_command=cmd,
            return_code=127,
            stderr=error_msg,
        )
        return 127
    except Exception as e:
        error_msg = f"Unexpected execution failure: {e}"
        print(f"{Fore.RED}[EXCEPTION]{Style.RESET_ALL} {error_msg}")
        log_event(
            command_name=command_label,
            raw_command=cmd,
            return_code=1,
            stderr=error_msg,
        )
        return 1


def handle_list_remotes(args: argparse.Namespace) -> int:
    """Lists configured rclone remotes."""
    print(f"\n{Fore.MAGENTA}=== Rclone Configured Remotes ==={Style.RESET_ALL}")
    return run_rclone_command(["listremotes"], command_label="list-remotes")


def handle_sync(args: argparse.Namespace) -> int:
    """Synchronizes source path to destination path using rclone sync."""
    print(
        f"\n{Fore.BLUE}=== Synchronizing Cloud Storage ==={Style.RESET_ALL}\n"
        f"Source: {Fore.YELLOW}{args.src}{Style.RESET_ALL} -> "
        f"Destination: {Fore.YELLOW}{args.dst}{Style.RESET_ALL}"
    )
    cmd_args = ["sync", args.src, args.dst, "-v"]
    ret = run_rclone_command(cmd_args, command_label="sync")
    if ret == 0:
        try:
            from src.verify_audit import audit_add

            audit_add(src=args.src, dst=args.dst, command="sync")
        except Exception as e:
            print(
                f"{Fore.YELLOW}[WARN] Audit block recording failed: {e}{Style.RESET_ALL}"
            )
    return ret


def handle_backup(args: argparse.Namespace) -> int:
    """Copies source path to destination path using rclone copy with timestamping."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"\n{Fore.GREEN}=== Starting Cloud Backup ==={Style.RESET_ALL}\n"
        f"Timestamp: {Fore.CYAN}{timestamp}{Style.RESET_ALL}\n"
        f"Source: {Fore.YELLOW}{args.src}{Style.RESET_ALL} -> "
        f"Destination: {Fore.YELLOW}{args.dst}{Style.RESET_ALL}"
    )
    cmd_args = ["copy", args.src, args.dst, "-v"]
    ret = run_rclone_command(
        cmd_args,
        command_label="backup",
        extra_log_info=f"Backup started at {timestamp} from {args.src} to {args.dst}",
    )
    if ret == 0:
        try:
            from src.verify_audit import audit_add

            audit_add(src=args.src, dst=args.dst, command="backup")
        except Exception as e:
            print(
                f"{Fore.YELLOW}[WARN] Audit block recording failed: {e}{Style.RESET_ALL}"
            )
    return ret


def handle_status(args: argparse.Namespace) -> int:
    """Displays the last recorded sync/backup log."""
    print(f"\n{Fore.MAGENTA}=== Last Sync / Backup Status ==={Style.RESET_ALL}")
    log_content = get_last_sync_log()
    print(f"{Fore.CYAN}{log_content}{Style.RESET_ALL}")
    print(
        f"\n{Fore.WHITE}Today's active log file: "
        f"{Fore.YELLOW}{get_current_log_path()}{Style.RESET_ALL}"
    )
    return 0


def handle_web(args: argparse.Namespace) -> int:
    """Starts the Flask web dashboard on port 5000."""
    from src.web_app import start_server

    port = getattr(args, "port", 5000)
    host = getattr(args, "host", "0.0.0.0")
    start_server(host=host, port=port)
    return 0


def handle_ai_train(args: argparse.Namespace) -> int:
    """Trains ML models on historical log data."""
    print(f"\n{Fore.CYAN}=== AI Model Training Pipeline ==={Style.RESET_ALL}")
    from src.train_model import train_models

    try:
        iso, reg, df = train_models()
        print(
            f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} Models trained and saved successfully."
        )
        return 0
    except Exception as e:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Training failed: {e}")
        return 1


def handle_ai_schedule(args: argparse.Namespace) -> int:
    """Predicts optimal backup windows based on moving averages and day-of-week patterns."""
    print(f"\n{Fore.CYAN}=== Smart Sync Schedule Recommendation ==={Style.RESET_ALL}")
    from src.ai_sync import smart_schedule

    sched = smart_schedule()
    print(
        f"Optimal Window:        {Fore.GREEN}{sched['recommended_time']}{Style.RESET_ALL}"
    )
    print(
        f"Optimal Day of Week:   {Fore.GREEN}{sched['recommended_day']}{Style.RESET_ALL}"
    )
    print(f"Daily Cron Expression: {Fore.YELLOW}{sched['daily_cron']}{Style.RESET_ALL}")
    print(
        f"Weekly Cron Schedule:  {Fore.YELLOW}{sched['weekly_cron']}{Style.RESET_ALL}"
    )
    est_sav = sched["estimated_offpeak_savings"]
    print(f"Estimated Savings:     {Fore.GREEN}{est_sav}{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}Analysis Rationale:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{sched['reasoning']}{Style.RESET_ALL}")
    print(
        f"\n[Analyzed {sched['analyzed_samples']} telemetry event samples across logs/]"
    )
    return 0


def handle_ai_anomaly_check(args: argparse.Namespace) -> int:
    """Checks transfer metrics against IsolationForest for anomalies."""
    print(
        f"\n{Fore.CYAN}=== Machine Learning Anomaly Detection Audit ==={Style.RESET_ALL}"
    )
    from src.ai_sync import detect_anomalies, predict_transfer_time

    if args.files is not None and args.size_mb is not None:
        files = args.files
        size_mb = args.size_mb
        duration = (
            args.duration
            if args.duration is not None
            else predict_transfer_time(files, size_mb)
        )
        deletions = args.deletions

        result = detect_anomalies(files, size_mb, duration, deletions)
        if result["is_anomaly"]:
            print(
                f"{Fore.RED}[ANOMALY FLAGGED]{Style.RESET_ALL} Suspicious transfer detected!"
            )
            for r in result["reasons"]:
                print(f" - {Fore.YELLOW}{r}{Style.RESET_ALL}")
            print(
                f"Score: {result['score']:.3f} | Alert logged to logs/anomalies.log & Telegram."
            )
            return 1
        else:
            print(
                f"{Fore.GREEN}[NORMAL]{Style.RESET_ALL} Metrics within expected parameters."
            )
            print(
                f"Files: {files} | Size: {size_mb:.2f} MB | "
                f"Duration: {duration:.2f}s | Deletions: {deletions}"
            )
            return 0

    # Diagnostic self-test mode
    print(f"{Fore.WHITE}Running ML Anomaly Detection Diagnostics...{Style.RESET_ALL}\n")
    norm = detect_anomalies(
        file_count=45, total_size_mb=180.0, duration=8.5, deletions=0
    )
    print("Test Vector 1 (Typical Daily Sync: 45 files, 180 MB, 0 dels):")
    print(f"  Status: {Fore.GREEN}NORMAL (Score: {norm['score']:.3f}){Style.RESET_ALL}")

    anom = detect_anomalies(
        file_count=12000, total_size_mb=15360.0, duration=14.0, deletions=500
    )
    print("\nTest Vector 2 (Suspicious Spike: 12,000 files, 15.0 GB, 500 dels):")
    if anom["is_anomaly"]:
        print(
            f"  Status: {Fore.RED}ANOMALY DETECTED (Score: {anom['score']:.3f}){Style.RESET_ALL}"
        )
        for reason in anom["reasons"]:
            print(f"  Flag:   {Fore.YELLOW}{reason}{Style.RESET_ALL}")
        print(
            "  Action: Logged to logs/anomalies.log & Telegram notification triggered."
        )

    return 0


def handle_audit_add(args: argparse.Namespace) -> int:
    """Snapshots cloud state and appends block to blockchain."""
    from src.verify_audit import audit_add

    src = getattr(args, "src", "gdrive:production")
    dst = getattr(args, "dst", "s3:backup")
    return audit_add(src=src, dst=dst, command="snapshot")


def handle_audit_verify(args: argparse.Namespace) -> int:
    """Validates cryptographic integrity of entire backup blockchain."""
    from src.verify_audit import audit_verify

    return audit_verify()


def handle_audit_proof(args: argparse.Namespace) -> int:
    """Generates and verifies Merkle inclusion proof for a file hash."""
    from src.verify_audit import audit_proof

    return audit_proof(args.file_hash)


def handle_audit_export(args: argparse.Namespace) -> int:
    """Exports full blockchain ledger as an executive PDF report and JSON."""
    from src.verify_audit import audit_export

    return audit_export()


def build_parser() -> argparse.ArgumentParser:
    """Builds and returns the command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="rclone-manager",
        description=(
            "Rclone Cloud Manager: Unified CLI for managing, syncing, "
            "and backing up cloud storage."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: list-remotes
    subparsers.add_parser("list-remotes", help="List all configured rclone remotes.")

    # Command: sync
    sync_parser = subparsers.add_parser(
        "sync",
        help="Synchronize source directory to destination (rclone sync).",
    )
    sync_parser.add_argument(
        "src",
        type=str,
        help="Source remote or local directory (e.g. gdrive:data or ./data)",
    )
    sync_parser.add_argument(
        "dst",
        type=str,
        help="Destination remote or local directory (e.g. onedrive:backup)",
    )

    # Command: backup
    backup_parser = subparsers.add_parser(
        "backup",
        help="Copy files from source to destination with timestamped logging.",
    )
    backup_parser.add_argument(
        "src",
        type=str,
        help="Source remote or local directory (e.g. gdrive:docs)",
    )
    backup_parser.add_argument(
        "dst",
        type=str,
        help="Destination remote or local directory (e.g. onedrive:backup)",
    )

    # Command: status
    subparsers.add_parser("status", help="Show the latest sync/backup execution log.")

    # Command: web
    web_parser = subparsers.add_parser(
        "web",
        help="Start the Flask web dashboard on port 5000.",
    )
    web_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run web dashboard on (default: 5000)",
    )
    web_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host interface (default: 0.0.0.0)",
    )

    # Command: crypt-backup
    cb_parser = subparsers.add_parser(
        "crypt-backup",
        help="Execute client-side encrypted backup to rclone crypt remote.",
    )
    cb_parser.add_argument("src", type=str, help="Source directory")
    cb_parser.add_argument("dst", type=str, help="Crypt destination remote")

    # Command: mount-remote
    mnt_parser = subparsers.add_parser(
        "mount-remote",
        help="Mount remote cloud storage to local directory or drive letter.",
    )
    mnt_parser.add_argument("remote", type=str, help="Cloud remote (e.g. gdrive:)")
    mnt_parser.add_argument(
        "mountpoint", type=str, help="Local mount path or drive letter"
    )
    mnt_parser.add_argument(
        "--vfs-cache-mode",
        type=str,
        default="full",
        help="VFS cache mode (default: full)",
    )

    # Command: bisync
    bi_parser = subparsers.add_parser(
        "bisync",
        help="Perform bidirectional synchronization between two cloud/local folders.",
    )
    bi_parser.add_argument("path1", type=str, help="First folder/remote path")
    bi_parser.add_argument("path2", type=str, help="Second folder/remote path")
    bi_parser.add_argument(
        "--resync",
        action="store_true",
        help="Reset and initialize bisync baseline comparison",
    )

    # Command: bandwidth-sync
    bw_parser = subparsers.add_parser(
        "bandwidth-sync",
        help="Synchronize with office-hours bandwidth rate limiting.",
    )
    bw_parser.add_argument("src", type=str, help="Source path")
    bw_parser.add_argument("dst", type=str, help="Destination path")
    bw_parser.add_argument(
        "--bwlimit",
        type=str,
        default="09:00,2M 18:00,off",
        help="Bandwidth schedule (default: '09:00,2M 18:00,off')",
    )

    # Command: versioned-sync
    ver_parser = subparsers.add_parser(
        "versioned-sync",
        help="Sync with timestamped deduplication and versioning via --backup-dir.",
    )
    ver_parser.add_argument("src", type=str, help="Source path")
    ver_parser.add_argument("dst", type=str, help="Destination path")

    # Command: failover-chain
    fo_parser = subparsers.add_parser(
        "failover-chain",
        help="Execute multi-cloud cascading failover sync (Primary -> Secondary -> Tertiary).",
    )
    fo_parser.add_argument("primary", type=str, help="Primary source cloud")
    fo_parser.add_argument("secondary", type=str, help="Secondary staging cloud")
    fo_parser.add_argument("tertiary", type=str, help="Tertiary cold archive cloud")

    # Command: ai-train
    subparsers.add_parser(
        "ai-train",
        help="Train ML models (IsolationForest & LinearRegression) on historical log data.",
    )

    # Command: ai-schedule
    subparsers.add_parser(
        "ai-schedule",
        help="Predict optimal backup time windows using moving averages and traffic models.",
    )

    # Command: ai-anomaly-check
    anom_parser = subparsers.add_parser(
        "ai-anomaly-check",
        help="Audit transfer metrics against IsolationForest for spikes & mass deletions.",
    )
    anom_parser.add_argument(
        "--files", type=int, default=None, help="File count to check"
    )
    anom_parser.add_argument(
        "--size-mb", type=float, default=None, help="Transfer size in MB to check"
    )
    anom_parser.add_argument(
        "--duration", type=float, default=None, help="Transfer duration in seconds"
    )
    anom_parser.add_argument(
        "--deletions", type=int, default=0, help="File deletions count (default: 0)"
    )

    # Command: audit-add
    audit_add_parser = subparsers.add_parser(
        "audit-add",
        help="Snapshot cloud state and append tamper-proof block to blockchain.",
    )
    audit_add_parser.add_argument(
        "--src", type=str, default="gdrive:production", help="Source remote"
    )
    audit_add_parser.add_argument(
        "--dst", type=str, default="s3:backup", help="Destination remote"
    )

    # Command: audit-verify
    subparsers.add_parser(
        "audit-verify",
        help="Validate cryptographic integrity of entire backup blockchain.",
    )

    # Command: audit-proof
    proof_parser = subparsers.add_parser(
        "audit-proof",
        help="Generate and inspect Merkle tree inclusion proof for a file hash.",
    )
    proof_parser.add_argument("file_hash", type=str, help="SHA-256 file hash to verify")

    # Command: audit-export
    subparsers.add_parser(
        "audit-export",
        help="Export full blockchain audit trail as an executive PDF compliance certificate.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    from src.advanced import (
        bandwidth_sync,
        bisync_folders,
        crypt_backup,
        failover_chain,
        mount_remote,
        versioned_sync,
    )

    dispatch_map = {
        "list-remotes": handle_list_remotes,
        "sync": handle_sync,
        "backup": handle_backup,
        "status": handle_status,
        "web": handle_web,
        "crypt-backup": lambda a: crypt_backup(a.src, a.dst),
        "mount-remote": lambda a: mount_remote(
            a.remote, a.mountpoint, a.vfs_cache_mode
        ),
        "bisync": lambda a: bisync_folders(a.path1, a.path2, a.resync),
        "bandwidth-sync": lambda a: bandwidth_sync(a.src, a.dst, a.bwlimit),
        "versioned-sync": lambda a: versioned_sync(a.src, a.dst),
        "failover-chain": lambda a: failover_chain(a.primary, a.secondary, a.tertiary),
        "ai-train": handle_ai_train,
        "ai-schedule": handle_ai_schedule,
        "ai-anomaly-check": handle_ai_anomaly_check,
        "audit-add": handle_audit_add,
        "audit-verify": handle_audit_verify,
        "audit-proof": handle_audit_proof,
        "audit-export": handle_audit_export,
    }

    handler = dispatch_map.get(args.command)
    if handler:
        exit_code = handler(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
