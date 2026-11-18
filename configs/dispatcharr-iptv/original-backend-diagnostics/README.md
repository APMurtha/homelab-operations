# Original backend diagnostics — offline candidate

This is an unapplied diagnostic-only delta for the original four-service release.
It is based on the three exact owner-approved 227122d file hashes, not the current
native-hardening lifecycle. Original files are retained byte-for-byte under
`original/`; proposed replacements are under `candidate/`.

`candidate-inventory.json` declares exactly three replacement targets, their
original rollback bytes, and64 unchanged installed-file hashes. Its manifest has
complete HERE-relative target closure. This directory is not an installer.

Offline checks from the repository root:

```sh
python3 -B configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/original-backend-diagnostics/tests -v
sh configs/dispatcharr-iptv/original-backend-diagnostics/tests/run-permissions.sh
```

The permission runner requires existing user/subuid/network namespace support.
It uses a disposable synthetic chroot, UID0/UID1000 and dummy data only; no Docker,
production service, application/database or external network operation occurs.

Read `docs/dispatcharr-original-backend-diagnostics-patch.md` before review.
Installation of this delta and one managed restoration attempt both require
separate authorization. No image, unit, guard, provider or Jellyfin changes are
included. Do not apply these files over the newer native-hardening sources.

Emergency correction: receipts now use `/root/dispatcharr-backend-diagnostics`,
with strict root-private parent and ancestor validation independent of `/docker`.
See `docs/dispatcharr-original-stack-recovery-completion.md` for installation/results.
