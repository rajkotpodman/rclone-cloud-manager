"""
Advanced Rclone Use Cases Module.
Implements:
1. Encrypted backup (rclone crypt)
2. Cloud drive mounting (rclone mount)
3. Bidirectional folder sync (rclone bisync)
4. Bandwidth rate-limited sync (--bwlimit)
5. Timestamped deduplication and versioning (--backup-dir)
6. Multi-cloud failover replication chain (Primary -> Secondary -> Tertiary)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import run_rclone_command  # noqa: E402


def crypt_backup(src: str, dst: str) -> int:
    """Executes an encrypted backup to an rclone crypt overlay remote."""
    print(f"[CRYPT] Initiating Zero-Knowledge Encrypted Backup: {src} -> {dst}")
    args = ["copy", src, dst, "--fast-list", "--transfers=8", "--buffer-size=64M", "-v"]
    return run_rclone_command(
        args,
        command_label="crypt-backup",
        extra_log_info=f"Encrypted payload copy: {src} -> {dst}",
    )


def mount_remote(remote: str, mountpoint: str, vfs_cache_mode: str = "full") -> int:
    """Mounts a cloud remote to a local directory or drive letter."""
    print(
        f"[MOUNT] Mounting Cloud Storage: {remote} at {mountpoint} (VFS: {vfs_cache_mode})"
    )
    args = [
        "mount",
        remote,
        mountpoint,
        f"--vfs-cache-mode={vfs_cache_mode}",
        "--vfs-cache-max-size=20G",
        "--vfs-cache-max-age=24h",
        "-v",
    ]
    return run_rclone_command(
        args,
        command_label="mount-remote",
        extra_log_info=f"Mounted {remote} to {mountpoint}",
    )


def bisync_folders(path1: str, path2: str, resync: bool = False) -> int:
    """Performs bidirectional synchronization between two folder trees."""
    print(
        f"[BISYNC] Executing Bidirectional Sync: {path1} <==> {path2} (Resync: {resync})"
    )
    args = ["bisync", path1, path2, "-v"]
    if resync:
        args.append("--resync")
    return run_rclone_command(
        args,
        command_label="bisync",
        extra_log_info=f"Bidirectional sync between {path1} and {path2}",
    )


def bandwidth_sync(src: str, dst: str, bwlimit: str = "09:00,2M 18:00,off") -> int:
    """Synchronizes folders respecting scheduled bandwidth limits."""
    print(
        f"[THROTTLE] Running Bandwidth-Throttled Sync: {src} -> {dst} (Limit: {bwlimit})"
    )
    args = ["sync", src, dst, f"--bwlimit={bwlimit}", "--tpslimit=10", "-v"]
    return run_rclone_command(
        args,
        command_label="bandwidth-sync",
        extra_log_info=f"Rate-limited sync: {src} -> {dst} with limit {bwlimit}",
    )


def versioned_sync(src: str, dst: str, custom_timestamp: Optional[str] = None) -> int:
    """Synchronizes directories while archiving modified/deleted files with timestamps."""
    ts = custom_timestamp or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_target = f"{dst.rstrip('/')}_versions/{ts}"
    print(f"[VERSION] Running Versioned Sync: {src} -> {dst}")
    print(f"[ARCHIVE] Prior revisions will be archived to: {backup_target}")

    args = [
        "sync",
        src,
        dst,
        f"--backup-dir={backup_target}",
        "--suffix=_old",
        "-v",
    ]
    return run_rclone_command(
        args,
        command_label="versioned-sync",
        extra_log_info=f"Versioned sync: {src} -> {dst} (Archive: {backup_target})",
    )


def failover_chain(primary: str, secondary: str, tertiary: str) -> int:
    """Executes a cascaded multi-cloud replication chain (Primary -> Secondary -> Tertiary)."""
    print("[FAILOVER] Initiating Multi-Cloud Failover Chain:")
    print(f"   Stage 1: {primary} -> {secondary}")
    print(f"   Stage 2: {secondary} -> {tertiary}")

    code1 = run_rclone_command(
        ["copy", primary, secondary, "--fast-list", "-v"],
        command_label="failover-stage1",
        extra_log_info=f"Stage 1 Replication: {primary} -> {secondary}",
    )
    if code1 != 0:
        print(
            f"[FAILOVER ERROR] Stage 1 Failed with exit code {code1}. Aborting chain."
        )
        return code1

    code2 = run_rclone_command(
        ["copy", secondary, tertiary, "--fast-list", "-v"],
        command_label="failover-stage2",
        extra_log_info=f"Stage 2 Replication: {secondary} -> {tertiary}",
    )
    if code2 == 0:
        print("[FAILOVER SUCCESS] Multi-Cloud Failover Chain Successfully Completed.")
    return code2
