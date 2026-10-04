# Advanced Rclone Automation & Enterprise Use Cases

This guide documents 6 production-grade, real-world deployment patterns for **Rclone Cloud Manager**. Each scenario includes the technical background, full executable command, automated cron schedule, and common troubleshooting resolutions.

---

## 1. Zero-Knowledge Encrypted Backup (`rclone crypt`)

### Scenario Description
Before confidential files, databases, or financial records leave your infrastructure, they are encrypted locally using **AES-256 with Poly1305** using Rclone's native `crypt` overlay. The target cloud provider (e.g., Google Drive) only sees scrambled file names, encrypted folder hierarchies, and ciphertext payloads. Even if Google Drive is compromised, your raw data cannot be read without your encryption password and salt.

### Setup & Command
Configure a `crypt` remote wrapping an existing remote (e.g. `gdrive:vault_encrypted`):
```bash
# Direct CLI execution via Rclone Cloud Manager:
python src/main.py crypt-backup /data/finance secret-drive:finance_vault
```
*Equivalent raw Rclone command:*
```bash
rclone copy /data/finance secret-drive:finance_vault \
  --fast-list \
  --transfers=8 \
  --buffer-size=64M \
  -v
```

### Cron Schedule (Daily at 01:00 AM)
```text
0 1 * * * /path/to/venv/bin/python /path/to/src/main.py crypt-backup /data/finance secret-drive:finance_vault >> /path/to/logs/cron.log 2>&1
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `bad password or salt` | Incorrect crypt password or salt in `rclone.conf`. | Verify passwords match the original configuration. Store obfuscated passwords safely. |
| `failed to open source directory` | Permission denied on local source. | Ensure the cron runner user has read permissions (`chmod -R 750 /data/finance`). |

---

## 2. Mount Cloud Storage as a Local Drive (`rclone mount`)

### Scenario Description
Mount remote cloud buckets (Google Drive, AWS S3, Wasabi) as a native local filesystem path (`/mnt/cloud_drive` on Linux or `X:` on Windows). Applications, media editors, and automated scripts can read and write files directly as if they were on a local SSD without pre-downloading the entire bucket.

### Setup & Command
```bash
# Linux Mount Execution:
python src/main.py mount-remote gdrive: /mnt/gdrive --vfs-cache-mode full

# Windows Mount Execution:
python src/main.py mount-remote gdrive: X: --vfs-cache-mode full
```
*Equivalent raw Rclone command:*
```bash
rclone mount gdrive: /mnt/gdrive \
  --vfs-cache-mode full \
  --vfs-cache-max-size 20G \
  --vfs-cache-max-age 24h \
  --allow-other \
  --daemon
```

### Systemd Service (Linux Auto-Mount on Boot)
Save as `/etc/systemd/system/rclone-mount.service`:
```ini
[Unit]
Description=Rclone Cloud Storage Mount
After=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/rclone mount gdrive: /mnt/gdrive --vfs-cache-mode full --allow-other
ExecStop=/bin/fusermount -u /mnt/gdrive
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `Fatal error: failed to mount: mountpoint not empty` | Mount directory has existing files. | Empty the folder or pass `--allow-non-empty` flag. |
| `The service rclone has failed to start (WinFsp missing)` | Windows requires WinFsp driver for virtual disk mounting. | Install WinFsp via `winget install WinFsp.WinFsp` or download from official GitHub. |

---

## 3. Bidirectional Cloud Synchronization (`rclone bisync`)

### Scenario Description
Keep two folders (e.g. `gdrive:shared_docs` and `onedrive:shared_docs`) in continuous two-way synchronization. Edits, new additions, and deletions made on either provider are bi-directionally propagated while detecting and isolating conflicting file edits into conflict copies.

### Setup & Command
Initialize the baseline on the first run using `--resync`:
```bash
# First-time initialization:
python src/main.py bisync gdrive:shared_docs onedrive:shared_docs --resync

# Subsequent ongoing synchronization:
python src/main.py bisync gdrive:shared_docs onedrive:shared_docs
```

