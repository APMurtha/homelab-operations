# Dispatcharr permanent streaming deployment — trusted release failed; original services restored

2026-11-17 UTC (2026-11-16 US/Eastern). Andrew's Rivendell, 10.10.20.30.
Latest approved release: `824d0be03af997762160e7bb7dd1fa497a5dfd9f`, branch `docs/udm-pro-max-migration-prep`.

**Latest status — 05:10 UTC: coordinated deployment FAIL. Original protected three-service runtime restored and healthy; API rollback incomplete.** The trusted guard published its generation and namespace grant, and the unprivileged relay became healthy. Managed backend readiness, registration, exports and gateway startup completed. The final running-contract verifier failed; offline replay reproduces `running_relay_tmpfs_missing` from Docker's mount representation. Scoped cleanup withdrew readiness and stopped all four services. The complete original protected source/unit baseline was restored through one authorized managed restoration start.

**One owned hidden DW English channel (ID 2) and stream (ID 2) remain.** The rollback precheck refused before any API mutation because the channel collection omitted the hidden channel. Fresh detail GET confirms its fields still match the ownership receipt. Cleanup stopped at this discrepancy; no deletion, forced reconciliation or candidate retry followed. This is not a completed application-state rollback.

**NO-GO for Jellyfin integration, playback or another deployment.** Separate review/authorization is needed for the running tmpfs verifier and hidden-channel inventory/rollback handling. No Jellyfin changes or broadcaster requests were initiated.

Sections 1–13 retain historical results. **Section 14 records this coordinated attempt and the final retained state.** Default Group ID 2 and the approved exact ACL remain in place.

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


## 13. Corrected candidate deployment — FAIL; original stack restored

### Approval, preflight and staged-source reconciliation

The owner authorized one controlled candidate attempt at `776f9843228148fe3d1fd744089f97fb0c82601e` and a conditional scoped rollback, then explicitly confirmed exclusive administration before the stop. Reviewed the corrected [verifier report](dispatcharr-permanent-streaming-verifier-fix.md), implementation report, prior failure history and candidate README.

Fresh live preflight at **02:51:09–02:51:29 UTC** passed the original three healthy services, idle Redis/media processes, zero recordings/channels/streams, original accepted image/security/namespace contracts, all nine installed persistence/admission hashes and root:root 0644 modes, current admin authentication (level 10), exactly one **Default Group ID 2**, unique locked streamcopy/MPEG-TS **profile ID 1**, exact approved ACL and Jellyfin peer **172.20.0.2**. The canonical ACL digest remains `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e`. Original application/gateway returned HTTP 200. Original systemd 20 drop-in and nine-minute start timeout were unchanged; 30 was absent.

