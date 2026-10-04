# Rclone Cloud Manager - Documentation & User Guide

Welcome to the comprehensive documentation for **Rclone Cloud Manager**.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quickstart & Installation](#quickstart--installation)
3. [Configuring Cloud Remotes](#configuring-cloud-remotes)
   - [Google Drive](#google-drive)
   - [Microsoft OneDrive](#microsoft-onedrive)
   - [Amazon S3 & S3-Compatible](#amazon-s3--s3-compatible)
4. [CLI Usage & Commands](#cli-usage--commands)
5. [Automated Scheduling](#automated-scheduling)
   - [Linux / macOS (Cron)](#linux--macos-cron)
   - [Windows (Task Scheduler)](#windows-task-scheduler)
6. [Logging & Auditing](#logging--auditing)
7. [Running Tests](#running-tests)

---

## Architecture Overview

```text
rclone-cloud-manager/
├── config/
│   ├── rclone.conf           <- Local credentials (ignored by git)
│   └── rclone.conf.example   <- Sample configuration template
├── logs/
│   ├── cron.log              <- Scheduled task stdout/stderr
│   └── rclone_YYYYMMDD.log   <- Daily rotating detailed command logs
├── scripts/
│   ├── auto_backup.sh        <- Daily 2 AM cron wrapper (Linux/macOS)
│   ├── auto_backup.bat       <- Daily 2 AM Task Scheduler script (Windows)
│   └── sync_all.sh           <- Batch synchronization script
├── src/
│   ├── __init__.py           <- Package metadata
│   ├── logger.py             <- Daily file logging & status parser
│   └── main.py               <- CLI interface (argparse + colorama)
└── tests/
    ├── test_basic.py         <- Basic package tests
    ├── test_cli.py           <- CLI & error handling unit tests
    └── test_logger.py        <- Logger & file rotation tests
```

---

## Quickstart & Installation

1. **Activate the virtual environment**:
   - Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Linux / macOS:
     ```bash
     source venv/bin/activate
     ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify rclone is accessible**:
   ```bash
   rclone version
   ```

---

## Configuring Cloud Remotes

You can configure remotes interactively using `rclone config` or by editing `config/rclone.conf` based on [config/rclone.conf.example](file:///e:/rclone%20project/rclone-cloud-manager/config/rclone.conf.example).

### Google Drive
Run:
```bash
rclone config
```
1. Type `n` for new remote, name it `gdrive`.
2. Choose storage type `drive`.
3. Leave client_id/secret blank for default or provide your own Google Cloud Console credentials.
4. Set scope to `1` (Full access).
5. Authorize in browser and save.

### Microsoft OneDrive
1. Run `rclone config`, name it `onedrive`.
2. Choose storage type `onedrive`.
3. Complete web authorization and choose `1` (OneDrive Personal/Business).

### Amazon S3 & S3-Compatible
Example stanza in `config/rclone.conf`:
```ini
[s3-backup]
type = s3
provider = AWS
access_key_id = YOUR_ACCESS_KEY
secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

---

## CLI Usage & Commands

Run all commands through the CLI:

### 1. List Remotes
```bash
python src/main.py list-remotes
```
Prints all configured cloud endpoints.

### 2. Synchronize Cloud Folders (`rclone sync`)
```bash
python src/main.py sync gdrive:documents onedrive:backup/documents
```
*Note: `sync` ensures destination matches source exactly (deletes extra files on destination).*

### 3. Backup Cloud Folders (`rclone copy`)
```bash
python src/main.py backup gdrive:photos s3-backup:vault/photos
```
*Note: `backup` performs `rclone copy` (does not delete existing destination files) and attaches a start timestamp.*

### 4. Check Last Run Status
```bash
python src/main.py status
```
Reads and outputs the most recent command execution, exit code, and any errors recorded in `logs/`.

---

## Automated Scheduling

### Linux / macOS (Cron)
Schedule daily at 02:00 AM:
```bash
0 2 * * * /path/to/rclone-cloud-manager/scripts/auto_backup.sh
```

### Windows (Task Scheduler)
Register via command line:
```cmd
schtasks /create /tn "RcloneDailyBackup" /tr "\"E:\rclone project\rclone-cloud-manager\scripts\auto_backup.bat\"" /sc daily /st 02:00 /f
```

---

## Logging & Auditing

- **Daily Log**: Every command executed via `main.py` writes to `logs/rclone_YYYYMMDD.log` with timestamp, stdout, and stderr.
- **Cron Log**: Automated runs append their output and exit codes to `logs/cron.log`.
- Both log files and any `.conf` files are strictly excluded in [.gitignore](file:///e:/rclone%20project/rclone-cloud-manager/.gitignore).

---

## Running Tests

Run the test suite with pytest:
```bash
pytest -v
```
All unit tests should pass with 100% green output.
