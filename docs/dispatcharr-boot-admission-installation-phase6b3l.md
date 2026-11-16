# Dispatcharr Phase 6B-3L — resource admission installation

2026-11-16 UTC. Rivendell, 10.10.20.30. Explicitly authorized installation and
nondisruptive verification only. Reviewed commit:
`463f623417c61298d98fd225e876859522e7d050`.

**GO — installation, native verification, standalone probe and post-installation
acceptance passed.** Both new files are installed and loaded for future stack
activations. The existing stack remains running with unchanged container IDs,
start times and images. No service/container restart or host reboot occurred.
This is not a managed-start or cold-boot validation of the new admission path.

References: [reviewed design](dispatcharr-boot-admission-phase6b3k.md),
[successful recovery](dispatcharr-controlled-recovery-phase6b3j.md),
[installation candidate](../configs/dispatcharr-iptv/boot-admission-phase6b3k/README.md).

## 1. Preflight and recovery

Final installation preflight at **19:40:07 UTC** established:

- Dedicated Gluetun, Dispatcharr and gateway healthy. Both persistence units
  enabled, active/exited, Result=success; Docker active/running.
- Input, guard and running-contract checks pass. The original seven installed
  files retain their reviewed SHA-256 values and ownership/permissions.
- Base stack unit SHA-256 remains
  `30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e`.
- No loaded or conflicting on-disk stack drop-ins; both new targets absent.
  The three original ExecStartPre commands match the reviewed base exactly.
- Fresh pinned SSH succeeds. Application and gateway management HTTP readiness,
  backend/worker checks and normal VPN exit checks pass before installation.
- Container identities/images, HostConfig fingerprints, running/health state,
  start times, restart counts, Docker process identity and networks captured.
- Rivendell installation rollback files under
  `/root/dispatcharr-minimal-recovery-20261116T051539Z` remain accessible; their
  hashes match earlier captured values. The scoped rollback instructions remain
  available in the reviewed repository plan.
- Independent existing checkpoint on Denethor at
  `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z` is
  accessible and all three archive SHA-256 values match. No backup was created,
  expanded, restored or moved.

Path inspection rejected symlinks and conflicting targets. The dedicated project
and systemd directories are root-owned 0755. Existing `/docker` is
`murth:docker`, mode 0770; its write group matches the root-owned, group-writable
rootful Docker socket. That existing administrator trust boundary was verified
and preserved; no parent-directory permissions were changed.

## 2. Exact installation and native validation

The source bytes were checked against both `git show` at the reviewed commit and
the explicitly authorized digests. They were streamed over the existing selected
SSH transport and created exclusively with no symlink following. No conflicting
file was overwritten. Only the following two runtime files and their necessary
parent directories were installed:

| Installed file | SHA-256 | Ownership / mode |
|---|---|---|
| `/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py` | `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917` | root:root / 0644 |
| `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` | `72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb` | root:root / 0644 |

Both installed files are regular files, not symlinks. Original seven persistence
files, Compose definitions, image references, secrets, application configuration,
restart policies and security files remain unchanged. Tests, README and manifest
were not installed as runtime components.

Native **systemd 255.4** verification ran against the installed base unit and
on-disk drop-in using:

```sh
systemd-analyze verify --man=no /etc/systemd/system/dispatcharr-stack.service
```

**Exit 0; stdout and stderr empty.** Before activation the manager still held the
original three prestart commands, confirming installation had not restarted the
unit or automatically exercised the new admission path.

## 3. Single standalone capacity probe

Exactly one invocation of the installed helper ran as a standalone read-only
probe, **19:44:04–19:44:29 UTC**. It read host proc telemetry only; it invoked no
Docker/systemd/firewall action and did not signal a worker or reset Redis.

**Actual helper exit: 0. Process duration: 25.288 seconds.** Output was eight JSON
records, **766 bytes**, with no stderr. The five-minute policy deadline remained
unchanged. The capacity decision was checked using the actual process status,
not merely the `capacity_ready` record.

| Helper elapsed seconds | Idle % | Steal % | Load1 | Consecutive qualifying samples |
|---:|---:|---:|---:|---:|
| 5.009 | 40.275 | 27.495 | 1.44 | 0 |
| 10.016 | 31.994 | 37.558 | 1.33 | 0 |
| 15.016 | 84.413 | 4.403 | 1.22 | 1 |
| 20.017 | 82.981 | 3.172 | 1.12 | 2 |
| 25.019 | 84.107 | 4.440 | 1.03 | 3 |

The live probe therefore waited through unsuitable conditions before accepting
three consecutive valid intervals. This verifies the installed helper's normal
Linux telemetry path and successful bounded exit; it does not test permanent
refusal, unit failure cleanup or post-reboot application initialization.

A one-off capture process kept the probe's exit receipt independent of SSH's
transport lifetime. It created no service, timer or scheduled job. Its temporary
root-private `/run` receipt was copied to local private evidence and removed after
completion. No additional persistent component remains.

## 4. Configuration activation without restart

After native verification and the successful probe, **`systemctl daemon-reload`**
was executed. Effective configuration and runtime checks passed at **19:46:50 UTC**.
No start/restart/reload command was sent to Dispatcharr, Gluetun, Caddy, Docker or
Jellyfin; only the systemd manager's configuration was reloaded.

