# Dispatcharr permanent streaming deployment — staging failed; rollback verified

2026-11-17 UTC (2026-11-16 US/Eastern). Andrew's Rivendell, 10.10.20.30.
Approved candidate: `f7115a8339685ba3e5314d8e54a40f239c5e3723` on `docs/udm-pro-max-migration-prep`.

**Latest status — 02:33 UTC: permanent deployment FAIL; scoped rollback PASS.** The approved candidate failed its real stopped-container mount contract before any candidate container started. The original three-service deployment was restored through the unchanged systemd/admission path and is healthy. No registration, new lifecycle drop-in, Jellyfin configuration change or broadcaster playback occurred.

**NO-GO for deploying candidate `f7115a8` or proceeding to Jellyfin integration/playback.** Its verifier needs a reviewed correction for Docker's stopped-container tmpfs representation and a new real-metadata regression before another deployment is authorized.

Sections 1–11 retain the earlier preflight/prerequisite history. Section 12 records the resumed deployment, precise failure, authorized rollback and final state. The prerequisites remain corrected; the new blocker is in the candidate contract.

**Historical deployment attempt — stopped before installation or disruption.** Two mandatory prerequisites fail: no existing Default Group and an application network ACL incompatible with the approved registrar. The original healthy three-container stack remains running. No stop/start authorization was consumed and no rollback was needed.

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

**Blocker B — network ACL mismatch.** The current application policy does not satisfy the registrar's exact-peer contract. The stored `network_access.value` was an empty object (`{}`), not an explicitly populated peer policy. The earlier “one configured entry” wording counted an empty-string fallback and was incorrect; it is corrected here. The empty object did not satisfy the registrar’s explicit STREAMS/M3U_EPG/XC_API contract. This is a compatibility failure, not a claim that the accepted running baseline has become unsafe. No policy was broadened, normalized or otherwise changed to force success.

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

## 10. Historical decision before prerequisite correction

**NO-GO for permanent deployment, Jellyfin integration or playback.** The existing protected three-container stack is healthy and remains running.

The next bounded action requires authorization to establish the missing Default Group through the supported API and reconcile the application ACL to the reviewed peer set, without broadening permissions or changing unrelated consumers. Then repeat the deployment preflight, including current administrative write-role compatibility, recovery, peer/permission and source checks, before any authorized stop/start. Do not bypass either registrar prerequisite or change the approved candidate merely to make this preflight pass.

Stop here. No installation, Jellyfin configuration change or broadcaster playback is accepted by this report. Raw credentials/tokens, private source URLs, database contents and recovery archives are excluded.

## 11. Authorized prerequisite correction — 2026-11-17 UTC

### Original state and scope

The owner explicitly authorized only creation of Default Group, an exact application ACL update, verification and repeat preflight. The owner also confirmed no conflicting administrator and no other device relying on M3U/EPG or XC API access outside the approved peers. API inventories and Redis/process checks found zero streams, channels, recordings and active Dispatcharr media consumers. No unexpected consumer or configuration drift was found.

The approved `f7115a8339685ba3e5314d8e54a40f239c5e3723` candidate tree is byte-for-byte unchanged; all 39 source/test manifest entries pass. Before changes the group inventory was empty, the existing `network_access` setting was record **6** with value `{}`, and exactly one locked active FFmpeg streamcopy/MPEG-TS profile existed. Original migration count/fingerprint, images, nine installed protection hashes and the original unit/drop-in state matched the accepted baseline.

### Exact changes and fresh verification

| UTC | Action/result |
|---|---|
| 02:11:22 | Original group inventory, ACL record/value, relevant identities and profile baseline captured privately. |
| 02:12:40 | One `POST /api/channels/groups/` with name `Default Group`; returned **ID 2**. Fresh detail and inventory GETs verify ID/name and exactly one group, custom/manual, zero associated channels. |
| 02:13:32 | One `PATCH /api/core/settings/6/` changing only `value` to the three exact authorized ACL fields. Fresh GET verifies exact stored values and unchanged record identity/other fields. Hash comparison verifies all unrelated settings unchanged. |
| 02:14:19 | Repeated live stack, source, protection, peer, idle-state, image and recovery-access preflight passes. |
| 02:15:23 | Fresh API preflight passes using the unchanged approved registrar validation functions; application/gateway HTTP 200. |