### Cron Schedule (Every 30 Minutes)
```text
*/30 * * * * /path/to/venv/bin/python /path/to/src/main.py bisync gdrive:shared_docs onedrive:shared_docs >> /path/to/logs/cron.log 2>&1
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `Bisync aborted: Prior lock file found` | Previous run crashed or did not finish cleanly. | Remove stale lock files in Rclone cache or pass `--force` after verifying no active jobs. |
| `Safety check failed: excessive deletions` | More than 50% of files were deleted or renamed. | Inspect source directory; if intentional, re-run with `--resync` to re-establish the baseline. |

---

## 4. Bandwidth-Limited Office Hours Backup (`--bwlimit`)

### Scenario Description
Running multi-gigabyte transfers during normal business hours can throttle company video conferences and VOIP calls. Using scheduled rate-limiting tables, Rclone caps transfer speeds at 2 MB/s during office hours (09:00 to 18:00) and unlocks full unthrottled gigabit speeds overnight.

### Setup & Command
```bash
python src/main.py bandwidth-sync /data/assets s3:company-backup/assets --bwlimit "09:00,2M 18:00,off"
```
*Equivalent raw Rclone command:*
```bash
rclone sync /data/assets s3:company-backup/assets \
  --bwlimit "09:00,2M 18:00,off" \
  --tpslimit 10 \
  -v
```

### Cron Schedule (Continuous Sync Job)
```text
0 9 * * 1-5 /path/to/venv/bin/python /path/to/src/main.py bandwidth-sync /data/assets s3:company-backup/assets --bwlimit "09:00,2M 18:00,off" >> /path/to/logs/cron.log 2>&1
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `Failed to parse --bwlimit` | Formatting syntax error in schedule string. | Format as `"HH:MM,Speed HH:MM,Speed"` using `M`, `k`, or `off` (e.g. `"08:00,10M 19:00,off"`). |
| `429 Too Many Requests` | API transaction rate limit hit regardless of bandwidth. | Pair `--bwlimit` with `--tpslimit 10` to pace API requests. |

---

## 5. Deduplication & Timestamped Versioning (`--backup-dir`)

### Scenario Description
To guard against accidental deletion or ransomware overwriting valid files, Rclone synchronizes your latest state while moving any modified or deleted older files into a dated timestamp archive folder (e.g. `s3:backup/versions/2026-10-04_1700/`). Your main directory always has the latest clean copy, while you retain an immutable historical archive.

### Setup & Command
```bash
python src/main.py versioned-sync /local/projects s3:vault/current
```
*Equivalent raw Rclone command:*
```bash
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
rclone sync /local/projects s3:vault/current \
  --backup-dir "s3:vault/versions/${TIMESTAMP}" \
  --suffix "_old" \
  -v
```

### Cron Schedule (Nightly at Midnight)
```text
0 0 * * * /path/to/venv/bin/python /path/to/src/main.py versioned-sync /local/projects s3:vault/current >> /path/to/logs/cron.log 2>&1
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `Can't move between different remotes in --backup-dir` | Target and backup-dir are on different cloud accounts. | `--backup-dir` must reside on the **same remote** as the destination bucket. |

---

## 6. Multi-Cloud Resilient Failover Chain (`Google Drive → AWS S3 → Backblaze B2`)

### Scenario Description
Enterprise high-availability disaster recovery: data is ingested into Google Drive, replicated to an Amazon S3 bucket, and then cascaded into Backblaze B2. If AWS or Google suffers an outage, the business can immediately restore from the secondary tertiary provider.

### Setup & Command
```bash
python src/main.py failover-chain gdrive:production s3:company-vault b2:company-archive
```
*Equivalent raw multi-step script:*
```bash
#!/usr/bin/env bash
set -euo pipefail

echo ">>> Stage 1: Google Drive to AWS S3"
rclone copy gdrive:production s3:company-vault --fast-list -v

echo ">>> Stage 2: AWS S3 to Backblaze B2"
rclone copy s3:company-vault b2:company-archive --fast-list -v

echo ">>> Multi-cloud replication chain verified."
```

### Cron Schedule (Daily at 03:00 AM)
```text
0 3 * * * /path/to/venv/bin/python /path/to/src/main.py failover-chain gdrive:production s3:company-vault b2:company-archive >> /path/to/logs/cron.log 2>&1
```

### Common Errors & Solutions
| Error | Cause | Fix |
| :--- | :--- | :--- |
| `S3 copy to B2 failed: High egress fee spike` | Using local intermediate machine as proxy. | Run Rclone on an EC2 instance in the same region, or verify direct server-to-server chunking. |
| `Failed to create file system for "b2:": key expired` | Backblaze Application Key has expired or lacks bucket write permissions. | Generate a fresh Backblaze Application Key with `readWrite` capabilities on the target bucket. |
