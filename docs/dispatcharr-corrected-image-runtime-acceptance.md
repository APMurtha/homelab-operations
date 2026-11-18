# Corrected Dispatcharr image — isolated runtime acceptance

**PASS. GO for production image-binding review only.** The single authorized
attempt completed all eleven application tests with **0 failures, 0 errors and
0 skips**, retained every required completion checkpoint and had no socket-audit
refusal. Scoped cleanup and production preservation pass. No production image
binding, deployment, real provider activation or playback occurred.

| Identity | Value |
| --- | --- |
| Approved binding | `e5e8080dfbe8fc1d3c4fdb1b10a186dc8d41a540` |
| Build evidence | `e0da9ff06ab827f6eaf79397d15dd8ce6399fe10` |
| Immutable image | `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439` |
| Exclusive attempt | `corrected-20261118-c118f7fa` |
| Synthetic payload SHA-256 | `b544cc4b158cebd769d57d862e9475574fa7b028658e2bda3e2ae4b02c8f6fd2` |
| Removed test-container ID | `7042c4b0a8a8ba241f89f424c81a9e03eb3e04d97cbc6566fd213078077d9c61` |
| Sanitized results SHA-256 | `e68c3bea0818401d812a5be0645dcefe7c5298c50057049e8b043688b2c6eb0c` |

## Preflight, receipt reconciliation and one launch

The checkout was clean at the approved binding commit. Its reviewed file inventory,
source manifest, runner/admission/transport/diagnostic pins and all 23 synthetic
payload entries matched. Every mapped payload entry was independently compared
with its approved Git blob; account fixtures retained their reviewed hashes.
Staged private bytes and the complete payload digest were independently re-read.
No application, fixture or security source changed during the attempt.

NEST verified Andrew's selected Rivendell profile and SSH account murth/UID1000.
Effective logind KillUserProcesses=false and the unbounded session scope remained
compatible with detached execution. The owner confirmed no conflicting
administration before launch. Fresh protected-service/Jellyfin health, image
metadata, all 33 container/configuration fingerprints, network/volume inventories
and host capacity passed.

An initial historical comparison found seedboxapi restart count 2 -> 3 and a
start-time change to 10:53:51 UTC. Its ID, image and configuration were unchanged;
read-only inspection found it stable and the restart more than four hours before
the window. The cause was not investigated. This pre-existing counter difference
was recorded before adopting a fresh before/after baseline. No counters or
containers were altered, and there was no such change during the actual attempt.

The original root-private corrected-build receipts were re-read with ownership,
mode, no-follow and exact published SHA-256 checks. All eight receipts and the
original build log matched. Their successful image/source verification was
reconciled into the runner's existing build-receipt schema in the **new** private
workspace `/tmp/dispatcharr-runtime-corrected-20261118-c118f7fa`. Original receipts were not overwritten, and this conversion
was not presented as a new image scan. The approved runner subsequently performed
its own fresh eighteen-source verification.

Immediately before launch (2026-11-18T15:34:32Z), load was
0.41357421875, RAM 3,476,594,688
bytes and disk 7,685,967,872 bytes. The reviewed
transport launch was invoked **exactly once**; every subsequent execution monitor
used status for the same ID. The SSH launch returned while the detached supervisor
continued. No relaunch, rebuild, retag or retry occurred.

## Verification, stabilization and admission

Fresh image verification reaped its export process with exit 0 and matched **all
18 corrected source/readiness hashes** in **100.430s**.
The three corrected hashes and remaining fifteen hashes match the approved binding;
the complete observed dictionary is retained in the results JSON.

Fixed stabilization elapsed **120.484s**, within the unchanged
180-second ceiling. Capacity observations during that interval were:

| UTC, 2026-11-18 | Load 1m | RAM available, bytes | Disk available, bytes |
| --- | ---: | ---: | ---: |
| 15:36:30.009 | 4.4287109375 | 3,436,646,400 | 7,676,239,872 |
| 15:36:45.854 | 3.52685546875 | 3,456,573,440 | 7,676,162,048 |
| 15:37:01.574 | 2.74462890625 | 3,453,300,736 | 7,676,022,784 |
| 15:37:17.389 | 2.2158203125 | 3,446,124,544 | 7,675,969,536 |
| 15:37:32.968 | 1.7919921875 | 3,447,504,896 | 7,675,912,192 |
| 15:37:48.448 | 1.46240234375 | 3,446,804,480 | 7,675,879,424 |
| 15:38:03.988 | 1.13818359375 | 3,446,001,664 | 7,675,990,016 |
| 15:38:19.446 | 1.13525390625 | 3,445,280,768 | 7,675,924,480 |
| 15:38:29.503 | 1.2685546875 | 3,448,721,408 | 7,675,961,344 |

There was **one** final admission decision at
**15:38:29.521 UTC: PASS**. Load
**1.2685546875 <=2**, RAM
**3,448,721,408 >=2,147,483,648 bytes**, disk
**7,675,961,344 >=1,073,741,824 bytes**.
No predicate, threshold, deadline or source expectation changed.

The container was created at 15:38:30.268 UTC;
application completion and scoped removal were recorded by
15:39:18.272 UTC, **48.004s**
later. Application and container exit codes were both zero.

## Explicit application acceptance

