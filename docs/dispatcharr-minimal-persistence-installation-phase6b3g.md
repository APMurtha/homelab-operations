# Dispatcharr Phase 6B-3G — minimal persistence installation

2026-11-16 UTC. Rivendell, 10.10.20.30. Explicitly authorized scoped installation.

**GO — installation and immediate acceptance passed.** The exact reviewed seven
files are installed. Both oneshot units are enabled and active/exited; all three
dedicated containers are healthy with restart=no. This certifies the installation
and tested normal operation, **not a cold boot, daemon-failure or full production
recovery test**. No next implementation phase was started.

## 1. Preflight and scope

Reviewed Phase 6B-3D design, 3E preflight, 3F recovery checkpoint and storage
reconciliation. The independent Denethor NVMe checkpoint's three archive hashes
and Rivendell's local rollback file hashes matched. Current Compose/source/image,
mount/namespace/port and guard contracts matched the reviewed assumptions.
There were no active media processes or configured channels/EPG providers.

All 32 containers and the existing networks/Docker process were recorded before
changes. Root available space exceeded 7 GiB. Fresh pinned SSH access worked.
No NAS repair, backup rerun or storage migration was needed. The legacy Orthanc
backup job/UNAS SMB issue was not treated as an installation blocker.

Only dedicated iptv-vpn, dispatcharr and gateway were stopped/recreated to adopt
restart=no. Existing networks, accepted base Compose, images, persistent mounts,
security inputs and unrelated services were retained. No global Docker restart,
host reboot, Jellyfin integration, channel import, DVR or playback occurred.

## 2. Exact installed files

Every active file is root:root, mode 0644, and matches the approved Phase 6B-3D
artifact SHA-256. No candidate source was modified to obtain acceptance.

| Installed path | SHA-256 |
|---|---|
| `/docker/dispatcharr-iptv/minimal-phase6b3d/verify.py` | `871bba35c84e1ecdc966d925a0718d281e559ce918420b41c26610eb4265be69` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/contracts.py` | `2ba2080ce45a2c72611f3c33c7341f921d44cdbc9d936ca9d1edd086622251dd` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/compose.persistence.proposed.yaml` | `60a41dd431bd1b986a9f432ffecdd039e80eae6aea630322dab163bee66a8c9a` |
| `/etc/systemd/system/dispatcharr-egress-guard.service` | `bde5207014fa24781d8cd1275a54dac056684299e498f4773fca2ed2e98cc174` |
| `/etc/systemd/system/dispatcharr-stack.service` | `30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e` |
| `/etc/systemd/system/docker.service.d/50-dispatcharr-order.conf` | `c9beb54d2b2e6285013355f3a80dd6677ff7723d10e835f45c499f39fb9e581b` |

The four project files are the read-only verifier, pure contracts, accepted table
template and restart-policy override. The remaining three are two systemd units
and the Docker ordering drop-in. No controller, enrollment, cgroup slice, recovery
daemon or new timer was introduced. Root-private staging and rollback receipts
are bookkeeping copies, not additional runtime components.

Native target `systemd-analyze verify` passed after installation and before
activation. All installed ownership/checksums were rechecked after activation.

## 3. Activation and systemd state

Followed the documented sequence: preserve baseline; stage reviewed bytes; install
project files; validate inputs/Compose; stop only dedicated services; reapply and
verify the existing accepted scoped guard; create stopped containers with the
minimal override; validate prestart; install units/drop-in; verify; daemon-reload;
request one stack start; accept; enable both units.

The single start used `systemctl start --no-block dispatcharr-stack.service` and
fresh read-only SSH polls. This preserves the reviewed unit behavior while avoiding
the transport's five-minute connection lifetime; it is not a retry/restart loop.

The Compose/health portion reached active in **135.408 seconds**. Gateway
remained stopped until application health passed, then became healthy.

| Unit | Final state | Result | Enabled |
|---|---|---|---|
| `dispatcharr-egress-guard.service` | `active (exited)` | `success`, exit 0 | `enabled` |
| `dispatcharr-stack.service` | `active (exited)` | `success`, exit 0 | `enabled` |

Effective dependencies were inspected after daemon-reload and enabling:

- Guard is Before=docker.service and depends on local storage. It applies and
  verifies only the accepted table, with no rule-removing ExecStop.
