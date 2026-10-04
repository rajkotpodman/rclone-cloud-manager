# Frequently Asked Questions (FAQ) for Clients

---

### Q1: Is our sensitive company data and credentials secure?
**Answer:** Yes, 100%. We employ zero-knowledge security principles. All cloud authentication uses official OAuth 2.0 tokens or IAM roles with least-privilege scoping (e.g., read-only access on the source drive). Your credentials are never stored on public servers or committed to version control; they remain strictly encrypted in your local or server environment.

---

### Q2: Will the automated backup slow down our company internet or team operations?
**Answer:** Not at all. We schedule intense backup routines during off-peak hours (such as 2:00 AM). In addition, we configure active bandwidth rate-limiting flags (`--bwlimit 10M` or custom schedules) to guarantee that daytime business internet usage is completely unaffected.

---

### Q3: What happens if a transfer gets interrupted by an internet disconnect or power failure?
**Answer:** The system is completely fault-tolerant and atomic. Rclone checks file hashes before and after every transfer. If a transfer is interrupted midway, Rclone simply resumes from where it left off on the next run without corrupting partially uploaded files or duplicating work.

---

### Q4: Does our company need to buy expensive third-party SaaS licenses?
**Answer:** No. Our solution is built entirely on open-source, battle-tested software (Python, Rclone, Linux/Windows native services) with zero monthly software licensing fees. You only pay for the raw cloud storage you actually consume on Google Drive, AWS, or Wasabi.

---

### Q5: Will there be any downtime during setup or migration?
**Answer:** Zero downtime. The automation scripts operate concurrently alongside your existing storage setups. Your team can continue editing Google Docs or uploading files while the synchronization engine silently mirrors data in the background.

---

### Q6: How do we know if last night's backup actually succeeded or failed?
**Answer:** Every single operation generates a daily rotating log file (`logs/rclone_YYYYMMDD.log`) detailing exact transfer times, file counts, and checksum validations. You can also view live statuses in the Web Dashboard or receive automated failure alerts directly in your team's Slack or Discord channel.

---

### Q7: What about cloud egress fees (e.g. AWS S3 download costs)?
**Answer:** We structure synchronization routines so data moves directly into archival tiers (like S3 Glacier Deep Archive at ~$0.00099 per GB/month). We configure transfer checkers so files are never re-downloaded or transferred unless they have genuinely been modified, keeping cloud API and transfer fees near zero.

---

### Q8: Can the system sync between different cloud providers (e.g. Google Drive to OneDrive or Dropbox to S3)?
**Answer:** Yes. Rclone natively supports over 70 cloud storage providers and protocols, including Google Drive, Microsoft OneDrive, Amazon S3, Wasabi, Backblaze B2, Dropbox, SFTP, and WebDAV. You can sync between any combination with a single command.

---

### Q9: Can non-technical team members monitor and trigger backups?
**Answer:** Absolutely. Along with the CLI commands, we provide a clean, browser-based Web Dashboard accessible on your local network where anyone on your team can verify remote statuses, inspect recent logs, and trigger manual syncs with a single click.

---

### Q10: What is included in the ₹40,000/month Pro Maintenance Retainer?
**Answer:** The retainer provides complete peace of mind:
- Continuous daily monitoring of backup integrity and audit logs.
- Automatic renewal of expiring OAuth tokens and API credentials.
- Cloud storage cost optimization and archival lifecycle audits.
- Same-day priority response for any data restoration or endpoint reconfiguration.