The locally retained patched image remains `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. No pull/build occurred. Rivendell rollback references under `/root/dispatcharr-minimal-recovery-20261116T051539Z` remain readable with recorded hashes. The **independent checkpoint is on Denethor**, at `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`; all three archive hashes were reverified locally. An initial read mistakenly looked for that path inside Rivendell and found it absent; the documented independent copy was then verified at its actual Denethor location. No recovery archive was created, copied, restored or published.

At **02:53:16–02:53:17 UTC**, the complete old staged tree was checked against `f7115a8`: exactly 41 files, no unreviewed additions or drift, expected ownership/modes. Only nine reviewed files were replaced or added to obtain the corrected **44-file** tree. All 42 manifest entries plus manifest/validation receipt match the approved correction commit byte-for-byte. Quiet Compose validation passed. Original base inputs remained untouched.

Retained private relay/registrar configuration was verified against current schema fields, authorized source equality, current guard digest, 12-second deadlines, current owner credentials, approved ACL digest and exact Jellyfin peer. Both files retain UID/GID 1000, mode 0400. Runtime child/export directories had reviewed ownership and modes, empty contents and no symlinks. No credentials/private source values were rewritten or published. The export directory remains only a prepared empty directory; Jellyfin settings were not touched.

After exclusive-administration confirmation, health/source/unrelated identity and Redis/media idle checks were repeated immediately before the sole stop at **03:05:16 UTC**. No active consumer was disrupted.

### Controlled timeline and stopped-container acceptance

| UTC | Result |
|---|---|
| 03:05:16–03:05:20 | One `systemctl stop dispatcharr-stack.service`; only original three dedicated containers stopped. |
| 03:05:30–03:05:31 | Patched AIO, managed relay and gateway staged stopped using reviewed Compose flags: no pull/build/dependencies; VPN owner retained. |
| 03:05:31 | **Corrected stopped contract PASS**: exact `HostConfig.Tmpfs`, six exact relay bind mounts, immutable image references, privileges/resources and shared namespace. Guard and corrected unrelated comparator pass. |
| 03:05:47 | Reviewed 30 drop-in installed root:root 0644; native systemd verification, candidate/private input verification, daemon-reload and effective order pass. |
| 03:06:08 | One candidate start submitted through systemd. |
| 03:06:09–03:06:24 | Unchanged resource admission passes in **15.003 s**; all prestart commands exit 0. |
| 03:06:24 | Managed lifecycle start begins after guard reapplication, runtime preparation and stopped contract. |
| 03:06:30.862–03:06:31.299 | Relay starts, prints its generic refusal and exits 1; no OOM or engine error. |
| 03:06:31.028 | Patched AIO starts briefly; gateway remains created/stopped. |
| 03:06:31–03:06:32 | Lifecycle fails while waiting for first service group; existing scoped `ExecStopPost` completes successfully. All four dedicated containers stopped. |
| 03:08:58–03:09:01 | Rollback preconditions verified; stopped relay removed without volume deletion; original AIO/gateway staged stopped, 30 removed, native original-unit verification and daemon-reload pass. |
| 03:09:23 | One authorized rollback start submitted for the original stack. No candidate retry. |
| 03:09:38 | Original admission passes in **15.002 s**. |
| 03:09:39 / 03:09:45 / 03:10:09 | Original VPN / original-image AIO / original gateway start. |
| 03:10:40 | Original unit active/exited, Result=success. Stopped-to-restored-active interval: **5 minutes 20 seconds**. |
| 03:11:11 | Fresh supported API verification confirms prerequisites retained and no integration records. |
| 03:11:22 | Final backend/security/unrelated-service rollback acceptance PASS. |

Native unit/effective-order verification retained inputs → original admission helper → guard apply → runtime preparation → corrected stopped verification → lifecycle start → running verification. Base Type=oneshot, restart=no, original 540/240-second timeouts and admission thresholds were preserved. Candidate `ExecStartPost` running verification was **not reached**, and is not claimed as a pass.

Admission samples:

| Purpose / elapsed | Idle | Steal | Load1 | Streak |
|---|---:|---:|---:|---:|
| Candidate / 5.002 s | 97.784% | 0.000% | 0.51 | 1 |
| Candidate / 10.003 s | 96.777% | 0.050% | 0.47 | 2 |
| Candidate / 15.003 s | 86.737% | 0.101% | 0.43 | 3 |
| Rollback / 5.001 s | 96.933% | 0.000% | 0.15 | 1 |
| Rollback / 10.002 s | 96.472% | 0.000% | 0.14 | 2 |
| Rollback / 15.002 s | 96.828% | 0.050% | 0.13 | 3 |

### Relay startup failure and security incompatibility

The corrected stopped tmpfs verification succeeded on actual Docker metadata; the earlier mount-enumeration defect did not recur. All candidate source and private-file checks, admission and prestart checks passed.

The managed relay runs as **UID/GID 1000**, with all capabilities dropped. The unchanged accepted `/run/dispatcharr-guard` directory is **root:root 0700**, while its `ready` file is root:root 0644. The candidate bind-mounts that directory read-only at `/guard` and calls `Relay.check()` to read `/guard/ready` before publishing its endpoint. Directory mode 0700 denies traversal to UID 1000 regardless of the file’s 0644 mode. A bounded host-side read-only probe using UID/GID 1000 and no supplementary groups confirmed **PermissionError**; no container was launched for diagnosis.

This is a confirmed blocking compatibility gap between the unprivileged candidate and the existing guard interface. The relay log deliberately reports only `Relay refused; private details withheld.` and provides no traceback; its exact caught exception is not recoverable from that message alone. The confirmed guard-read failure and source startup order explain a concrete refusal path without claiming an unrecorded traceback or excluding every possible earlier exception.

No guard permission, ACL, policy, private configuration, privilege or timeout was relaxed. No running metadata acceptance, rolling-budget runtime acceptance, endpoint registration/export acceptance or four-service application acceptance is claimed. The reviewed rolling-budget/resource source and image identities remained unchanged, but the service did not become healthy.

### Registration outcome and safe scoped rollback

The first Compose wait failed before `backend.py` and `register.py` could be invoked by the lifecycle. `/docker/dispatcharr-iptv/data/permanent-streaming` remained absent: no ownership ledger, write-ahead API journal, commit marker or uncertain registration write. The gateway never started. No opaque endpoint was registered and no exports were generated. Candidate AIO logs showed no migration application/start marker or traceback; the subsequent restored DB verification confirmed the original 184-row migration fingerprint exactly.

Rollback was limited to the approved procedure after verifying all dedicated components stopped, no control process remained, registration never began, original nine files were intact, the 30 drop-in matched its reviewed hash, exact guard was present, VPN owner retained, and unrelated comparator passed. Only the stopped new relay was removed, without `-v`. Only original-image AIO/gateway were recreated stopped against original base+minimal Compose inputs. Only the new 30 drop-in was removed. Native unit verification and daemon-reload restored the original lifecycle; one systemd start restored the original three-service stack through unchanged admission/guard checks.

No Redis/DB reset, data/volume deletion, archive restore, image pull/build, direct protected-container start, candidate retry, Docker-wide restart, host/VM operation, firewall/VPN change, Jellyfin mutation or playback occurred.

### Final verified protected state

- Original VPN, original-image AIO and original gateway are healthy, restart=no and RestartCount 0; stack and guard units active/exited with Result=success.
- PostgreSQL/migration checks and authenticated Redis PING pass. Both uWSGI workers have fresh Redis-backed heartbeats (ages **0.310 / 0.014 s**, TTL 30), with the same web-worker master. Default and DVR Celery respond. Migration inventory remains **184**, fingerprint `b00f51e91c5b882cd84d3b2579d074ca`.
- Application and gateway HTTP **200/200**. No observed media processes, startup traceback, migration failure or recurring Redis-reference error. Provider audit remains one built-in account/profile, zero unexpected accounts/profiles and zero EPG sources.
- Supported fresh API reads confirm group **2**, locked profile **1**, current admin access and exact ACL digest unchanged. Streams/channels/recordings remain **0/0/0**. No stale binding or duplicate record exists.
- Exact nftables/ready-marker and original running-contract verification pass. tun0 default routing, OUTPUT DROP, embedded-DNS rejection, loopback resolver and disabled IPv6 pass. No new externally published port or Docker network remains.
- The **corrected four-service diagnostic comparator** confirms all genuinely unrelated container IDs, images, HostConfig hashes, start times, running/health states, restart policies/counts, Docker process and network identities unchanged. Existing unrelated stopped/unhealthy workloads remain in their preflight states; no repair was attempted. Jellyfin remains healthy, peer **172.20.0.2**, Live TV configuration hash unchanged.
- Original VPN owner identity and HostConfig hash retained. AIO/gateway identities changed because of scoped recreation; their original image pins, data and accepted three-service contract are restored. No claim of original AIO container-ID/HostConfig byte identity is made.

Final running identities:

| Service | Container ID | Image ID |
|---|---|---|
| rivendell-iptv-vpn | `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e` | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` |
| dispatcharr | `3b5e61e63bd738548bfc222c7d61ded655ffb5d7de391cde636b1ecc54b9d18c` | `sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` |
| rivendell-iptv-gateway | `6213d7ec435595be58b980935e639f5835225817cdb986c5d445d37005afebba` | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |

