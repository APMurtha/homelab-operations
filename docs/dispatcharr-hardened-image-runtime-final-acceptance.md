# Hardened Dispatcharr isolated runtime final acceptance

**FAIL; NO-GO for image-binding review.** One authorized detached attempt passed
verification and admission, then the unchanged socket audit stopped the application
on a background plugin-repository manifest hostname lookup. Scoped cleanup and
production preservation **PASS**. No retry, source correction or allowlist change
was performed.

| Identity | Value |
| --- | --- |
| Attempt | `acceptance-20261118-22973a21` |
| Approved checkpoint | `86413aebc5677dfd4142a8c12d1a4db6e970a15b` |
| Transport release | `8f8d719242146fc1cea67bd15a2f0bfafa540b24` |
| Image | `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be` |
| Test container, removed | `9baf784afdacf863cc1cdf7b8d74e31a2657c9e49ff71f06be98ed2aa2d7f7a9` |
| Synthetic payload SHA-256 | `2a36401c59d6492e54d8a5d7aa0f7adb56c4f5be96dcaddd5cb82e9232b04b0c` |
| Transport source SHA-256 | `fb69c44a15977ca424a897665836de1047b28fd6df65e44fc8dd04023455833a` |
| Unchanged runner SHA-256 | `c5aeadca482d51d4beb61c8b9396fe613dad6ab00304ce3ee6404762ec7090e7` |

## Preflight and single launch

The clean checkout was at the approved checkpoint. Historical review-file hashes
were verified against their own approval commits; current code and manifest hashes
matched the latest approved checkout. An initial local comparison used a historical
README hash that predated approved transport documentation changes. That comparison
was corrected against the corresponding commits; no pin or file was regenerated
to accept drift, and no remote launch had occurred.

NEST verified Rivendell and SSH account murth (UID1000). The owner confirmed no
conflicting administration. Live KillUserProcesses remained false; SSH/logind,
scope, public user-record sources and key/PAM policy remained compatible. All
**33 production container** identity/configuration/state records and complete
network/volume fingerprints matched the accepted baseline. The protected four
services and Jellyfin were healthy. The original immutable image and verified
build receipt matched. No external image-layer verification wrapper was used.

Preflight MemAvailable was **3,568,144,384 bytes**,
free disk **7,755,018,240 bytes**, and observed load
**0.179**. Load admission was deferred to the
approved runner. json-file bounded logging was available.

The **23-file synthetic-only payload** was independently checked against approved
git blobs, prior reviewed passwd/group fixture hashes and all 18 expected image
sources. The remote private staged files were independently re-read and checked.
No provider credentials, production policies, databases or private source URLs
were supplied. Bundle directories/files were UID1000-owned 0700/0600. Old build,
intent, failed-attempt and capacity receipts were preserved.

Launch was invoked **exactly once**. Its SSH call returned reserved; later calls
used only status for this same identity. The detached supervisor continued after
the launch SSH returned. No deliberate disconnect/fault experiment was performed.

## Verification, stabilization and admission

All **18 actual image-source hashes** passed, and the export process exited zero.
Verification took **95.568 seconds**. Fixed stabilization ran
for **120.448 seconds** (120 seconds planned, 180-second ceiling).
The high initial load was observed without early refusal or repeated admission:

| UTC, 2026-11-18 | One-minute load | RAM available, bytes | Disk free, bytes |
| --- | ---: | ---: | ---: |
| 04:50:37.696 | 5.30078125 | 3517087744 | 7752904704 |
| 04:50:53.262 | 4.19384765625 | 3525898240 | 7752859648 |
| 04:51:08.887 | 3.26416015625 | 3541696512 | 7752663040 |
| 04:51:24.409 | 2.68798828125 | 3530371072 | 7752626176 |
| 04:51:40.053 | 2.091796875 | 3557396480 | 7752548352 |
| 04:51:55.486 | 1.70751953125 | 3544326144 | 7752466432 |
| 04:52:10.957 | 1.32861328125 | 3544850432 | 7752269824 |
| 04:52:26.366 | 1.03369140625 | 3543392256 | 7752204288 |
| 04:52:37.018 | 0.80419921875 | 3551551488 | 7752204288 |

There was **one** final admission decision at
**04:52:37.032 UTC: admitted=true**.
Final load **0.80419921875 ≤ 2**, RAM
**3,551,551,488 ≥ 2,147,483,648 bytes**, disk
**7,752,204,288 ≥ 1,073,741,824 bytes**.
No threshold changed. This execution demonstrates that the fixed quiet interval
separated the verification-induced load spike from the final capacity decision.

## Actual application results

| Required phase | Retained evidence / result |
| --- | --- |
| PostgreSQL | **PASS**, explicit root checkpoint; PostgreSQL 17, disposable DB initialized |
| Authenticated Redis | **PASS**, explicit checkpoint; authenticated PING |
| UID1000 Django | **PASS**, explicit checkpoint; Django 6.0.9 |
| Migrations | **PASS**, explicit checkpoint; 184 migration rows; MD5 fingerprint `b00f51e91c5b882cd84d3b2579d074ca` |
| Actual Celery startup | **PASS**, explicit worker-start checkpoint; eager disabled, real Redis broker |
| Celery task registration | **PASS**, required tasks registered; 57 registry entries |
| Default/DVR task outcomes | **NOT ACCEPTED**, no task_execution completion checkpoint |
| Native security API tests | **NOT ACCEPTED**, no native_api completion checkpoint |
| Synthetic Xtream/channel workflow | **NOT ACCEPTED**, no completion evidence |
| XMLTV import and EPG mapping | **NOT ACCEPTED**, no completion evidence |
| Authorization/revocation bootstrap | **PASS**, retained actual UID/GID1000 probes: private traversal/write denial, revocation observed, fresh generation |
| Full negative authorization cases | **NOT ACCEPTED**, no completed application test evidence |
| uWSGI/backend readiness and DW compatibility | **NOT ACCEPTED**, no completion evidence |
| Full application/final acceptance | **FAIL / incomplete**, application exited 86; parent container exited 1 |