Committed ACL:

```text
STREAMS = 127.0.0.1/32,10.10.20.30/32,172.16.70.1/32,172.20.0.2/32
M3U_EPG = 127.0.0.1/32
XC_API  = 127.0.0.1/32
```

Canonical digest, computed exactly as the approved registrar does—SHA-256 of `json.dumps(value, sort_keys=True, separators=(',', ':'))`:

```text
cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e
```

The private registrar-preflight metadata contains this exact `expected_network_access_sha256` and `jellyfin_peer_ipv4 = ["172.20.0.2"]`; fresh API values pass the approved `network_check` and digest comparison. The full deployment registration-credential configuration is **not installed**—during a future authorized installation it must use this verified digest and current credentials. No deployment credential file was created merely to claim configuration acceptance.

No broad CIDR was added. Every configured CIDR is an exact /32 peer. There were no unrelated keys in the original ACL object; the update preserved all unrelated settings and record fields. The custom group is associated through the API’s normal built-in custom-account behavior; no provider account was created. The account inventory remains one, and profiles are unchanged.

### Repeat deployment preflight

| Check | Result |
|---|---|
| Exactly one Default Group | PASS, ID 2, name verified by detail and list reads |
| Exact approved ACL / canonical digest / registrar validation | PASS |
| Current accepted-AIO API authority | PASS: owner user level **10**; authorized group POST and settings PATCH succeeded and were verified |
| Unique locked active FFmpeg streamcopy/MPEG-TS profile | PASS, **profile ID 1**, full profile inventory unchanged |
| Nine installed persistence/admission hashes and permissions | PASS, same hashes listed in section 2 |
| Approved permanent candidate | Unchanged; not installed |
| Exact patched image | Available locally at the reviewed `14c837…cad21` identity; not promoted |
| Current application and gateway | HTTP **200 / 200**; all three original containers healthy |
| Current nftables / namespace contract | PASS, accepted exact guard and running-contract checks |
| VPN/DNS/IPv6 | tun0 default route, OUTPUT DROP, embedded-DNS rejection, nameserver 127.0.0.1 and disabled IPv6 pass |
| Existing rollback and independent checkpoint | Accessible; three independent archive hashes match; no new backup or restore |
| Playback/recordings/channels/streams | Zero active Redis channel keys/media processes; API records all zero |
| Jellyfin peer | Still **172.20.0.2** |
| Docker, networks, protected/unrelated container identity | IDs, image IDs, HostConfig fingerprints, start times, health and restart counts unchanged |
| Jellyfin Live TV file | Original hash unchanged; no Jellyfin settings changed |
| Database schema / provider accounts | Still 184 migration rows with original fingerprint; one built-in account; no new source/EPG account |

The verified permanent export directory and four-service runtime are still installation-stage checks, not completed actions. The export directory remains absent; the existing Jellyfin configuration UID/GID 1000 is compatible with the candidate. No group/channel/stream IDs from a historical trial were imported: group 2 is the new API-created prerequisite, and the future registrar will discover it by name.

### Private rollback and outcome handling

Private records are retained under `/docker/dispatcharr-iptv/private/permanent-prerequisites-20261117/`: root:root directory 0700, files 0600. They include original ACL record/value and inventory, planned values/digests, one-shot mutation intents/responses, verified group and ACL after-images, unrelated-setting comparison hashes and repeat preflight receipts. Credentials, JWTs and private broadcaster URLs are excluded from this report and were not written into those task receipts.

There was **one group-creation attempt and one ACL-patch attempt**, both with known, freshly verified outcomes. No blind retry, uncertain-write reconciliation or rollback was required. If an authorized rollback is later needed, first confirm setting record 6 still equals this task’s exact committed value and group 2 remains unchanged and unused. Only then restore the captured original ACL value and remove only the task-created group through supported APIs; any conflict must stop the rollback. Do not overwrite newer changes or restore a whole database.

### Current decision and stop state

**Both previously reported prerequisites are resolved. GO for a separately authorized controlled permanent deployment**, with its normal fresh consumer/conflict, source, credential, recovery and staged-container checks. The future private registrar configuration must use the digest above. No remaining blocker was found in this task’s current non-disruptive preflight.

