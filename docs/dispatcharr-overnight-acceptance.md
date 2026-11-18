# Dispatcharr overnight acceptance

**NO-GO for image-binding review.** Two additional isolated attempts ran and
cleaned up successfully. Both stopped on acceptance-test errors. The second
reached the native adapter's explicit `native_selected_group_missing` refusal;
its underlying cause is not established by the retained evidence. The uncertainty
stop condition applies. The third permitted attempt was not launched.
Production Dispatcharr and Jellyfin remain healthy and unchanged. No deployment.

## Identities and scope

- Starting evidence: `3f1b2c08d684e08c356cb82930b9a04d655a66f8`.
- Retained image: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
- First correction and attempt payload: commit `0f1d0f3decf00f28e42d754eac617a241f731276`.
- Second correction and attempt payload: commit `dbf60e4`.
- Each attempt used one launch, a fresh exclusive identity and the detached transport.
  Subsequent monitoring used status only. No automatic retries occurred.

## Demonstrated test-only corrections

**Plugin maintenance:** the prior failure stack entered `refresh_plugin_repos`
from plugin manifest retrieval. The pinned upstream `apps/plugins/apps.py` at
`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e` queues a startup refresh with a ten-second
countdown and wires a periodic refresh. Its supported
`DISPATCHARR_SKIP_PLUGIN_AUTODISCOVERY=1` opt-out returns before both operations.
The synthetic environment now sets that option before Django initialization,
including inherited uWSGI fixture processes. Runtime checks verify no plugin
refresh periodic schedule and retain the registered plugin task. Both attempts
passed these checks without a socket refusal.

This isolates unrelated maintenance; it does not establish that production plugin
maintenance is safe or authorize its network access. The preceding audit did not
retain the hostname or prove any completed external connection.

**Nullable account metadata:** attempt 1 stopped in the test's chained dictionary
lookup at runtime_test.py:330. The pinned M3U model allows nullable
`custom_properties`; the test assumed structured metadata on every unrelated/default
account. Raw response values and exception messages were not retained. Offline
reproduction demonstrates AttributeError for nullable JSON. A strict structured-tag
selector now ignores untagged/malformed metadata while preserving exact registration
matching, duplicate-count rejection, ownership journals and no-blind-retry assertions.
Attempt 2 explicitly passed that test and retained its uncertain-write scenario receipt.
No native adapter or Dispatcharr application source was changed.

The transport advances only its exact test-payload pin. The runner, image verifier,
socket audit and admission helper are byte-for-byte unchanged. Production installed
mapping sections in the transition manifest are unchanged; only five test-source
inventory entries changed or were added. Exact final hashes are in
`overnight-summary.json`; historical correction inventories are retained in
`overnight-offline-results.json` and `overnight-fixture2-offline-results.json`.

## Offline regressions

All **681 distinct tests pass**, zero failures: the existing 674 plus three plugin
fixture tests and four nullable-registration tests. The harness suite contains 116.
The full suites cover CLI/native contracts, permanent streaming, guard/trusted
readiness, persistence/admission, UID1000 and namespace permissions, DNS/TLS,
credential redaction, detached transport and socket restrictions.

The plugin tests execute the exact upstream AppConfig with synthetic Django modules,
reproduce normal startup wiring and verify the supported opt-out. The source
fixture matches upstream Git blob `2257ebe8ee9d8b607121cffbb0196e9203ec3476`.
The nullable tests preserve strict tag matching and duplicate detection. No
application assertion was weakened and no new network destination was permitted.

## Fresh preflight and admission

Both clean committed payloads were independently compared with Git source blobs,
then privately staged and independently re-read. Existing account fixtures and the
build receipt remained pinned. Andrew's selected SSH account was verified as
murth/UID1000 on Rivendell. Effective KillUserProcesses remained false, session
runtime unbounded and the reviewed detached transport compatible. The owner's
exclusive-administration confirmation and this autonomous authorization were retained.

Before each launch all 33 container fingerprints, protected-service/Jellyfin health,
network/volume inventories, retained image identity, build receipt and resource
availability matched. The preceding attempt's terminal cleanup was confirmed before
the next launch. Every actual image verification matched all 18 source hashes and
completed before stabilization. Each attempt made exactly one final admission decision.