| Requirement | Retained result |
| --- | --- |
| PostgreSQL / authenticated Redis | Completed bootstrap checkpoints; PostgreSQL 17 and authenticated PING |
| UID1000 Django | Django 6.0.9, Python 3.13.17; actual application UID/GID1000 |
| Migrations | 184 rows; migration fingerprint matches previous isolated baseline |
| Real Celery startup/registration | Non-eager solo consumer with actual Redis; 57 tasks registered |
| Actual task execution | Six retained task results, including expected denials and successful queue probes |
| Security API / inactive refresh | Native API checks pass; ambient and explicitly requested inactive refresh denied |
| Partial failed creation | HTTP 403 authorization_refused; synthetic account ID 3 inactive/error, owned readback, one unresolved intent, no blind retry |
| Authorized inactive discovery | Synthetic account ID 4 initially inactive; actual API and ORM group-association readback |
| Stable group identity | Xtream category `"1"` -> native group PK 3; persisted xc_id and imported stream FK agree |
| Selected import | Exactly one owned synthetic channel; unselected channels not imported |
| XMLTV / EPG / programme | Native EPGData ID resolved/read, stable tvg-id fixture.one and 1 programme(s) retained |
| Default/DVR queue probes | Actual task results on default Celery queue `celery` and DVR queue `dvr` |
| uWSGI / backend | Two actual workers, fresh Redis-backed heartbeats and HTTP 200 |
| DW English compatibility | Synthetic DW channel 9001 snapshot unchanged; no playback |
| Authorization permissions | Actual UID1000 private-policy denial/public projection; five negative states rejected; actual revocation bootstrap checks |
| Credential redaction | Provider fixture username/password absent from captured application logs |
| Socket audit | No refusal record; successful process explicitly reports zero refusals |
| Final completion | application_suite and supervisor final_acceptance checkpoints, success=true, 11 tests passed |

Migration-row MD5 fingerprint: `b00f51e91c5b882cd84d3b2579d074ca`.
This identifies the disposable migration inventory, not a production database check.
The numeric native EPG ID was asserted through the real isolated database/ledger
but was not retained numerically in the final summary; no ID is invented here.

The corrected group lifecycle is now demonstrated by actual installed Django
views/tasks, PostgreSQL associations and supported API readback, not manufactured
relationships. The positive workflow ends registered_inactive. Its temporary
metadata enablement concerns only the disposable synthetic account. The interrupted
write test exercises a controlled post-create API refusal and durable unresolved
intent; it does not claim an actual production crash or uncertain production write.

All eleven test_passed records and every required completion checkpoint are
retained. No phase is inferred from startup or a later test beginning. The existing
plugin-maintenance opt-out remained active and meaningful native tasks stayed
registered. The Celery test consumer runs in a solo thread with real Redis, rather
than separate production worker processes; no eager/mock task execution is claimed.

## Isolation and security limits

Retained Docker inspection confirms network=none, no ports, privileged=false,
read-only root, exactly three read-only synthetic fixture/account binds, no named
volume and no production network/credential/database/socket exposure. Bootstrap
observed only loopback and no external default route. Requested resources remained
1 CPU, 1.5 GiB RAM/swap and 256 PIDs; retained metadata independently confirms memory
and PID limits, while CPU is evidenced by the exact pinned --cpus=1 create recipe.
Observed container memory peak was 598,110,208 bytes. The 240-second
application watchdog and 1,200-second transport deadline remained unchanged.

All eighteen installed files remained root:root 0644 and required application
parents were traversable. UID1000 application imports and permission probes passed.
Only reviewed local synthetic provider/API/XMLTV fixtures were used: eight metadata /
XMLTV HTTPS fixture requests, with no media or external provider retrieval. Positive
VPN/route/DNS witnesses are explicitly test-only. **This is not evidence of a real
AirVPN grant or live provider interoperability.** No socket destination was added
or firewall/VPN/DNS/systemd/Jellyfin policy modified.

## Cleanup and preservation

The approved runner reports cleaned=true. Transport terminal state is **completed,
cleanup_complete=true**, reason normal_return_reconciled. Independent postflight
found no container owned by this attempt. All 33 pre-attempt container IDs, images,
start times, restart counts, health and Config/HostConfig/Mounts fingerprints match;
full Docker network and volume inventory digests are unchanged. The protected
four-service stack and Jellyfin remain healthy. No unrelated service was modified.

All 48 historical runtime receipt hashes and all eight original corrected-build
receipt hashes remain unchanged. Staged controller/payload bytes and the reconciled
build receipt retain their pre-launch hashes. The corrected image remains present.
Private receipts and diagnostics are retained in the fresh workspace; only its
single disposable container/tmpfs state was removed. Cleanup is verified, not uncertain.

Sanitized complete evidence, admission observations, explicit checkpoints, test IDs,
source hashes, before/after fingerprints and private-receipt hashes are published in
`configs/dispatcharr-iptv/hardened-image-integration/corrected-runtime-acceptance-results.json`.
No credentials, raw provider URLs, tokens, databases or recovery archives are included.

**Final: PASS; GO for production image-binding review only.** The production
release still has aio_image=null and no production binding or deployment changed.
Separate review/authorization is required for any matched production transition,
real provider policy/activation, real network test or playback. Stop after publication.