This task did **not** install candidate files or the 30 drop-in, prepare the four-service runtime, start a relay, register a channel/stream, generate exports, restart/recreate any container, run daemon-reload, invoke the admission gate or modify Docker/firewall/VPN policies. No stop/start cycle was used. No Jellyfin modification or broadcaster playback occurred. The original protected three-container stack remains running and healthy.

**Stop after this correction and verification. Do not automatically resume deployment.**

## 12. Resumed deployment — staging FAIL, rollback PASS

### Fresh preflight and authorized staging

The resumed deployment retained scope: only the protected Dispatcharr project and initial backend acceptance; no Jellyfin configuration or live playback. Fresh checks at **02:20:43–02:20:46 UTC** passed: original three containers healthy, idle Redis/media state, zero recordings/channels/streams, exact group **2**, admin level 10, profile **1**, exact approved ACL/digest, Jellyfin peer **172.20.0.2**, all nine installed persistence/admission hashes, current guard/namespace protections, retained patched image, and accessible recovery references. All candidate source bytes still match approved commit `f7115a8339685ba3e5314d8e54a40f239c5e3723`.

At **02:22:58 UTC**, exactly **41** approved source/manifest/validation files were staged under `/docker/dispatcharr-iptv/permanent-streaming/`, root:root directories 0755/files 0644. Private relay/registration JSON was prepared with current authorized values, UID/GID 1000 and mode 0400 beneath the root-private directory. No secret values are included here. Dedicated runtime and empty export directories were prepared with reviewed ownership; the quiet Compose config check passed. No running container changed during source staging.

### Timeline

| UTC | Action/result |
|---|---|
| 02:23:56 | Issued `systemctl stop dispatcharr-stack.service` once. |
| 02:24:01 | Original three containers stopped; VPN-owner identity, guard, Docker/networks and unrelated services retained. |
| 02:25:30 | Created only patched AIO, relay and gateway **stopped**, with no build/pull/dependency recreation. |
| 02:25:31 | Approved stopped-contract verification failed: `contracts.Refusal: unexpected_relay_mount`. |
| 02:28:06–02:28:08 | After read-only diagnosis, performed authorized rollback staging: removed only the stopped new relay, recreated original-image AIO/gateway stopped from original base+minimal files. Original prestart passes. |
| 02:29:12 | Submitted the single managed start, used for restoring the original deployment. No candidate startup retry. |
| 02:29:27 | Original admission helper exits successfully after 15.002 seconds; guard/prestart pass; original VPN starts. |
| 02:29:33 | Original-image Dispatcharr starts. |
| 02:29:56 | Original gateway starts after application health. |
| 02:30:27 | Original systemd unit active/exited, Result=success. |
| 02:31:52 | Fresh API confirms group/ACL/profile retained and zero streams/channels/recordings. |
| 02:33:23 | Final original-stack, protection and unrelated-identity verification PASS. |

The observed stopped-to-active interval was approximately **6 minutes 26 seconds**. There were no active consumers at preflight.

### Precise candidate failure

The relay's stopped Docker metadata correctly contains:

```json
{"HostConfig.Tmpfs":{"/tmp":"rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700"}}
```

At this stopped lifecycle stage, Docker's `Mounts` list contains the six bind targets `/exports`, `/guard`, `/runtime`, `/etc/resolv.conf`, `/opt/permanent` and `/run/credentials/relay.json`. It does **not** yet enumerate `/tmp` there. The approved `contracts.py` builds its allowed set with those targets **plus `/tmp`**, then demands exact equality with the `Mounts` targets for both stopped and running checks. Therefore it rejects the correctly configured stopped tmpfs representation before startup.

This is a candidate validation defect, not a missing tmpfs configuration or a reason to weaken its security requirements. The offline four-service fixture modeled a `/tmp` mount as already present; it did not reproduce this actual stopped Docker representation. The implementation missed that distinction. The actual staging check caught the defect before a candidate process could run.

No candidate verifier was edited or bypassed. No candidate container started; their initial StartedAt fields confirmed this. The registrar never ran, `/data/permanent-streaming` was never created, and there was no uncertain channel/stream API outcome. The reviewed **30** drop-in was **not installed**; native verification of a newly installed unit and daemon-reload were not reached. The original **20** drop-in and base unit remained unchanged throughout.

A surrounding diagnostic comparison also initially counted the newly created dedicated relay as an unrelated container because it reused the three-service exclusion list. A subsequent **read-only** comparison excluding all four intended dedicated names confirmed every genuinely unrelated container and Docker/network identity unchanged. This bookkeeping issue did not alter the approved verifier or the mount-failure result.