- Stack Requires/After/BindsTo Docker and guard; PartOf propagates their normal
  service stop/restart jobs. It reapplies/verifies after Docker startup, before
  protected Compose startup, and uses the existing health dependencies/gates.
- Docker's effective drop-in Wants guard and stack and orders after guard. Its
  soft relationship preserves unrelated Docker availability if the guard fails;
  the stack's hard dependency and preflight block its own admission.
- Docker restart policies are no for all three protected containers, preventing
  engine autostart around those checks. Unrelated restart policies are unchanged.

The ordinary start path and dependency order succeeded. Guard-failure behavior is
supported by the reviewed dependency/verification design and previous offline
fixtures; a live failure was deliberately **not** injected. Active/exited is a
oneshot status, not continuous container health supervision.

## 4. Container identities

Full before/after IDs are retained in private receipts. These historical IDs are
not instructions to signal processes or blindly operate later replacements.

| Dedicated component | Before ID | After ID | Final health / restart count |
|---|---|---|---|
| `/rivendell-iptv-vpn` | `dfa35e0d8614e51001e2da17cf32fa34e1d78fc0c267d0bee29cd04a084b00ba` | `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e` | healthy / 0 |
| `/dispatcharr` | `2c1331d8e7d766fc0f1a3a5630bb99bb53fe8460f43b1406d6ce889c087f1b5f` | `d34275eddd72dd944bf7e2bb24496d71467b2e4a6505fc93e830a4f3fbb34b92` | healthy / 0 |
| `/rivendell-iptv-gateway` | `f60893c317fb043f20a0db8cbf88482635e27f0b4671c8fbb6f5153d3bec4f2a` | `03ec8c82417ede9175ad0320a37792c72357987529009aea0b51d3991c2f2ffd` | healthy / 0 |

The original pinned Dispatcharr 0.33.0 image remains deployed. Gluetun/Caddy image
IDs also remain unchanged. The custom readiness test image was neither deployed
nor made permanent. Persistent data were not replaced and network IDs stayed
unchanged.

## 5. Firewall, VPN, DNS and gateway

**Passed, nondisruptive checks:**

- Exact live `inet rivendell_iptv` structure and matching policy marker, before
  and after accepted scoped reapplications. No global flush/policy redesign.
- Dedicated Gluetun healthy; WireGuard setup log observed, tun0 up and its default
  policy route present. Namespace OUTPUT remains default-drop.
- Normal HTTPS IP-echo request succeeded from the Dispatcharr namespace and
  returned a public VPN address different from the host's normal exit. Host exit
  identity was compared in memory and not included in public receipts.
- Observed dedicated VPN exit: `198.44.159.163`. No IPTV endpoint was contacted.
- Application nameserver directives are exactly 127.0.0.1; Docker embedded DNS
  remains explicitly rejected; Gluetun's reviewed resolver configuration retained.
- Namespace IPv6 remains disabled; no added IPv6 path or port exposure.
- Reviewed Caddy access/header/redirect configuration unchanged; gateway health
  returned HTTP 200 via `http://10.10.20.30:9191/healthz`.
- Exact shared namespace, private mounts, restricted capabilities and sole
  published listener contract passed the installed running verifier.

This confirms the approved VPN path and normal-operation restrictions. No
fallback route was made available by this change. VPN-loss, global-flush and
unauthorized-client packet tests were not repeated; there is no claim of a new
live fail-closed experiment. The prior scope/security limitations remain.
HLS relay is not deployed in the accepted three-service base; its saved source
and policy boundaries are unchanged, and no relay/trial resource was added.

## 6. Application acceptance

| Check | Result |
|---|---|
| Dispatcharr HTTP | 200; Docker health healthy |
| PostgreSQL | Read-only SQL succeeds; database dispatcharr, role dispatch |
| Schema/migrations | 184 migrations; fingerprint unchanged; validated migrate --check exits 0 |
| Redis | PING succeeds; two fresh Redis-backed web-worker heartbeats |
| uWSGI | Two web workers with the same live master parent, plus existing router; heartbeat freshness <1 second at capture |
| Default and DVR Celery workers | Both reply to validated supported readiness check |
| Provider audit | Only legitimate built-in account/profile; no unexpected account, profile or EPG source |
| Channels / EPG | Zero / zero, unchanged |
| Startup exceptions | Zero Redis NoneType/exists matches, zero tracebacks and zero migration-failure markers in bounded startup logs |
| Media processes | No FFmpeg/FFprobe processes; no playback initiated |
| Restart loops | Zero restart count for each recreated dedicated container |

