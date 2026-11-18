# Original backend diagnostics — offline candidate

This candidate extends the diagnostic-instrumented original four-service lifecycle,
not the newer native-hardening lifecycle. The current installed baseline is
`f4298da`: exact rollback copies of its three diagnostic files are preserved under
`installed-baseline/`, with hard-coded verification in `verify_candidate.py`.
The older `227122d` originals remain byte-for-byte under `original/`.

The proposed correction replaces only `backend.py` and `manifest.json`.
`lifecycle.py` remains the exact installed `0df62a94…` bytes. The inventory closes
all 67 targets: two proposed replacements and 65 unchanged files. `candidate.patch`
now reviews only the delta from `installed-baseline/`. Nothing here is an installer.

```sh
python3 -B configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/original-backend-diagnostics/tests -v
sh configs/dispatcharr-iptv/original-backend-diagnostics/tests/run-permissions.sh
```

The permission runner uses disposable user/network namespaces, a synthetic chroot
and UID0/UID1000. No Docker, production service, application/database or external
network operation occurs. Synthetic child-process tests execute only local Python
fixtures; they never execute Celery or Dispatcharr.

Receipts remain `/root/dispatcharr-backend-diagnostics`, with unchanged strict
root-private ancestry/no-follow/exclusive-write rules. Classifications and timings
contain fixed fields only. Broker comparison is pure and accepts authoritative
already-resolved settings; the runtime path emits unknown until such snapshots
are available. It does not infer effective configuration from environment absence,
import Django or query a broker.

See `docs/dispatcharr-celery-diagnostic-correction.md`. Installation and one managed
restoration start require separate authorization. This offline task installs
nothing and changes no image, unit, guard, provider or Jellyfin configuration.