### Safe rollback and resource admission

Rollback preconditions were verified: all dedicated containers stopped, candidate AIO/relay/gateway never started, no registration state or uncertain API write, original unit/drop-in/base inputs intact, data untouched and exact guard present. Only the stopped new relay was removed, **without a volume-removal flag**. Original AIO/gateway were recreated stopped against unchanged original base+minimal Compose files; the VPN-owner container was preserved.

The only start request in this resumed task restored the original three-service deployment through systemd. The unchanged resource gate admitted:

| Helper elapsed | Idle | Steal | Load1 | Streak |
|---:|---:|---:|---:|---:|
| 5.001 s | 97.583% | 0.000% | 0.11 | 1 |
| 10.001 s | 98.140% | 0.050% | 0.10 | 2 |
| 15.002 s | 96.581% | 0.000% | 0.10 | 3 |

Native execution metadata confirms successful input verification, admission exit 0, original accepted guard reapplication and original prestart exit 0. These are **rollback admission results**, not successful admission of the four-service candidate. No threshold/timeout adjustment, manual protected-container start or repeated start was used.

### Final acceptance of restored state

- Original VPN, original-image Dispatcharr and original gateway healthy, restart=no, RestartCount 0. Stack and guard units active/exited, successful.
- All nine installed persistence/admission hashes remain exactly as listed in section 2; original accepted guard and running-contract checks pass.
- PostgreSQL/authenticated Redis pass. Both uWSGI workers have fresh Redis-backed heartbeats (0.778/0.922 seconds, TTL 29 each); default and DVR Celery respond. Migration check passes; 184-row fingerprint remains unchanged. No inspected startup traceback, migration failure or recurring Redis-reference exception.
- Application and gateway HTTP **200**. Group **2**, profile **1** and ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e` remain verified. Streams/channels/recordings remain **zero**.
- Dedicated tun0 default route, OUTPUT DROP, embedded-DNS rejection, nameserver 127.0.0.1 and disabled IPv6 pass. No new published port/network or firewall/VPN policy change occurred.
- All unrelated IDs/images/HostConfig fingerprints/start times/health/restart counts and Docker/network identities match preflight. Jellyfin's Live TV file hash remains unchanged; no Jellyfin action or playback occurred.

Final running identities:

| Service | Container ID | Image |
|---|---|---|
| VPN owner | `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e` | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` |
| Dispatcharr | `0c40d2a193994cb2b66a176fd51167562b7c75d7231ee56c7882d0872ccbd2bd` | `sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` |
| Gateway | `035022b00d4e669760f8716287e9c90303a8ed3731e2262642f39d54764b3aeb` | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |

AIO/gateway IDs and Docker HostConfig fingerprints changed because they were recreated from the original accepted Compose inputs during rollback; byte-identical old container configuration is not claimed. Their original image pins, data and required three-service security contract are restored. The original VPN ID and HostConfig fingerprint are retained.

### Retained artifacts and current decision

Root-private deployment intent, command, stopped-contract, rollback and final-verification receipts are retained under `/docker/dispatcharr-iptv/private/permanent-deployment-20261117/`. Raw logs/configuration, credentials, private source references and recovery data are excluded from Git/chat publication.

The staged approved source directory and private configuration remain **inactive** for diagnosis, with restrictive permissions. The new drop-in is absent, no relay container or registration state remains, and the prepared export directory is empty. Those files are not evidence of an installed/running permanent integration. The patched image remains locally retained; it was used only for stopped staging, never for a running producer. No volume/data deletion, Redis/DB reset, image pull/build, host/VM operation or Docker-wide restart occurred.

**Deployment FAIL; authorized rollback PASS. NO-GO for Jellyfin integration or playback.** Before another deployment, prepare and review a corrected candidate that validates the exact tmpfs specification from `HostConfig.Tmpfs` in the stopped state, distinguishes running mount enumeration appropriately, and still rejects missing/extra/unsafe mounts. Add a regression fixture based on this real stopped metadata, then obtain authorization for the new candidate and another bounded deployment. Do not simply remove the tmpfs security requirement or retry `f7115a8` unchanged.

Stop here with the original protected three-service stack healthy and running.