### Exact verified installed candidate inventory

The following inactive source files were verified both during reconciliation and final rollback acceptance. Paths are relative to `/docker/dispatcharr-iptv/permanent-streaming/`; they remain root:root 0644 under 0755 directories. Original nine persistence/admission hashes remain exactly as recorded in section 2. The immutable candidate image references remain those in the correction report; patched AIO and relay were staged from the same retained `14c837…cad21` image, while VPN/Caddy pins were unchanged.

| Candidate file | SHA-256 |
|---|---|
| `.gitignore` | `6feaded4e28ea86e001a6751b4e3d960e8b7c31b9616ff9936b79297086e809b` |
| `30-permanent-streaming.conf` | `3be80cb6197f1fa756aa9c7c477dc8064cb4fd0d6a6ec59ef5eb18bf7817cb70` |
| `Caddyfile` | `8b7b661f80ab157957480b330d96861d3980370fd1830d0cb36df93b79a08ba6` |
| `README.md` | `f3bbfb404331c95af9a7e5be9c3e1a75d24ea9c0c00caa689af84675fb42f779` |
| `accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `api-source-pins.json` | `036dd097e03ef536f3f0e1de53f3707c5ab5177fc2244dc71dce91400f637cdc` |
| `api.py` | `aabd860d76651e021ca5b61677c8c02b554f3ae5901f41072c9518434b1fca15` |
| `backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` |
| `base-input-pins.json` | `83395e6599724e46dee03bdcd791bf7a178355229cf001b5aae98a124f19fe08` |
| `bounded_server.py` | `ec8e615f721ee1b047b51a80537c39f1247b136503c5236ef5d975f4fc9c020d` |
| `compose.yaml` | `7587c2badc7c06b2bac59408964216d00f366b17109a6417caa38ba64399e51c` |
| `contracts.py` | `71da7561a97b279a058f1fe65477ab76864307cc4327ad487d061367ae9fc038` |
| `diagnostic_inventory.py` | `2e83b5e7a11f247ed7d8e382c64f62375aa4086ce517629c052be8b08ff16126` |
| `dns_worker.py` | `df7e483eaad95749fe5cc0ae97dd0d259c6e86b7896edca3cac9d62728870596` |
| `exports.py` | `460291da7961b9463420cec14c19648f4e33ad21eef82af271d3d1d830bb9c44` |
| `fetch_runtime.py` | `8b3595556c3061da17e5a018e07871238d786601e973625cde13f88ca91a3d27` |
| `files.py` | `314e4c70f7daf02bd6d1ce8a5bb8cc60690365d4507c3f99915ae2c5cf79723a` |
| `health.py` | `f4da54dece514ea24df5a6561ce52b883a1737213634b95bb1eab94a1b4ec6db` |
| `hls_relay.py` | `5eb958dbcf1ef6d2b92fa47ba4fb737511042486601969b955f7940241fb4b36` |
| `jellyfin.py` | `f328d3c5e26ca3465717b17376e6cc3a04f858595b08514e449064c68ade950f` |
| `lifecycle.py` | `2e2c7664cf7ea9fc6d2d547f1b8248b3a6734f32a332c12fcf7f9af4e2e6a7ed` |
| `manifest_telemetry.py` | `179a364baaf3a7fbde6c09082db0fc9df65639812a86e7139bc0c1ec32df5784` |
| `rate_budget.py` | `86b11daec92b621d2bb4d9288da78ea909976f5483c5aab4417a29961b22bd56` |
| `reference/Caddyfile.accepted` | `bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98` |
| `reference/trial_hls_relay.py` | `15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75` |
| `refresh_manifest.py` | `438fe72028cec2703111a109b8217fc01e8c3b8757d380c9b0af5cbb6f2c0a8d` |
| `register.py` | `20f0ed9ed1c44be718dbc2e1c8bb2147cde0d818152f984d2080d2cb3bc03652` |
| `registration-config.schema.json` | `7edb2204f1be1380dd9c2168c2d6021da8882c69b2abf89b401aecdfa8ed413b` |
| `relay-config.schema.json` | `2adf89698e2b9038e97a69279715d1a62dc1d7367d7ffcb2c926dc3a6e898d62` |
| `relay_main.py` | `b273dd21d1ea8a89010a7304138046d7426c61a98d8aaeb0be3188cd38e69473` |
| `telemetry.py` | `d5ab9d69bd66b364b0cdc2c0b61af225e75998cbc587bac2b61fdb16823c5ffa` |
| `tests/fixtures/relay-stopped-18bdf54.json` | `cbd455cfa1797347362e0a96244886398ea3388e59a013cd7a315bf59cbd884c` |
| `tests/run-offline.sh` | `369749fc567eb1545729a56d8a39ca11f33d92ebfb14dab336020cdd9efdd9b5` |
| `tests/test_candidate.py` | `8142e68571d5549ce62c4e6d5cb20aeb42f7cb2c85122a951100591ad4117b28` |
| `tests/test_contract.py` | `1a1fa266cce482175113ff8ce35fd9cccc92a4f2e56bc923c9522347dad35a9f` |
| `tests/test_gateway_native.py` | `6d5b298927c27315f057182507098aac4af4b7d59cf8cb0d37a4a3d25e456dee` |
| `tests/test_inventory.py` | `535c0427773fa268aa26a6ef5d35d7e02ecfeb1bff6fbaf10c5cbbd4ac2caf79` |
| `tests/test_network.py` | `6079fe5c8a6c08b6c0bbb2eb6d21651ec84c8a410dc78b5f25c01ce884acd133` |
| `tests/test_provenance.py` | `d70a03f532ba59b1047eb962b539accc3d78cecf942c8ddc371d5ddfd1ff337c` |
| `tests/verify_units.py` | `54321e61b45dd632642ab60eb6070959e065fb7aed1c3cfc212777553f40086e` |
| `verify.py` | `af6657dee883b297f281e0997e254886df2d5f28ec76955293c45b7e1d72ebb2` |
| `verify_binding.py` | `cf9d079d720c952c7a2368a568d9d73595f12cd05889aac33775ef0cacc1c4f8` |
| `manifest.json` | `3d5ae000603fc8d3bf7796deb996c39f863ab877f45160edd22ebf9a65648ae4` |
| `validation-results.json` | `70bebbb697b3804c238cd45f0309ddd5a0ff518b3e2a3c3fa124afebc011f5a5` |

### Retained evidence, blockers and decision

Root-private intent/command, source hash, stopped-contract, installed-unit, failure-log/inspect, rollback-precondition, backend and final-verification receipts are retained under `/docker/dispatcharr-iptv/private/permanent-deployment-776f984-20261117/` (0700 directory, 0600 files). Supported API prerequisite/rollback receipts remain under the existing root-private prerequisite directory. Raw credentials, private broadcaster references, tokens, endpoint values, database contents and recovery archives are excluded from publication.

The corrected 44-file candidate and private configuration remain **staged but inactive**. The 30 drop-in and relay container are absent, runtime directory was removed by normal systemd failure cleanup, registration state is absent and the export directory remains empty. No candidate source change was made during this deployment task.

**Permanent deployment FAIL; documented rollback PASS. NO-GO for Jellyfin integration or playback.** A separately reviewed correction must make the unprivileged relay’s guard-read interface compatible with the accepted protection, with permission-faithful startup tests, before a new candidate or deployment can be authorized. Preserve the exact host guard and existing security restrictions; do not chmod the guard or grant capabilities merely to bypass this failure. A future attempt requires fresh preflight and reconciliation of the retained inactive candidate.

Stop with the original protected three-service stack healthy and running. No further attempt is authorized by this result.


## 14. Coordinated trusted-guard release 824d0be — FAIL; protected runtime restored

### Authority, exact release and fresh preflight

The owner authorized one matched installation/deployment attempt and one safe original-baseline restoration start if required, and confirmed no conflicting administrative work. The exact approved commit was checked out without candidate edits. Reviewed the trusted implementation/design, previous deployment report, candidate README and transition manifest. SSH access used Andrew's selected Rivendell profile; the actual host was verified. VM or hypervisor operations were not performed.

Fresh checks at 04:39–04:42 UTC passed before disruption:

- Original VPN/AIO/gateway healthy and idle; zero live-channel Redis keys, media processes, recordings, channels and streams. Existing input, exact guard and running contracts passed.
- All nine original persistence/admission files and all 17 original protected hashes matched. The prior inactive candidate matched its 44 expected hashes without unrelated drift.
- Current administrative API credentials authenticated with the required role. Exactly one Default Group, ID 2; unique locked streamcopy/MPEG-TS profile ID 1. No historical credentials or database import was used.
- Exact ACL: STREAMS `127.0.0.1/32,10.10.20.30/32,172.16.70.1/32,172.20.0.2/32`; M3U_EPG and XC_API each `127.0.0.1/32`. Canonical digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e` matched the registrar.
- Jellyfin peer remained `172.20.0.2`; export ownership/access and private configuration were checked without exposing their contents. Jellyfin Live TV configuration hash remained `28d72351abb46aac33dff87e30ff4bf58ae44122d63b6e3197b26a843540a71b`.
- Immutable VPN, patched AIO/relay and gateway images were already local. No build or pull occurred.
- Existing root-private rollback artifacts remained readable and matched recorded hashes. The independent checkpoint on **Denethor**, `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`, passed all three archive hash checks. No new backup or restore exercise occurred.
- Exact host nftables policy, VPN default route through tun0, OUTPUT DROP and embedded-DNS rejection, loopback-only resolver configuration and disabled IPv6 passed. The installed VPN health command passed without fetching broadcaster media.

