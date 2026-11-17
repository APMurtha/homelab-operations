# Dispatcharr permanent streaming deployment — preflight NO-GO

2026-11-17 UTC (2026-11-16 US/Eastern). Andrew's Rivendell, 10.10.20.30.
Approved candidate: `f7115a8339685ba3e5314d8e54a40f239c5e3723` on `docs/udm-pro-max-migration-prep`.

**Deployment stopped before installation or disruption.** Two mandatory prerequisites fail: no existing Default Group and an application network ACL incompatible with the approved registrar. The original healthy three-container stack remains running. No stop/start authorization was consumed and no rollback was needed.

## 1. Preflight and artifact verification

Reviewed the approved [implementation report](dispatcharr-permanent-streaming-implementation.md) and [candidate README](../configs/dispatcharr-iptv/permanent-streaming/README.md). The local candidate checkout was clean at the exact approved commit. All 39 source/test entries in its committed manifest match; candidate manifest SHA-256 is `98d962f397c5bae9aee3411574687168140d17c6419635a7e3d8f7550e1b0c0f`. The candidate was not edited or substituted.

Fresh preflight at **2026-11-17T01:58:52Z** established:

- Original VPN, Dispatcharr and gateway containers running and Docker-healthy. Existing minimal input, exact guard and running-contract checks pass.
- All nine installed persistence/admission hashes and root:root 0644 permissions match approval. The stack and guard units are active/exited, Result=success. Only the original 20-resource-admission drop-in is loaded; the start timeout remains nine minutes.
- The exact patched image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` remains available locally. No pull/build was performed.
- Zero Dispatcharr live-channel Redis keys and zero FFmpeg/FFprobe processes. Supported API inspection reports zero recordings, zero channel groups; PostgreSQL reports zero channels and EPG sources. No playback or recording was stopped.
- PostgreSQL migration inventory remains 184 rows, fingerprint `b00f51e91c5b882cd84d3b2579d074ca`. One locked active FFmpeg streamcopy/MPEG-TS profile exists.
- The existing owner's accepted-origin login authenticates and can read the relevant API inventories. Credentials and JWT remained private; no channel, stream, group or settings mutation was attempted. Write-role acceptance was not exercised after the other prerequisites failed.
- Owner confirmed no conflicting administrative work during this window.
- Existing Rivendell rollback inputs under `/root/dispatcharr-minimal-recovery-20261116T051539Z` remain readable with the recorded hashes. The independent checkpoint at `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z` is accessible; all three archive hashes match its manifest. No backup creation or restore exercise occurred.

## 2. Exact installed identities and hashes

These are the retained original deployment, not a claim that the permanent candidate was installed.

| Container | Exact running image identity | State |
|---|---|---|
| `rivendell-iptv-gateway` | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` | healthy; restart count 0 |
| `dispatcharr` | `sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` | healthy; restart count 0 |
| `rivendell-iptv-vpn` | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` | healthy; restart count 0 |

The original VPN-owner container ID remains `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e`.

| Installed file | Verified SHA-256 |
|---|---|
| `/docker/dispatcharr-iptv/minimal-phase6b3d/verify.py` | `871bba35c84e1ecdc966d925a0718d281e559ce918420b41c26610eb4265be69` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/contracts.py` | `2ba2080ce45a2c72611f3c33c7341f921d44cdbc9d936ca9d1edd086622251dd` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/compose.persistence.proposed.yaml` | `60a41dd431bd1b986a9f432ffecdd039e80eae6aea630322dab163bee66a8c9a` |
| `/etc/systemd/system/dispatcharr-egress-guard.service` | `bde5207014fa24781d8cd1275a54dac056684299e498f4773fca2ed2e98cc174` |
| `/etc/systemd/system/dispatcharr-stack.service` | `30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e` |
| `/etc/systemd/system/docker.service.d/50-dispatcharr-order.conf` | `c9beb54d2b2e6285013355f3a80dd6677ff7723d10e835f45c499f39fb9e581b` |
| `/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py` | `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917` |
| `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` | `72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb` |

The 30-permanent-streaming drop-in is absent and `/docker/dispatcharr-iptv/permanent-streaming/` does not exist. No candidate/runtime/private configuration was staged.

## 3. Scoped timeline and prerequisite failures

| Stage | Result |
|---|---|
| Review exact approved commit and manifest | PASS |
| Verify independent recovery and original installed protections | PASS |
| Read current health, idle state, profile, peers and application compatibility | Two prerequisites fail |
| Owner credential/API and recording checks | Authentication/read checks pass; zero recordings; missing group confirmed through API |
| Final unchanged-state verification, 2026-11-17T02:00:46Z | PASS |
| Candidate staging, protected stop, stopped recreation, drop-in install, daemon-reload, protected start | **Not performed** |
| Registration/export acceptance and rollback | **Not reached / not required** |

**Blocker A — Default Group absent.** SQL count and supported API inventory both confirm zero groups. The approved registrar explicitly requires one existing group named Default Group. It intentionally writes only the owned channel/stream and cannot create this prerequisite group. No group was created implicitly.

**Blocker B — network ACL mismatch.** The current application policy does not satisfy the registrar's exact-peer contract. Its STREAMS field currently has one configured entry and does not equal the required set. Neither M3U_EPG nor XC_API is the required literal `127.0.0.1/32`. This is a compatibility failure, not a claim that the accepted running baseline has become unsafe. No policy was broadened, normalized or otherwise changed to force success.

The candidate would require STREAMS to contain exactly `127.0.0.1/32`, `10.10.20.30/32`, `172.16.70.1/32` and the observed Jellyfin peer `172.20.0.2/32`, with M3U_EPG/XC_API loopback-only. Any reconciliation must first review the actual current policy and intended consumers and obtain a precise scoped authorization; do not silently discard access or add broad CIDRs. The registration credential file must then bind the reviewed canonical ACL digest.

## 4. Resource admission

No systemd start was issued and the admission helper was not invoked. Admission duration/results are **not applicable**. Its installed source and drop-in hashes remain unchanged. There was no threshold, timeout or restart-policy adjustment.

## 5. Backend and relay readiness

The original three-service application remains healthy. Authenticated Redis PING succeeds through the idle-state check; PostgreSQL read-only queries succeed. A permanent deployment's fresh per-worker uWSGI/Celery acceptance was not reached, and no new claim of candidate backend readiness is made.

The patched image is retained but was not promoted. No managed relay container was created, started or tested live. Rolling-budget source verification belongs to the approved candidate and its 117 offline tests; its installed runtime budget was not exercised here.

## 6. Registration and exports

No endpoint was generated or registered, no owned channel/stream was created or updated, and no deployment transaction journal or rollback intent was required. The database remains at its preflight zero-channel state.

Jellyfin's current peer is `172.20.0.2`; its Live TV configuration file is owned by UID/GID 1000, compatible with the reviewed candidate's ownership requirement. The permanent export directory is absent, as expected before staging, and was not created after the compatibility failure. No M3U/XMLTV generation or Jellyfin configuration action occurred. Future export readability and renewal remain unaccepted.

## 7. VPN/firewall/security

Fresh exact nftables guard and running namespace/image-contract checks pass. Additional read-only normal-path checks confirm default routing through tun0, OUTPUT default DROP, Docker embedded-DNS rejection, application nameserver 127.0.0.1 and disabled IPv6. Dedicated Gluetun remains healthy.

No external media, manifest, segment, playlist or broadcaster request was made. No failure injection was performed. These are current normal-path baseline checks, not a new exhaustive leak test. No new port or Docker network exists. The accepted gateway/filter source remains unchanged; candidate-specific routing/filter acceptance was not reached.

## 8. Unrelated services and Jellyfin

Final comparison confirms all protected and unrelated container IDs, image IDs, HostConfig fingerprints, start times, running/health states and restart counts equal preflight. Docker process identity and Docker network identities are unchanged. Jellyfin remains healthy; its Live TV file hash remains exactly the preflight value. Existing stopped/unhealthy services remain their pre-existing conditions; no unrelated repair was attempted.

No Jellyfin tuner/provider, library, user, playback default or DVR setting changed. No playback was initiated. There was no VM/host operation, reboot or Docker-wide restart.

## 9. Failures/deviations and rollback

This is a **preflight NO-GO**, not a failed start or partial deployment. The explicit instruction to stop on a failed prerequisite was followed. Lifecycle calls: **zero stops, zero starts, zero container recreations**. No daemon-reload, source installation, private configuration preparation or policy change occurred.

No deployment API writes have an uncertain outcome. The only authentication request issued an in-memory JWT for authorized credential confirmation; subsequent calls were read-only. No rollback was attempted because the original deployment was never altered. Current guard protection was preserved throughout.

## 10. Final decision

**NO-GO for permanent deployment, Jellyfin integration or playback.** The existing protected three-container stack is healthy and remains running.

The next bounded action requires authorization to establish the missing Default Group through the supported API and reconcile the application ACL to the reviewed peer set, without broadening permissions or changing unrelated consumers. Then repeat the deployment preflight, including current administrative write-role compatibility, recovery, peer/permission and source checks, before any authorized stop/start. Do not bypass either registrar prerequisite or change the approved candidate merely to make this preflight pass.

Stop here. No installation, Jellyfin configuration change or broadcaster playback is accepted by this report. Raw credentials/tokens, private source URLs, database contents and recovery archives are excluded.