Heartbeats establish current web-worker liveness and Redis-backed activity; this
phase does not claim stream-specific cached-reference/playback validation.
The database fingerprint compared migration names/count and lineup counts; it is
not a claim that every bookkeeping row is byte-identical after normal startup.
No unexpected migration or direct database/configuration write was performed by
the verification commands.

## 7. Unrelated services and management

All **29 unrelated containers** retained their IDs, images, start times, running
states and HostConfig fingerprints; previously healthy services remained healthy.
Docker's main process and active timestamp, the complete network ID set and the
dedicated network ID were unchanged. Fresh SSH succeeded throughout and after
enabling.

| Service | Final status / identity |
|---|---|
| `/nzbget` | running; no Docker healthcheck; `1c6fa534fe68` unchanged |
| `/qbittorrent` | healthy; `512885aff720` unchanged |
| `/radarr` | running; no Docker healthcheck; `d721f472d63b` unchanged |
| `/sonarr` | running; no Docker healthcheck; `f438ff1017bb` unchanged |
| `/prowlarr` | running; no Docker healthcheck; `c483390b08ba` unchanged |
| `/gluetun` | healthy; `1d1c69791f68` unchanged |
| `/jellyfin` | healthy; `6798247b9099` unchanged |

Jellyfin was not configured, restarted or recreated. Its image/container and
HostConfig were unchanged; no tuner, guide, user, library or playback setting was
changed. Original download Gluetun remains healthy; download-service readiness
above is current Docker running/health state, not a new transfer test.

## 8. Deviations and diagnostic corrections

No infrastructure-design deviation or actual security acceptance failure occurred.
Two new one-off diagnostic assertions needed correction:

1. Before any installation change, a SQL check used `channels_channel`; the
   read-only catalog established the actual `dispatcharr_channels_channel` name.
   The diagnostic was corrected and the complete preflight passed. No approved
   candidate or schema was changed.
2. After startup, a resolver check searched raw text for 127.0.0.11 and matched a
   warning comment in the unchanged reviewed file. Actual nameserver directives
   were exactly 127.0.0.1. The diagnostic was corrected to parse directives and
   require that exact list; no resolver/security change or service restart was
   made. Full acceptance then passed.

The stack was started once; no speculative recovery signal, second restart or
worker reload was used. No rollback was required because the observed workload
and installed controls passed their actual acceptance conditions.

## 9. Rollback readiness

Fresh root-private installation baseline:

```text
/root/dispatcharr-minimal-recovery-20261116T051539Z
```

It retains original Compose, all-container/network/Docker baseline, scoped guard,
Docker unit, file-absence facts and installation state/acceptance receipts.
Staged reviewed files/checksums remain under `/root/dispatcharr-minimal-phase6b3d`.
The independent Phase 6B-3F checkpoint on Denethor's secondary NVMe remains
available and rehashed; no backup was repeated.

If later rollback is explicitly authorized, use the Phase 6B-3D scoped procedure:
keep/reapply accepted rules, stop only dedicated stack, confirm stopped, disable
candidate units and remove only its recorded units/drop-in, daemon-reload, then
recreate/start from the unchanged original base and verify old restart policies.
Preserve data and filters. An unresponsive Docker API means shutdown is
unconfirmed: stop/report rather than removing protections or using broad kills.
Do not restore a full-host ruleset or unrelated media services. Ordinary rollback
does not require a PostgreSQL restore; no database migration occurred here.

## 10. Final assessment and remaining work

**GO — approved minimal persistence installed, enabled and running successfully.**

Still untested/unresolved for unattended production: host cold boot, Docker-wide
restart/failure behavior, proportionate full restore rehearsal, routine Dispatcharr
backup coverage/destination access, NAS/legacy storage health where relevant,
and operational health/backup-age/resource monitoring. Those are separate work,
not hidden claims of this installation. One-shot active status does not restart
a later crashed application. No reboot/failure test or permanent Jellyfin/lineup
integration was started automatically.

Private sanitized receipts are under
`.ai-local/dispatcharr-phase6b3g/`; installed file hashes and live acceptance are
also recorded in the root-private rollback directory. No credentials, WireGuard
keys, generated Django secrets, host WAN address or upstream authentication URLs
are disclosed in this report.