### Systemd compatibility gate

Rivendell uses systemd `255.4-1ubuntu8.18` and unified cgroups. Existing journal execution evidence established root UID/GID and the exact `/system.slice/dispatcharr-stack.service` and `/system.slice/dispatcharr-egress-guard.service` hook contexts required by the publisher. Delegate and PrivateUsers were disabled, both units used system.slice, and no RootDirectory/RootImage remapping applied. Existing ordering/dependencies and original drop-in restoration inputs were inspected.

Native `systemd-analyze verify` passed for isolated proposed original-three-service and permanent-four-service unit fixtures before the stop. Installed systemd documentation supported the proposed runtime-directory preservation behavior. The actual coordinated installation was verified again before reload: exact prestart ordering, unchanged admission thresholds/timeouts, guard withdrawal hooks, and public runtime-directory mode/preservation. No running-unit mutation was used to probe cgroup assumptions.

### Installation integrity and stopped contract

All **65 installed-target mappings** matched the approved transition manifest after staging and installation of the 30 drop-in. The first stage installed 64 targets and changed/added 24 paths; the remaining reviewed 30 drop-in completed the map. No hash was regenerated to accept drift. The exact mapping and hashes are reproduced below; source provenance is the immutable approved commit.

The existing base units, policy, WireGuard configuration, DNS and persistent application data were preserved. Public `/run/dispatcharr-guard-status` was prepared root:root 0755, empty; `/run/dispatcharr-guard` remained root:root 0700. No readiness/grant was manually created. Only the approved private relay field was migrated from `ready_file` to `guard_status_dir=/guard-status`; private credentials/source settings remained private and unchanged. Runtime/export ownership and scoped modes passed.

