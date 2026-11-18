# Dispatcharr runtime admission sequencing

**Offline implementation PASS: 644 distinct tests pass. GO for one separately
authorized isolated application attempt, subject to the execution prerequisites
below. Image binding and deployment remain NO-GO.** No Rivendell access, Docker
operation, image scan, real stabilization wait, application test or production
configuration change occurred while implementing this correction.

Baseline: `beced1187137ede15b43ea1680c1dbeb8e19fbd2`.
Branch: `docs/udm-pro-max-migration-prep`.
Retained image reference:
`sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
This image was not inspected or rebuilt during offline development.

## Before and after

Previously, an external preflight exported image layers and verified sources;
`run_runtime.main` then checked load/RAM immediately. That flow coupled CPU-heavy
verification directly to admission, left disk admission in a separate wrapper,
and used a fixed temporary-container name with randomly selected evidence paths.
Attempt 2 stopped after verification raised load from approximately 0.67 to 5.87.
The [load investigation](dispatcharr-rivendell-load-investigation.md) attributes
most CPU work to Docker/containerd and the SSH/streaming group during that interval.

The runner now owns the complete sequence. A future operator must not wrap it in
another immediate image-layer verification/capacity-gate sequence. The new
host-only admission helper and the existing verifier refactor preserve all source
checks and require a fresh exclusive identity before attempting work.

## Implemented flow

1. Require the exact retained immutable image ID, the original verified build
   receipt, reviewed helper bytes and the exact synthetic expected-source fixture.
   The helper's 18 pinned hashes match the unchanged release contract: 14 hardened
   outputs plus four inherited readiness files.
2. Reserve `runtime-attempt-<attempt_id>` exclusively in the existing private
   workspace. The explicit ID is also used in the temporary container's name and
   attempt label. Missing/invalid/duplicate IDs fail closed; no old receipt is
   overwritten or cleared.
3. Capture healthy protected-stack/Jellyfin and all-container identity/configuration
   fingerprints, plus network and volume inventories. Prepare only public synthetic
   fixture code. Host helper payloads are excluded from the container fixture.
4. Invoke `inspect_image.verify` once. It checks immutable image identity, streams
   layers with the existing whiteout/latest-layer handling, checks all 18 hashes,
   and waits for the export process to exit successfully. Only then is
   `verification_completed` recorded. A partial/failed export cannot authorize
   stabilization.
5. Begin a **fixed 120-second stabilization interval**. Observe capacity at the
   start and approximately every **15 seconds**, including the final observation.
   Favorable readings cannot end the interval early. High readings cannot extend
   it. Observations are not admission decisions and do not invoke the runner again.
6. During stabilization, use cheap image-identity and container metadata checks.
   There is **no second layer scan**. Changed image identity, protected health,
   any captured container identity/configuration/state, or the pinned source
   contract aborts immediately. Expensive verification evidence must belong to
   this attempt, be complete and be at most 30 seconds old at stabilization start.
7. After the fixed interval, make **one final admission decision** from the retained
   final capacity measurement. Refusal stops before container creation. Success
   is followed by one cheap identity/production/fixture consistency recheck, then
   the existing scoped Docker creation/start/runtime/cleanup path.

The **hard stabilization ceiling is 180 seconds**. Probe commands receive short
remaining-deadline budgets; the state machine checks elapsed monotonic time after
probes, sampling and evidence writes. Oversleep, interruption, malformed readings,
stale measurements or deadline expiry cannot authorize creation. No new daemon,
timer, service, port, network or privileged application process is introduced.

## Preserved limits and runtime behavior

| Predicate / limit | Value |
| --- | --- |
| One-minute load | ≤ 2 |
| MemAvailable | ≥ 2,147,483,648 bytes (2 GiB) |
| Free space on existing workspace filesystem | ≥ 1,073,741,824 bytes (1 GiB) |
| Test container CPU | ≤ 1 CPU |
| Test container RAM and RAM+swap ceiling | 1,610,612,736 bytes (1.5 GiB) |
| Test container PIDs | ≤ 256 |
| Container restart policy | no |
| Application/runtime watchdog | existing 240 seconds |

No thresholds, approved image, application source or production contract changed.
The original three read-only fixture binds, network none, no published ports,
read-only rootfs, tmpfs-only application state, no production volumes/socket/data,
capability restrictions and existing 1 MiB × 2 temporary-container logging remain.
The host verifier and admission modules never enter the container fixture.

`runtime_test.py` and `runtime_diagnostics.py` are **byte-for-byte unchanged**.
Their Unix/loopback literal allowlist, exit-86 refusal, sanitized socket records,
phase completion checks and inherited diagnostic descriptor remain intact.
The runner still retains diagnostics when final application JSON is missing and
cleans up only the exact known container ID it created. A new regression ensures
that a receipt-write failure immediately after known container creation still
reaches scoped cleanup. No test container was actually created by these tests.

Production capture now compares all containers' IDs, immutable images, start times,
restart counts, health/status and Config/HostConfig/Mounts digests rather than only
five health strings. No raw configuration values are journaled. The post-run
comparison also includes the volume inventory. Error journaling avoids raw Docker
stderr or exception bodies.

## Evidence and failure handling

`admission.jsonl` lives in the exclusive 0700 attempt directory, with mode 0600.
Records are appended and fsynced; directory creation/publication is fsynced.
Records have a sequence, wall-clock epoch, event and bounded details. Limits are
64 records and 16 KiB per record. Normal execution needs about nine capacity
observations, not an unbounded polling history.

Records include:

- Attempt reservation, verification start and successful process-exit/hash evidence.
- Stabilization start, planned duration and deadline.
- Actual monotonic capacity observations: all three load values, RAM and free disk.
- Stabilization end, actual elapsed seconds and completed/aborted state.
- Exactly one final admission decision when that boundary is reached, including
  the exact measurement and unchanged thresholds.
- Scoped creation intent/known ID, runtime outcome or a sanitized attempt failure.

Missing or stale verification causes **zero** final admission decisions. A high
final load or insufficient final RAM/disk causes **one refused** decision and
zero container creations. Timeout/health/image drift during observation also
stops before creation without another scan. A journal failure cannot permit
creation. A late decision write crossing the deadline is explicitly invalidated;
there is no second capacity decision or retry.

KeyboardInterrupt/SystemExit and ordinary failures retain the consumed identity
and best-effort terminal evidence. Failed/interrupted identities are never
reusable. If an interruption occurs during Docker creation and its outcome is
uncertain, reconcile the exact name/creation intent read-only before any cleanup;
never blindly call main or create again. Prior attempts and their private
receipts remain outside this new attempt directory and are untouched.

Limits remain explicit: filesystem fsync and process scheduling can themselves be
delayed, so the ceiling is a fail-closed deadline, not a guarantee that the OS
returns control at precisely 180 seconds. Tests simulate a 195-second oversleep
and demonstrate refusal with actual elapsed time retained. Once already-admitted
execution advances to Docker, identity/health changes have unavoidable
check-to-use windows; metadata checks are not continuous attestation. Lost power,
SIGKILL before persistence or unavailable storage can still lose the latest record.
Uncertain/missing evidence requires reconciliation, never inferred permission.

## Offline regression results

**644 distinct tests pass, zero failures**: the 608-test baseline plus **36 new
sequencing regressions**. All time advancement in sequencing tests is synthetic;
no test sleeps for two or three real minutes. Docker/image/process boundaries are
mocked, using in-memory tar layers for verifier tests. Existing socket fixtures
remain confined to unrouted temporary namespaces; the real public-address audit
fixture is refused before kernel network use.

| Suite | Distinct tests |
| --- | ---: |
| Provider/native CLI tools | 139 |
| Native provider hardening | 91 |
| Permanent streaming / lifecycle / guard / registration / admission | 210 |
| Persistence | 26 |
| Guard-interface assessment | 14 |
| Trusted guard design | 28 |
| Native isolated fixtures | 14 |
| Permission/packaging fixtures | 40 |
| Image harness, diagnostics and new sequencing | 79 |
| Existing isolated socket fixtures | 3 |
| **Total** | **644** |

Coverage includes successful full-interval stabilization; transient/persistent
high load; exact-boundary load/RAM/disk acceptance; memory/disk refusal; incomplete,
missing, stale, future and wrong-attempt verification; image/source/health drift;
slow probes, oversleep and the three-minute ceiling; stale samples and slow
persistence; interruption; duplicate identity; failed journal writes; exactly one
export and decision; no creation after refusal; and preserved resource/isolation
arguments. Synthetic whole-run tests verify admission precedes creation and that
known-owned cleanup remains scoped. Separate verifier fixtures prove a failed
export produces no completion evidence and a successful export is reaped first.
These are not real Django/Celery/API/XMLTV acceptance results.

The existing diagnostic regression's path-location assertion was updated to
follow the new shared attempt-directory owner and still require the runner's
Journal call. No socket classifications, denial predicates or application checks
were relaxed. Relevant trusted-guard/source-inventory tests were rerun after the
last pin update; overlapping reruns are not double-counted.

## Exact changed-file inventory

The report excludes its own hash. The result JSON excludes its own hash from its
internal inventory to avoid a cycle.

| Repository path | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/hardened-image-integration/README.md` | `68f0de83bf30ff1ff984983cb9dd7f8a2c1381b18a5b091a4df941a960e117b5` |
| `configs/dispatcharr-iptv/hardened-image-integration/inspect_image.py` | `67549e04e19b0239229c878984f61a6b44f5e944dc1c4a5950f678e2b1872822` |
| `configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py` | `c5aeadca482d51d4beb61c8b9396fe613dad6ab00304ce3ee6404762ec7090e7` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_admission.py` | `c7bec3b64de82afcfee3d85861480b542d93947943cd9c87802be9293573d314` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_admission.py` | `9848ea54a5baa514e205abba9b032b2e8e55609dc5db9dccfa3b46984d4e8090` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_diagnostics.py` | `b209a0e2289263dfa5d546eb5738dcc6e544f4de8ba03352c2960215a9d0bbe4` |
| `configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json` | `819b63dd17c1b3a3a19877171229d1c8c21e6151c23f7ff7bc14bb593f64638b` |
| `/home/murth/Projects/dispatcharr-permanent-candidate/configs/dispatcharr-iptv/hardened-image-integration/admission-sequencing-results.json` | `fbeff409e20d2dd5d65f16088af719ca7aad7fa7dae295475d70858b656518cd` |

`inspect_image.py` exposes its existing streaming logic as a returning function;
its original standalone main remains. `runtime_admission.py` is the new state
machine, source contract and private journal. `run_runtime.py` integrates these
helpers and exclusive IDs. `test_runtime_admission.py` is new synthetic coverage;
`test_runtime_diagnostics.py` changes only the attempt-location assertion. README
and this report describe the new calling contract. The transition manifest updates
only those five legitimate **test-source inventory** entries (including newly
tracked helper/test sources). All **80 installed mappings** and other manifest
sections are unchanged. App source/image pins, production Compose, relay,
guard/systemd/admission units and historical receipts/evidence remain unchanged.

## Remaining execution prerequisites and decision

A separately authorized operator must prepare the exact reviewed payload,
including base64 host entries `host/runtime_admission.py` and
`host/inspect_image.py`, and the original synthetic runtime/diagnostic/client/
publisher fixtures. Helper SHA-256 values must equal `run_runtime.HOST_HELPERS`;
unknown or modified helper bytes are refused before Docker access. Preserve the
original verified build workspace and receipt, select a new explicit `attempt_id`,
verify exclusive administration and baseline health, and do not reuse either old
attempt's identity or invoke an obsolete outer verification wrapper.

Transport timing also needs explicit review before execution: verification plus
120 seconds of stabilization plus the unchanged 240-second runtime watchdog can
exceed the NEST SSH helper's synchronous five-minute limit. The next authorized
procedure must provide a receipt-safe execution/monitoring plan for that combined
budget; a transport timeout is not permission to retry or abandon an uncertain
container. No SSH helper timeout, runtime watchdog, daemon or asynchronous launcher
was changed/installed here. No new infrastructure is required by this state machine.

**GO for a separately authorized isolated application attempt once that execution
plan and fresh prerequisites are satisfied.** This is approval readiness for the
procedure, not evidence that the retained image passes the application matrix.
No runtime attempt, image binding, deployment or provider activation follows this
publication.