| Attempt | Exclusive identity | Image verification | Stabilization | Final load 1m | RAM available, bytes | Disk available, bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `overnight1-20261118-3d8ef59a` | 82.692s | 120.500s | 0.66015625 | 3,536,785,408 | 7,738,941,440 |
| 2 | `overnight2-20261118-dd0c87d8` | 106.726s | 120.405s | 0.89892578125 | 3,544,133,632 | 7,736,823,808 |

Both decisions passed unchanged limits: load <=2, RAM >=2 GiB and disk >=1 GiB.
The fixed 120-second stabilization and 180-second ceiling were preserved. Full
capacity observations, timestamps and admission records are in each attempt JSON.

## Actual application outcomes

| Phase | Attempt 1 | Attempt 2 |
| --- | --- | --- |
| PostgreSQL 17 and authenticated Redis | Explicit completion | Explicit completion |
| UID1000 Django 6.0.9 | Explicit completion | Explicit completion |
| Migrations | 184 rows, completed | 184 rows, completed |
| Redis-backed non-eager Celery worker | Started; 57 tasks registered | Started; 57 tasks registered |
| Actual task results | Two actual results: expected denial and disabled-refresh marker | Same two actual results |
| Application testcases | 4 passed, test 5 errored | 5 passed, test 6 errored |
| Plugin fixture isolation | Passed | Passed |
| Private-policy/public-projection checks | Passed; five negative cases rejected | Passed; five negative cases rejected |
| Interrupted discovery/no blind retry | Error in test-only tag scan | Passed; single write, API readback, intent retained, no retry |
| Synthetic native import/XMLTV mapping | Not reached | Failed before selected group resolution |
| Default/DVR queue-probe completion | Not reached | Not reached |
| uWSGI/backend and DW fixture preservation | Not reached | Not reached |
| Final application acceptance | Failed/incomplete | Failed/incomplete |
| Socket audit refusal | None retained | None retained |

Migration row fingerprint in both disposable databases:
`b00f51e91c5b882cd84d3b2579d074ca`. The last explicit application phase checkpoint
was `task_execution` in both runs. Passing individual native API tests does not
constitute completed native API or Xtream/XMLTV phase acceptance. No later phase
is inferred from startup or from a started test. Authorization evidence is
synthetic only, **not proof of a real AirVPN grant**.

## Precise outstanding blocker and stop decision

Attempt 2's traceback ends at native.py:289 in `Adapter.register`, called by
`Integration.test_06_actual_native_discovery_import_and_XMLTV_mapping`.
That source line explicitly raises `Refused('native_selected_group_missing')` when
the selected stable group cannot be resolved from the newly created account's
native group associations. Account creation and the earlier controlled failure
scenario ran against disposable data. The native import, EPG and subsequent
compatibility assertions did not complete.

The evidence does not establish why the selected group was absent from the
adapter's resolved set: the account/group response and relevant discovery outcome
were not retained in diagnostic detail. It is not safe to label this a fixture
problem or an application defect. No group was invented, no assertion bypassed,
no application/adapter changed and no third attempt launched. Further investigation
must establish that boundary before another runtime attempt or image-binding review.

## Isolation, cleanup and production preservation

Each test container used network=none, no ports, no production networks/volumes,
no production credentials/policies/databases, no Docker socket, a read-only root
filesystem and disposable tmpfs state. The pinned recipe retained 1 CPU, 1.5 GiB
RAM, 256 PIDs, no restart, bounded Docker logs, 240-second application watchdog
and 1,200-second transport deadline. Only reviewed synthetic read-only fixtures
were mounted. Actual bootstrap observed only loopback and no external default route.

Both terminal statuses were failed with cleanup_complete=true. The approved runner
removed its exact owned container; read-only reconciliation found no remaining
container for either attempt. All 33 original container IDs/images/start times/
restart counts/health/configuration digests, complete network/volume fingerprints,
and the retained image stayed unchanged. Previous receipts and diagnostics remain
intact. The four protected services and Jellyfin remained healthy.
No image build/pull/retag, production modification, real provider authorization or
external provider request, Jellyfin change or playback occurred.

Sanitized per-attempt evidence: `overnight-attempt-1-results.json` and
`overnight-attempt-2-results.json` under the integration directory. Private receipts
remain under their original exclusive runtime/transport attempt directories; no
receipt was cleared or reused. The final summary includes exact evidence hashes.

**Final: NO-GO for image binding; stop for review of the unresolved native group
resolution boundary. No deployment is authorized by these results.**