Only patched AIO, relay and gateway were staged stopped; the VPN-owner container and Docker network were retained. The stopped verifier passed the six exact read-only/bounded relay bind mounts, new `/guard-status` interface, namespace, privileges/resources and exact `/tmp` `HostConfig.Tmpfs` configuration. Native unit verification and effective loaded-command ordering passed before the sole managed candidate start.

### Timeline and admission

All times UTC on 2026-11-17. There was one candidate managed stop/start cycle, zero candidate retries and one separately authorized original restoration start.

| Time | Event and result |
|---|---|
| 04:44:45–04:44:49 | Original systemd-managed stop; only the three dedicated containers stopped; owner/network retained |
| 04:45:17 | Coordinated files staged; private schema migration and permissions pass |
| 04:47:34–04:47:36 | Patched AIO/relay/gateway staged stopped; complete stopped contract pass |
| 04:47:57–04:47:58 | 30 drop-in, all 65 hashes, native/effective unit ordering and reload pass |
| 04:51:16 | Sole candidate `systemctl start` submitted; early withdrawal and input checks pass |
| 04:51:16–04:51:31 | Unchanged resource-admission helper passes in **15 seconds** |
| 04:51:31–04:51:32 | Guard application, publication, lifecycle preparation and prestart pass |
| 04:51:32–04:52:45 | Managed lifecycle start exits 0 after backend/relay readiness, registration, export generation and gateway startup |
| 04:51:54 | Observed VPN/relay healthy, matching published generation/grant, transaction granted/unblocked; relay fetch count 0 at this observation |
| 04:52:45 | Final `verify.py running` exits 1; candidate unit fails |
| 04:52:45–04:52:48 | Scoped failure cleanup exits 0, withdraws public records and stops all four protected services |
| 05:00:04 | Rollback preconditions established: exact kernel policy, all protected stopped, readiness withdrawn, known committed API state |
| 05:02:45–05:02:48 | Complete original protected baseline restored and native/prestart verification passes |
| 05:04:05 | Sole authorized original managed restoration start submitted |
| 05:04:05–05:04:20 | Original admission helper passes in **15 seconds** |
| 05:05:19 | Original managed start completes; unit active/exited, Result=success |
| 05:08:08–05:08:10 | Conflict-checked API rollback precheck refuses before mutations: hidden channel absent from collection inventory |
| 05:09:41 | Read-only channel detail and stream reads match owned receipt; retained state established |
| 05:10:07 | Final original running/security/unrelated-state verification passes |

### Candidate startup results and verifier failure

The trusted interface resolved the prior root-private-directory traversal failure: the relay ran unprivileged, read the public status, pinned matching guard/grant generations, and became healthy. The trusted transaction reached granted/unblocked. The original private directory remained 0700. This demonstrates the managed publication/namespace/readiness path for this attempt; it does not establish continuous kernel/VPN attestation or instantaneous revocation. The approved design's asynchronous cleanup and check-to-use limitations still apply.

The approved lifecycle returned success. Its established checks include PostgreSQL, authenticated Redis, both uWSGI worker heartbeats, Default/DVR Celery, relay readiness, supported API registration/readback, local exports and gateway readiness in that order. The owned ledger contains one stream ID 2 and hidden channel ID 2, number 9001, group 2/profile 1; no pending journal or commit marker remained. Generated M3U/XMLTV files exist and remain inactive after cleanup. The final four-service running-contract acceptance **did not pass**; lifecycle success must not be reported as complete deployment acceptance.

The final verifier emitted its generic refusal. A read-only offline projection of captured Docker metadata reproduces **`Refusal:running_relay_tmpfs_missing`**: the running container's exact `/tmp` configuration exists in `HostConfig.Tmpfs`, while Docker's `Mounts` array contains the six bind mounts and no `/tmp` entry. The stopped check accepted that representation; the running check still demands a tmpfs Mounts entry. The generic outer exception did not expose its original inner traceback, so the offline result identifies the reproduced contract incompatibility rather than an unmasked production traceback. No verifier bypass or candidate correction was made.

