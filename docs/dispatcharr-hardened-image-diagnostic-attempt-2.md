# Dispatcharr diagnostic rerun — attempt 2

**BLOCKED in preflight; NO-GO for image binding.** The single additional attempt
stopped at its recorded post-image-verification capacity check: one-minute load
was **5.87158203125**, above the unchanged limit of **2**. Available RAM and disk
passed. No runtime runner invocation or test container creation/start occurred.
No retry, rebuild, deployment or application-source change followed.

## Release and preflight

Checkpoint: `c3cb43a563aedbdd089e05952c92dbdccbbaa2b1`.
Approved diagnostics: `a84ee663653c8d2f3292edac05c24c7309087397`.
Retained image: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
Branch: `docs/udm-pro-max-migration-prep`.

The clean checkout and approved harness hashes matched. Pinned NEST access
verified Rivendell as Andrew's selected `andrew-media` / `media` SSH account.
The owner confirmed no conflicting administrative operations. The original verified
build receipt identifies the exact retained image. Read-only image-layer streaming
verified all **14 hardened outputs and four inherited readiness hashes** against
the unchanged release contract. No probe container, extracted source file, image build,
pull or retag was used. Reviewed fixture hashes remain those of the approved
synthetic payload; no payload was mounted or executed.

All 33 production container records matched the accepted baseline during preflight,
including IDs, images, start times, restart counts, health/status and canonical
Config/HostConfig/Mounts hashes. The four protected Dispatcharr services and
Jellyfin were healthy. The postflight independently confirmed the complete
container, network and volume fingerprints still match the preceding checkpoint.
No production credentials, policy files or databases were supplied to a test
environment; none was created.

## Exact capacity checks

Each check was appended to a new private exclusive
`diagnostic-attempt-2-capacity.jsonl` journal, flushed and fsynced **before** its
pass/fail decision. These are the actual values used, including the failed check.
Thresholds remain RAM ≥ **2,147,483,648 bytes**, free disk ≥ **1,073,741,824 bytes**,
and one-minute load ≤ **2**. The additional post-verification check enforces the
same limits before a runtime invocation; nothing was relaxed or bypassed.

| Check | UTC | RAM available, bytes | Disk free, bytes | Load 1 / 5 / 15 | Result |
| --- | --- | ---: | ---: | --- | --- |
| preflight_entry | 2026-11-18T03:22:54Z | 3609939968 | 7699402752 | 0.6650390625 / 1.26318359375 / 1.126953125 | PASS |
| preflight_before_image_verification | 2026-11-18T03:22:54Z | 3604840448 | 7699398656 | 0.6650390625 / 1.26318359375 / 1.126953125 | PASS |
| preflight_after_image_verification | 2026-11-18T03:24:16Z | 3574943744 | 7698972672 | 5.87158203125 / 2.77294921875 / 1.67236328125 | FAIL |

The failure is specifically the one-minute load predicate; both other predicates
passed at that instant. Load rose during the interval containing read-only image
verification. Its cause was not measured, and no unrelated-service investigation
or load-reduction operation was started. The later postflight sample is retained
separately in JSON and is not substituted for any gate's actual inputs.

The planned observer for the approved runner's own gate was not used: preflight
had already failed. The runtime runner and application harness remain unchanged.
There was no waiting for a better sample or second admission attempt.

## Isolation and application evidence

The planned configuration remains the reviewed network-none, no-published-port,
read-only-rootfs container with disposable tmpfs, no production networks, volumes,
credentials, policies, databases or Docker socket, no restart, at most 1 CPU,
1.5 GiB RAM and 256 PIDs, and only reviewed read-only synthetic fixtures.
Because no container existed, these are planned constraints, **not new observed
runtime-isolation results**.

| Required application phase | Result |
| --- | --- |
| PostgreSQL initialization and authenticated Redis | NOT EXECUTED |
| UID1000 Django initialization | NOT EXECUTED |
| Database migrations and fingerprint | NOT EXECUTED |
| Celery startup, registration and actual task execution | NOT EXECUTED |
| Native API tests and owned resource behavior | NOT EXECUTED |
| Synthetic Xtream account, groups and channel operations | NOT EXECUTED |
| XMLTV import and EPG mapping | NOT EXECUTED |
| Authorization and revocation | NOT EXECUTED |
| Backend readiness and DW English compatibility | NOT EXECUTED |
| Final acceptance | NOT EXECUTED |

Last completed application checkpoint: **none**. Runtime test count: **zero**.
No new socket event exists, so there is no family, operation, destination class,
application test phase or application stack to report. The original socket event
remains unresolved. No prior inferred phase is upgraded to a success.

## Receipts, cleanup and production preservation

This attempt used a separate exclusive capacity journal. The first attempt's
exclusive intent was neither cleared, retried nor modified. Its SHA-256 remains
`ae1dc6cf227f4fd7663a047ad0ce783535d8c653aa219fd48ed83a2a7ba89386`. No attempt-2 runtime intent was created because the
preflight failed first. The unused planned runtime identity was
`dispatcharr-native-runtime-a84ee66-attempt2`; no such container exists.

No test container, network or volume was created, so none required removal. No
new runtime-attempt fixture directory exists. The original image, build receipt,
previous receipts and private diagnostic evidence are intact. The new capacity
journal and postflight receipt are preserved privately in the original build
workspace. Only sanitized evidence is published.

Postflight confirms all **33** production container IDs, image IDs, start times,
restart counts, health/status and configuration fingerprints unchanged. Complete
Docker network and volume metadata fingerprints match the preceding accepted
checkpoint. All four protected services and Jellyfin remain healthy. No protected
or unrelated service was operated; no firewall/VPN/DNS, systemd, Jellyfin,
application policy or playback change occurred.

## Evidence inventory

| Unchanged harness file | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py` | `763839d42e80e933e52918349bd7f34dd816b546b2f2fe0c92b3ff69b326a90e` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_diagnostics.py` | `de5ed39ff92da1002e2f90507511d9dd3cfc878b8e5de55126fb30d467bae432` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_test.py` | `56c68d1412984d7b0351bd0ecc4cc6c4862c6a32bccb0eccd412e9500fca6333` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_diagnostics.py` | `3cbac9f04bf49805543d9e40f87e1f1c3a27af649f46880e4d221b8153142477` |

New sanitized machine-readable evidence:
`configs/dispatcharr-iptv/hardened-image-integration/diagnostic-attempt-2-results.json`
— SHA-256 `b72c9613506c35aef0d123d7c8ebea950d06a7c12d08f239dcd2a1e73f121593`.

It contains every gate's exact values, all 18 image hashes, approved fixture hashes,
production preservation records, original receipt hashes, executed preflight/
postflight script hashes, and explicit not-executed phase states. No private
configuration contents, credentials, provider URLs or databases are included.
The report excludes itself from its hash inventory. No source pins, installed
manifests or harness files were changed in this publication.

## Decision

**NO-GO for image-binding review or deployment.** The precise blocker is the
failed post-verification load check, not an application or socket-audit result.
A future attempt needs separate authorization and fresh adequate-capacity checks.
Do not relax admission, clear either attempt's evidence, rebuild, activate a
provider or automatically retry. No application correction is justified by this
unexecuted runtime matrix.
