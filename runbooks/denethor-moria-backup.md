# Denethor personal-file backup to Moria

**Read-only status update, 2026-11-16:** last-success receipt is Nov 14 16:00 UTC;
service currently failed and the 11:00 Eastern timer remains enabled. NAS identity
UNASPRO8/Moria and service ports are live. The configured SMB share is enumerated,
but direct share/repository access returns permission denied. Do not interpret
the Restic HTTP 500 as NAS offline or switch this job to Orthanc. No backup or
configuration change was executed. See [reconciliation](../docs/storage-source-of-truth-reconciliation.md).

Verified 2026-11-06: initial snapshot `93e4a953` contains 84,935 files and
23,656,792,016 source bytes, with 10,673,754,144 packed bytes added. Restic's full
`check --read-data` verified all 607 packs without errors. A real Hyprland settings
file and recovery canary were restored into a temporary directory, checked with
Restic `--verify`, and independently matched to the originals using SHA-256.
Follow-up snapshot `ee78705d` covers 91,255 files and 24,071,888,621 source bytes,
including WoW settings/addons. All 6,317 WoW files were restored and verified;
`Config.wtf` also matched the live original using SHA-256. Repository metadata
checks passed for all three retained snapshots. The daily timer is enabled;
its schedule was subsequently changed to 11:00 Eastern daily.
The NAS/replacement-machine recovery path has not been tested end-to-end.

## Scope and destination

- Source: `/home/murth`, including hidden preferences, SSH keys, projects,
  Obsidian and Steam userdata/Proton compatdata. Also includes
  `/mnt/data/World of Warcraft/_retail_/WTF` and `_retail_/Interface` for WoW
  settings and addons.
- Destination: Moria UNAS at `10.10.10.8`, SMB share `denethor_backup`, repository
  directory `denethor-restic`. This is separate from Orthanc's `moria` ZFS pool.
- Restic encrypts data and metadata locally; Rclone supplies SMB transport without
  a permanently mounted share or listening backup daemon.
- Excludes caches, Trash, installed game payloads, replaceable Mise runtimes and
  the backup's own credentials. Other `/mnt/data` content and system root are
  outside this backup.
- Root rollback remains Omarchy/Snapper's separate responsibility.

## Operation

The user timer is configured for daily 11:00 local time, with no random
delay and persistent catch-up when the user manager starts. It requires a
logged-in user; no linger or wake-from-suspend was enabled. A failed job triggers
a desktop notification. No automatic history deletion or pruning is configured.

```bash
denethor-backup snapshots
denethor-backup backup
denethor-backup check
denethor-backup check --read-data
denethor-backup restore-test
systemctl --user list-timers denethor-backup.timer
journalctl --user -u denethor-backup.service
```

Private credentials: `~/.config/denethor-backup/` (mode 700 directory, credentials
mode 600). Scripts: `~/.local/bin/denethor-backup` and
`~/.local/share/denethor-backup/`. Receipts: `~/.local/state/denethor-backup/`.
Never commit these credential files, raw logs or restored private files.

To pause scheduled backups, without deleting any stored versions:

```bash
systemctl --user disable --now denethor-backup.timer
```

## Recovery

Keep the encryption passphrase in a password manager accessible independently of
Denethor. The backup credentials directory is deliberately excluded from backups.

On a replacement Omarchy machine, install `restic` and `rclone` through
`omarchy pkg add restic rclone`. Use `rclone config` to create an SMB remote named
`moria-denethor`, host `10.10.10.8`, with an authorized NAS account. Enter credentials
only through the local hidden prompts. Then run:

```bash
restic -r rclone:moria-denethor:denethor_backup/denethor-restic snapshots
restic -r rclone:moria-denethor:denethor_backup/denethor-restic restore SNAPSHOT_ID \
  --target /path/to/new-empty-directory --verify
```

Restic prompts for the independently stored encryption passphrase. Restore to a
new directory, verify the files, then selectively copy them into the replacement
home. Do not restore over a live home blindly.

Live application databases can require the application stopped for a consistent
copy. This backup is not a disk image or a replacement for Omarchy rollback.
NAS snapshot/immutability and an off-site copy have not been configured or verified.

## Post-repair system rollback point

Omarchy root snapshot **22**, created 2026-11-06 at 21:53 Eastern (4.5.0-3),
captures the Bluetooth rule, RTKit and Flea installation. Its Limine menu entry
and referenced boot files were verified. Snapshots 18–22 are retained under the
existing five-snapshot policy, including pre-upgrade snapshot 20. No snapshot
boot or rollback was performed. Home files remain outside root snapshots.

Post-reboot acceptance on 2026-11-07: the missed 11:00 backup caught up at login
at 17:27 Eastern and completed successfully (snapshot `7682093d`, 91,314 files).
The timer remains enabled for daily 11:00 local time. Bluetooth firmware retries
did not recur. Audio required a follow-up startup adjustment documented in
Denethor's local repair notes; another reboot is needed to validate that change.