No broadcaster fetch or playback command was issued. Relay telemetry recorded zero fetches at 04:51:54, before registration completed; runtime files were subsequently removed by normal systemd cleanup, so this report does not assert a final lifetime counter that was not retained. Initial health/acceptance checks used the reviewed non-media paths.

### Scoped restoration and unresolved API cleanup

After cleanup, all four protected containers were stopped, both public records were absent, the transaction was revoked/unblocked, and the kernel firewall still matched exactly. Private failure/transaction/ownership evidence was preserved. No blocked transaction was cleared.

The complete **original** protected baseline was restored, including original guard source, minimal verifier and resource-admission drop-in, not merely the original AIO image. All 17 original protected hashes and nine persistence/admission files passed. Reviewed new guard/30 drop-ins and cleanup helper were removed; private relay configuration was restored only after comparison with this attempt's captured after-image. The stopped relay container was removed without deleting volumes. Original AIO/gateway were staged stopped, the VPN owner/network retained, native unit/prestart checks passed, and systemd was reloaded before the one original managed restoration start.

**Ordering deviation:** automatic failure cleanup had already stopped the backend before API undo could run. The compatible original runtime was therefore restored first, with the committed ownership ledger and no pending API journal established beforehand. API undo then required a fresh exact comparison. It stopped at its inventory assertion before reaching the reviewed `rollback_owned` function or any DELETE/PATCH/POST mutation of application records.

Fresh supported API reads show one owned stream ID 2 matching its saved fields. The channel collection returns zero rows, while channel detail ID 2 exists, is hidden, and matches all owned fields; PostgreSQL independently reports one channel. The collection-based rollback assumptions therefore do not cover this observed hidden-channel representation. **Both owned records and the private ledger were retained.** No rollback completion receipt exists. Authentication token acquisition and reads occurred; no application record was deleted or altered by this rollback check.

Do not claim full application rollback PASS. The infrastructure/runtime restoration is verified, while application-state cleanup is **blocked pending separate authorization and reviewed hidden-channel handling**. The retained stream references the now-inactive relay; it is not a working permanent deployment. Do not delete its stream while leaving the hidden channel, reuse the stale binding, or force ledger removal.

### Final protected state and unrelated services

- Original VPN, AIO and gateway are healthy; restart counts 0. Original running-contract and exact host guard checks pass. Relay container and permanent 30 drop-in are absent; public readiness/grant records remain withdrawn. Root-private guard stays root:root 0700.
- Original admission/guard hooks are active; stack active/exited with Result=success. Final authenticated API reads also reconfirmed group 2, locked profile 1 and the exact approved ACL digest. The original source/unit baseline matches its 17 hashes, including the nine installed persistence/admission files listed in section 2.
- PostgreSQL responds; migration inventory remains **184**, fingerprint `b00f51e91c5b882cd84d3b2579d074ca`; `migrate --check` passes. No unexpected migrations or startup migration exceptions were found.
- Authenticated Redis PING passes. Two web-worker heartbeats were fresh (approximately 0.30/0.21 seconds old, positive TTL). Default and DVR Celery workers respond. Application HTTP and gateway health return **200**; no FFmpeg/FFprobe processes or startup tracebacks were observed.
- Exact nftables protection and VPN tun0 routing, DNS rejection/loopback resolver and disabled IPv6 pass after restoration. There are no added ports or Docker networks.
- Corrected four-service inventory comparison confirms every genuinely unrelated container's identity/configuration/start time and health, Docker process identity, and Docker network identities unchanged. Jellyfin is healthy; peer and Live TV hash match preflight. No Jellyfin setting was changed.
- The approved 45-file candidate remains staged but inactive. New private protocol metadata and empty public anchor are retained; they were not silently adopted or cleared. Generated local exports and ownership/transaction diagnostics are retained as inactive evidence. No tuner/provider points were changed in Jellyfin.

| Final service | Immutable image identity |
|---|---|
| VPN | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` |
| Original AIO | `sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` |
| Gateway | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |

The attempted patched AIO/relay image was `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. The VPN-owner container retained ID `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e` throughout. Original guard SHA-256 after restoration is `df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd`.

### Evidence, decision and remaining prerequisites

Root-private receipts, full diagnostics, captured API ownership/transaction data and private configuration comparisons remain under `/docker/dispatcharr-iptv/private/trusted-deployment-824d0be-20261117/` (0700 directory, 0600 files). Credentials, tokens, opaque endpoints, broadcaster references, transaction contents and recovery archives are excluded here.

**Deployment FAIL; original protected runtime restoration PASS; API rollback INCOMPLETE. NO-GO for Jellyfin integration/playback.** Before further deployment, separately review/fix the running Docker tmpfs representation check with strict exact tmpfs/bind restrictions, and reconcile the supported API's hidden-channel listing/detail behavior with registration and scoped rollback. Further authorization is required before removing the retained owned records or changing the candidate. A future deployment also requires fresh complete preflight and reconciliation of the inactive files/private schema. No automatic retry is authorized.

### Exact attempted installed-target hashes