Last completed application checkpoint: **task_registration**. The application died
before final unittest JSON was written. No test count or passed testcase is
invented: tests_run is unavailable and there are zero retained test_started /
test_passed records. The observed background Celery task is evidence of task
execution activity, but it does not satisfy the required default/DVR task-result
acceptance checks. Migration fingerprint is a disposable test-database row
fingerprint, not a production schema assertion. No production database was used.

The bootstrap authorization records are explicitly **synthetic, not a real AirVPN
grant**. The retained policy-boundary probes do not upgrade the later unexecuted
security matrix to PASS. No broadcaster request or playback occurred.

## Socket-audit finding and precise blocker

The audit record is fsynced, from the UID1000 **application** process, background
thread, phase **task_registration**, test identifier **unassigned**:

- Operation: **getaddrinfo**; family **AF_UNSPEC**.
- Address form: **hostname_text**; destination classification: **unknown**.
- Reason: **unknown_destination_denied**; legacy_allowed=false.
- Action: immediate application exit **86** before name resolution proceeded.

Sanitized call stack, oldest to newest retained frame:

```text
trace.py:585 trace_task
tasks.py:20 refresh_plugin_repos
api_views.py:959 _fetch_manifest
http_security.py:111 get_with_validated_redirects
http_security.py:42 validate_outbound_http_url
socket.py:983 getaddrinfo
runtime_test.py:62 audit_network
runtime_diagnostics.py:257 audit
```

The stack identifies a real Celery `refresh_plugin_repos` task entering plugin
manifest retrieval and outbound-HTTP URL validation. This is an attempted hostname
lookup on a background HTTP-maintenance path, **not an AF_UNIX operation or confirmed
loopback connection**. The hostname and any eventual public/private address are
intentionally not retained; no completed external connection or public destination
is claimed. Network-none isolation and the audit refusal remained enforced.

The global test-phase context describes the main process's current phase, not a
causal test assignment for that background task. A later generic root
application_process_abnormal record did not overwrite the retained socket refusal.
The old generic audit failure may have had a similar cause, but its exact event
was never captured and is not retroactively classified here.

**Precise blocker:** unrelated plugin-repository background refresh attempted
unapproved hostname resolution during isolated application setup. Any next step
requires separate review of that startup/queue side effect and the synthetic test
fixture's scheduling. No destination should be allowed merely to pass this matrix.
No application, image, fixture or socket-policy correction was made in this task.

## Isolation, cleanup and preservation

The retained Docker inspection confirms network=none, no published ports,
privileged=false, read-only rootfs, exactly three synthetic read-only fixture /
passwd / group binds, no production volume and observed memory=1,610,612,736 bytes,
pids=256. The actual bootstrap independently observed only loopback, no external
default route and no Docker socket. All 18 source files had retained root:root 0644
mode checks; required public code-directory checks did not fail.

The unchanged reviewed create recipe requested **1 CPU**, **1.5 GiB RAM+swap**,
**256 PIDs**, no restart and disposable tmpfs. CPU quota itself was not separately
retained in the inspection format; its requested flag is established by the
unchanged runner, not invented as an independent measurement. The 240-second
runtime watchdog and 1,200-second supervisor deadline remained unchanged and were
not reached. The container-to-scoped-cleanup interval was **24.145
seconds**.

Final transport status:

```json
{
  "attempt_id": "acceptance-20261118-22973a21",
  "state": "failed",
  "cleanup_complete": true,
  "last_event": "runtime_finished",
  "reason": "failure_or_abnormal_exit_reconciled"
}
```

The approved runner removed its exact known test container. Transport read-only
reconciliation confirmed scoped absence and preserved baseline. Final independent
postflight confirms all **33** original container IDs, images, start times,
restart counts, health/status and configuration fingerprints unchanged; full
network/volume fingerprints unchanged; protected Dispatcharr services and Jellyfin
healthy; retained image unchanged; **9 previous receipt/intent/capacity files unchanged**.
No owned test container remains. All new private receipts and sanitized diagnostic
logs remain in their exclusive attempt directories. No forced cleanup, recovery
attempt, production modification, image build/pull/retag, source/allowlist change,
provider activation, Jellyfin change or playback occurred.

## Published evidence and decision

Sanitized evidence:
`configs/dispatcharr-iptv/hardened-image-integration/runtime-final-acceptance-results.json`
— SHA-256 **`aee89c497f569eb6b4f4e8a02580444424cdd96882979dcd32b9055550f57612`**. It contains exact verification/source identities,
all admission observations, explicit checkpoints, sanitized refusal, saved
isolation metadata, final status, receipt hashes and before/after preservation
records. Private payload contents, credentials, provider URLs, application database
data and raw service logs are excluded. The report excludes its own hash.

**NO-GO for image-binding review or deployment.** Verification, stabilization,
transport and cleanup worked; the application acceptance matrix remains incomplete
because of the blocked background plugin manifest lookup. Stop after this single
attempt and publication. Further corrective work or another run requires separate
authorization.
