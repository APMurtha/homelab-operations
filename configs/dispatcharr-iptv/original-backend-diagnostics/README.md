# Original backend diagnostics — offline structured candidate

This is Option A for the original four-service lifecycle, not native hardening.
It uses one supported `celery -A dispatcharr inspect ping --timeout=8 --json`
command and requires exactly one explicit positive pong from default and DVR.
No human-output fallback, retry, delay, alternate health probe or bypass exists.

The current installed diagnostic baseline (source1f73b94, deployment evidence
f7df20f) is preserved exactly in `structured-baseline/`; its hashes are frozen in
`structured-baseline-hashes.json` and hard-coded by `verify_candidate.py`.
Older f4298da copies under `installed-baseline/` and227122d `original/` copies
remain unchanged and independently verified. Use the correct current rollback.

Only `backend.py` and `manifest.json` are proposed installation targets.
Lifecycle bytes remain exactly `0df62a94…`. The inventory closes all67 targets:
2 proposed replacements and65 unchanged files. `candidate.patch` now compares
against `structured-baseline/`. This directory is not an installer.

```sh
python3 -B configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/original-backend-diagnostics/tests -v
sh configs/dispatcharr-iptv/original-backend-diagnostics/tests/run-permissions.sh
```

Tests use mocks, synthetic local Python child pipes and disposable UID0/UID1000
user/network namespaces and chroot. They never execute Celery or Dispatcharr,
contact a broker, or operate Docker/systemd. The retained JSON CLI contract is
recorded in `celery-json-cli-contract.json` without a new application invocation.

Private receipts remain `/root/dispatcharr-backend-diagnostics` with unchanged
strict root ancestry, ownership, modes, no-follow and exclusive-write checks.
Only fixed sanitized metadata is retained. Broker comparison remains unknown
unless authoritative effective-settings snapshots exist; no snapshot acquisition
or Django import was added.

See `docs/dispatcharr-celery-structured-readiness-fix.md`. Installation and any
managed restoration start require separate authorization. No image, unit, guard,
provider, Jellyfin or production configuration is changed by this offline task.

For future failed captures the optional Celery record field `reply_rejection`
identifies the first failed structured validation rule. Multiple defects can
produce the same first rejection. A capture byte limit takes precedence over
UTF-8 errors in a truncated prefix. Valid empty and one-role mappings retain
their missing-role classifications. Historical receipts remain readable without
the field. The November 19 stdout was discarded, so its specific rejection
cannot be recovered. The baseline inventory here describes the historical
structured candidate and is not a deployment or rollback plan for this change.