These are the **attempted release** hashes verified before the candidate start, not a claim they remain active after original-baseline restoration. The source mapping is [the approved transition manifest](https://github.com/APMurtha/homelab-operations/blob/824d0be03af997762160e7bb7dd1fa497a5dfd9f/configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json).

Transition manifest SHA-256: `75d6fbb8357c515058eb4acb145b0920d363055a11782c875247f09bc3df5f6b`. Installed candidate manifest SHA-256: `797dcdd7230efb89c2d133443c6d6e4371700e567299744f54d4245fc7d42a69`. All 65 mapped files were root:root 0644.

| Installed target | SHA-256 |
|---|---|
| `/docker/dispatcharr-iptv/Caddyfile` | `bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98` |
| `/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py` | `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917` |
| `/docker/dispatcharr-iptv/compose.proposed.yaml` | `08585e417a257c22f7a207c8440c82bc009edc48ab641b097ce733cde553915d` |
| `/docker/dispatcharr-iptv/guard.py` | `d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/cleanup.py` | `bb1f7166cb6adeec352abdd2eccb21365c8ae61ff7892a0da028e4c1fee71432` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/compose.persistence.proposed.yaml` | `60a41dd431bd1b986a9f432ffecdd039e80eae6aea630322dab163bee66a8c9a` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/contracts.py` | `2ba2080ce45a2c72611f3c33c7341f921d44cdbc9d936ca9d1edd086622251dd` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/verify.py` | `a809936e8b31c265c00738d60d24064578b32c255759f16151a048cb95408de7` |
| `/docker/dispatcharr-iptv/permanent-streaming/.gitignore` | `6feaded4e28ea86e001a6751b4e3d960e8b7c31b9616ff9936b79297086e809b` |
| `/docker/dispatcharr-iptv/permanent-streaming/30-permanent-streaming.conf` | `55ed3a21aec684c70b0599be358a915d2b91ffdfe088bee7a338e1774ce1a1c9` |
| `/docker/dispatcharr-iptv/permanent-streaming/Caddyfile` | `8b7b661f80ab157957480b330d96861d3980370fd1830d0cb36df93b79a08ba6` |
| `/docker/dispatcharr-iptv/permanent-streaming/README.md` | `cee2b638b746340f45fea72fdfc1c52700f645341bee6eb42b72767d7d9203e0` |
| `/docker/dispatcharr-iptv/permanent-streaming/accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `/docker/dispatcharr-iptv/permanent-streaming/api-source-pins.json` | `036dd097e03ef536f3f0e1de53f3707c5ab5177fc2244dc71dce91400f637cdc` |
| `/docker/dispatcharr-iptv/permanent-streaming/api.py` | `aabd860d76651e021ca5b61677c8c02b554f3ae5901f41072c9518434b1fca15` |
| `/docker/dispatcharr-iptv/permanent-streaming/backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` |
| `/docker/dispatcharr-iptv/permanent-streaming/base-input-pins.json` | `425ebd00cbae9c21180037d404cf38a1bba2c419145d77beafda4029bdf48227` |
| `/docker/dispatcharr-iptv/permanent-streaming/bounded_server.py` | `ec8e615f721ee1b047b51a80537c39f1247b136503c5236ef5d975f4fc9c020d` |
| `/docker/dispatcharr-iptv/permanent-streaming/compose.yaml` | `3f1993c109a9e9e18a0da04616e3a09dd3a132c478f57af15cd99cceef2c27de` |
| `/docker/dispatcharr-iptv/permanent-streaming/contracts.py` | `2cfd3e900d5f91b00e95e3e576142ea15d46af56f4acd11f0ebb714dc032249e` |
| `/docker/dispatcharr-iptv/permanent-streaming/diagnostic_inventory.py` | `2e83b5e7a11f247ed7d8e382c64f62375aa4086ce517629c052be8b08ff16126` |
| `/docker/dispatcharr-iptv/permanent-streaming/dns_worker.py` | `df7e483eaad95749fe5cc0ae97dd0d259c6e86b7896edca3cac9d62728870596` |
| `/docker/dispatcharr-iptv/permanent-streaming/exports.py` | `460291da7961b9463420cec14c19648f4e33ad21eef82af271d3d1d830bb9c44` |
| `/docker/dispatcharr-iptv/permanent-streaming/fetch_runtime.py` | `8b3595556c3061da17e5a018e07871238d786601e973625cde13f88ca91a3d27` |
| `/docker/dispatcharr-iptv/permanent-streaming/files.py` | `314e4c70f7daf02bd6d1ce8a5bb8cc60690365d4507c3f99915ae2c5cf79723a` |
| `/docker/dispatcharr-iptv/permanent-streaming/guard_readiness.py` | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` |
| `/docker/dispatcharr-iptv/permanent-streaming/health.py` | `f4da54dece514ea24df5a6561ce52b883a1737213634b95bb1eab94a1b4ec6db` |
| `/docker/dispatcharr-iptv/permanent-streaming/hls_relay.py` | `171461eb4bb83170a83d4b52aeca90d3f7ebc5d8486b615cdf654b7fc98078f5` |
| `/docker/dispatcharr-iptv/permanent-streaming/jellyfin.py` | `f328d3c5e26ca3465717b17376e6cc3a04f858595b08514e449064c68ade950f` |
| `/docker/dispatcharr-iptv/permanent-streaming/lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` |
| `/docker/dispatcharr-iptv/permanent-streaming/manifest.json` | `797dcdd7230efb89c2d133443c6d6e4371700e567299744f54d4245fc7d42a69` |
| `/docker/dispatcharr-iptv/permanent-streaming/manifest_telemetry.py` | `179a364baaf3a7fbde6c09082db0fc9df65639812a86e7139bc0c1ec32df5784` |
| `/docker/dispatcharr-iptv/permanent-streaming/rate_budget.py` | `86b11daec92b621d2bb4d9288da78ea909976f5483c5aab4417a29961b22bd56` |
| `/docker/dispatcharr-iptv/permanent-streaming/reference/Caddyfile.accepted` | `bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98` |
| `/docker/dispatcharr-iptv/permanent-streaming/reference/trial_hls_relay.py` | `15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75` |
| `/docker/dispatcharr-iptv/permanent-streaming/refresh_manifest.py` | `438fe72028cec2703111a109b8217fc01e8c3b8757d380c9b0af5cbb6f2c0a8d` |
| `/docker/dispatcharr-iptv/permanent-streaming/register.py` | `20f0ed9ed1c44be718dbc2e1c8bb2147cde0d818152f984d2080d2cb3bc03652` |
| `/docker/dispatcharr-iptv/permanent-streaming/registration-config.schema.json` | `7edb2204f1be1380dd9c2168c2d6021da8882c69b2abf89b401aecdfa8ed413b` |
| `/docker/dispatcharr-iptv/permanent-streaming/relay-config.schema.json` | `94cf3990b3e8f3d6237f7ef09f832b01b12f3fe8c8d529c44662e4b12076cf8b` |
| `/docker/dispatcharr-iptv/permanent-streaming/relay_main.py` | `830c87685643af37b9f008640b457d1a4e77bdf1fdef554f36fd82cec589f356` |
| `/docker/dispatcharr-iptv/permanent-streaming/telemetry.py` | `d5ab9d69bd66b364b0cdc2c0b61af225e75998cbc587bac2b61fdb16823c5ffa` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/fixtures/relay-stopped-18bdf54.json` | `cbd455cfa1797347362e0a96244886398ea3388e59a013cd7a315bf59cbd884c` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh` | `238ed027c00afe6c52e0c42294e305259f42dba5fc2ff2335ef5222f9101823d` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_candidate.py` | `45e13af50ad9e76abd6f52cbd940ce6033831aa0622089851b09ad944441fdba` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_contract.py` | `1cfcaed0882b06dae1ce7f2f48f8b8ca7ab64c277a8f694c289ef5b840ba2082` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_gateway_native.py` | `6d5b298927c27315f057182507098aac4af4b7d59cf8cb0d37a4a3d25e456dee` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_inventory.py` | `535c0427773fa268aa26a6ef5d35d7e02ecfeb1bff6fbaf10c5cbbd4ac2caf79` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_network.py` | `952f1673076daae67f6c6e6ec413bafd9ec636c8f7327bf6828dbb0026bc666f` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/test_provenance.py` | `dee3b3a5360497574668d5eb9ad710c67f4e85ad7f2013357314cdbf4c194cfd` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/verify_units.py` | `ef4d2b9c51c2c0f30ee913324185803e4a24206ea74face082ac5fdd45036524` |
| `/docker/dispatcharr-iptv/permanent-streaming/validation-results.json` | `df2efedc9cb4f198ed52d684e3da9b5bc8622bbda7b0a7fc9216ad2329baf22a` |
| `/docker/dispatcharr-iptv/permanent-streaming/verify.py` | `9b6bb1eab509ae3d7c2e8d0143829ddd1b6b92e05b9340ed5c1bcdf99db0cfaa` |
| `/docker/dispatcharr-iptv/permanent-streaming/verify_binding.py` | `cf9d079d720c952c7a2368a568d9d73595f12cd05889aac33775ef0cacc1c4f8` |
| `/docker/dispatcharr-iptv/resolv.vpn.conf` | `847d06f745d54e604791fa452b44a992026df81ba0dbdf58d81a8d02dd9d7ce2` |
| `/docker/dispatcharr-iptv/security.py` | `e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2` |
| `/docker/dispatcharr-iptv/vpn-owner-gate.sh` | `e343e41632ece47165ecc6f2ae1f00779e92d77dd552329ef628807bab7ba523` |
| `/docker/dispatcharr-iptv/vpn-post-rules.txt` | `d48815495401014e7fcd43848af20259a13f1a59c3ac7882795c9fecace6ade4` |
| `/docker/dispatcharr-iptv/vpn-startup-gate.py` | `766879e875aa801c376adc44a65f02301dfd2c225acd29909c34da823b847ee7` |
| `/etc/systemd/system/dispatcharr-egress-guard.service` | `bde5207014fa24781d8cd1275a54dac056684299e498f4773fca2ed2e98cc174` |
| `/etc/systemd/system/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf` | `392994ee3a0eec4b87127b13aa1efb51ce058fd135fbbed52f17d30fde2dbefc` |
| `/etc/systemd/system/dispatcharr-stack.service` | `30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e` |
| `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` | `578e03101e64c14da217e3d77f5bed9e0dbfbab9dad24b3f077c6b3891aed023` |
| `/etc/systemd/system/dispatcharr-stack.service.d/30-permanent-streaming.conf` | `55ed3a21aec684c70b0599be358a915d2b91ffdfe088bee7a338e1774ce1a1c9` |
| `/etc/systemd/system/docker.service.d/50-dispatcharr-order.conf` | `c9beb54d2b2e6285013355f3a80dd6677ff7723d10e835f45c499f39fb9e581b` |