The effective prestart sequence is exactly:

1. `/usr/bin/python3 /docker/dispatcharr-iptv/minimal-phase6b3d/verify.py inputs`
2. `/usr/bin/python3 -B /docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py`
3. `/usr/bin/python3 /docker/dispatcharr-iptv/guard.py apply --policy /docker/dispatcharr-iptv/private/egress-policy.json`
4. `/usr/bin/python3 /docker/dispatcharr-iptv/minimal-phase6b3d/verify.py prestart`

Then the unchanged Compose startup, existing running-contract verification and
original scoped ExecStopPost cleanup remain in place. The third command above
was **not executed by this installation**: daemon-reload does not start the stack.
No firewall reapplication or policy modification was performed.

Verified unchanged: Requires/After/Before/Wants/BindsTo/PartOf dependencies;
original ExecStart/ExecStartPost/ExecStopPost argument lists; Restart=no;
TimeoutStartSec=540 and TimeoutStopSec=240; Compose wait option; unit enabled,
successful active/exited state and prior activation timestamps. These remain
per-command systemd timeout semantics, not a single aggregate activation budget.

The stack's only loaded drop-in is the newly authorized path. Both persistence
units remain enabled and successful. Docker's dependencies, process identity and
activation timestamps are unchanged.

## 5. Post-installation application and security acceptance

Previously validated diagnostics ran nondisruptively with the generated app
environment. No diagnostic logic, data records or stream configuration changed.

| Check | Result |
|---|---|
| PostgreSQL read-only connectivity | PASS |
| Migrations | None pending; 184 entries, unchanged fingerprint |
| Redis PING | PASS |
| Two uWSGI workers | PIDs 277/278, master 274; unchanged |
| Redis-backed worker heartbeats | Fresh: ages 0.705/0.776 seconds, TTL 29 seconds each |
| Celery default / DVR | Both respond to validated ping |
| Application HTTP / gateway health | 200 / 200 |
| Read-only provider audit | PASS; built-in records only, zero channels/EPG sources |
| Recurring Redis-reference exceptions / application tracebacks / migration failures | None in inspected logs |
| Application FFmpeg/FFprobe | None |

The scoped nftables guard and full running-contract verification pass. tun0
remains up with the intended VPN route; namespace OUTPUT remains default-drop;
Docker embedded DNS rejection remains present; application nameserver directives
are 127.0.0.1; namespace IPv6 remains disabled. Normal HTTPS IP-echo verification
from the application reports accepted VPN exit **198.44.159.163**, different from
the host's normal exit. No IPTV endpoint or playback was requested.

Accepted gateway access/filtering configuration is unchanged and its health
endpoint passes. No firewall/VPN rule, capability or network was modified. VPN-loss
and boot packet tests were not performed; these are normal-operation checks, not
a new proof against every possible transient packet exposure.

## 6. Runtime identity and unrelated services

The following dedicated container ID prefixes and start times are identical
before and after installation; full identities are retained privately:

| Component | Container ID prefix | Start time UTC, unchanged |
|---|---|---|
| Dedicated VPN | `1b9d20c93194` | 18:53:43.381 |
| Dispatcharr | `d34275eddd72` | 18:53:50.621 |
| Gateway | `03ec8c82417e` | 18:55:02.757 |

All three remain healthy with restart count 0. Unrelated container IDs, images,
HostConfig fingerprints, start times, running state and healthy baselines match
the captured preflight. Docker process and network identities are unchanged.
Jellyfin, original download Gluetun and qBittorrent remain healthy; Sonarr, Radarr,
Prowlarr and NZBGet remain running. No unrelated container was recreated or
restarted. Existing stopped containers remain stopped.

## 7. Deviations, rollback and final assessment

No reviewed artifact or design deviation was required. Two read-only preflight
issues were resolved before mutation: the inspection parser was corrected for
systemd's repeated command entries, and the overly strict ancestor-ownership
heuristic was replaced with verification of the existing Docker-administrator
trust boundary. Neither indicated changed service configuration. Streaming the
reviewed bytes avoided extra permanent staging files. The standalone receipt was
temporary diagnostic evidence, not another installed service/component.

Rollback remains scoped to the new drop-in and helper. With no activation job in
progress, remove the drop-in, daemon-reload, verify the three original prestart
commands, then remove the helper and its directory if empty. Do not stop a healthy
stack merely to remove the unused prestart override. Original persistence files,
security controls, images and data must be retained. No rollback was necessary or
exercised; the implementation included scoped rollback on validation failure.

**Installation assessment: GO / PASS.** The two files are installed, loaded and
verified; the existing protected stack is left running. Private receipts are
retained in Git-ignored `.ai-local/dispatcharr-phase6b3l/`; only this sanitized
report is published. No credentials, private log exports, dumps or recovery
archives are included.

The helper has not yet been exercised by an actual systemd stack start. Managed
startup, refusal/cleanup behavior and a controlled cold reboot remain separate
live validation work requiring authorization. No reboot, restart, playback,
Jellyfin integration or next implementation phase is started automatically.
