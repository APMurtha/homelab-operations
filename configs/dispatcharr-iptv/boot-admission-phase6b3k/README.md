# Phase 6B-3K — UNAPPLIED boot admission candidate

Read the [design and installation/rollback plan](../../../docs/dispatcharr-boot-admission-phase6b3k.md).
This directory is a proposal, not an installed service or daemon.

Only two files would be installed after approval:

| Repository file | Proposed destination |
|---|---|
| `admit.py` | `/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py` |
| `20-resource-admission.conf` | `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` |

Use root:root, mode 0644. Python invokes the script; executable mode is unnecessary.
The original seven persistence files remain unchanged. Do not install the tests,
this README or the artifact manifest as additional runtime components.

The existing stack unit's prestart order becomes:

1. Original input verification.
2. Bounded CPU admission.
3. Original accepted-table reapplication.
4. Original final guard/network/namespace preflight.
5. Original Compose start and application health gates, then running verification.

The drop-in resets only `ExecStartPre` to insert the helper; it repeats the exact
three reviewed commands. Do not use it against a changed base unit or merge it
blindly with other drop-ins. Tests pin the original base unit SHA-256.

Admission requires three consecutive five-second samples with idle CPU >=50%,
steal <=10%, load1 <4 and four online CPUs. Earliest success is approximately
15 seconds. The monotonic deadline is 300 seconds; there is no fixed boot sleep.
Missing/malformed telemetry or changed CPU topology blocks; counter discontinuity
resets the streak. Exit 0 admits, 1 is deadline refusal, 2 is invalid telemetry,
and 130 is interactive cancellation. SIGTERM retains normal process semantics.
Use the exit status as the admission decision; `capacity_ready` is a telemetry
observation and can be followed by refusal if logging crosses the deadline.

The helper reads only `/proc/stat` and `/proc/loadavg`, emits bounded JSON status,
and exits. It cannot reserve CPU, certify application readiness or enforce VPN
isolation. It invokes no Docker, systemd, nft, network or process-control API.
No scheduled retry or continuous monitoring is added. After any refusal the
existing unit's scoped cleanup runs; security rules and data are retained.

The original health checks, Compose wait option, per-command systemd timeouts,
dependencies and restart policies are unchanged. Aggregate activation can exceed
540 seconds: that setting is not a whole-job stopwatch in systemd 255. The gate's
own deadline bounds admission, with the existing timeout as a fallback if it hangs.

Offline reproduction from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s configs/dispatcharr-iptv/boot-admission-phase6b3k/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 configs/dispatcharr-iptv/boot-admission-phase6b3k/tests/verify_units.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s configs/dispatcharr-iptv/minimal-phase6b3d/tests -v
```

The native verifier creates temporary unit files and a Docker readiness fixture;
`systemd-analyze verify` parses them without executing services. Local sandbox
socket restrictions may require permission to run this offline verifier outside
the sandbox. No new daemon, Docker instance or VM is needed. These tests do not
prove boot-time behavior on Rivendell. Do not execute an installation or restart
as part of this phase.

## Coordinated trusted readiness update

The current 20 drop-in adds fixed-path withdrawal BEFORE input verification and
admission, and invokes the matched scoped cleanup helper after withdrawal. CPU
thresholds, admit.py, base unit bytes and timeouts are unchanged. Earlier command-
list-only descriptions above document the original baseline. Use the complete
trusted-guard implementation transition; do not install this drop-in alone.


The coordinated native-hardening candidate inserts provider authorization
withdrawal before the existing guard-marker withdrawal and admission command.
It does not change admit.py, thresholds, sample windows, retries or unit timeouts.
Cleanup attempts provider withdrawal and existing scoped stop even on failure.
See docs/dispatcharr-native-hardening-final-integration.md; no drop-in is installed
by this offline work.
