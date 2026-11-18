# Hardened image build and isolated integration evidence

Current corrected build: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
Packaging and UID1000 policy checks passed; application acceptance stopped on an
unclassified socket-audit event. **NO-GO for binding; do not automatically rerun
the historical test harness.** See [runtime acceptance](../../../docs/dispatcharr-hardened-image-runtime-acceptance.md)
and `runtime-acceptance-results.json`. The material below retains prior checkpoint
provenance; its 26c93e… image is historical and was not reused.

## Earlier checkpoint evidence

**One image built; application acceptance FAIL; NO-GO for deployment.**
See [the integration report](../../../docs/dispatcharr-hardened-image-integration.md).

Built immutable ID:
`sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78`.
It is a retained review artifact, not a deployable release. Production is unchanged.

The [subsequent offline policy/packaging fix](../../../docs/dispatcharr-provider-policy-permission-fix.md)
updates the future source candidate and packaging tests only. The image identity
and verification-results.json here remain the historical failed-build evidence.
At that checkpoint no replacement image had been built; the current runtime
acceptance report records the later single corrected build.

- `inspect_image.py`: hash-only base-layer inspection, including whiteouts.
- `prepare_context.py`: verify eight source inputs, four inherited readiness files,
  approved patch bytes and 13 output hashes; no build/deploy operation.
- `Dockerfile`: immutable local base, label, COPY only; no RUN or pull.
- `build_once.executed.py`: build-wrapper source used for the failed image (normalized EOF),
  excluding its appended public-source payload. Its umask 077 directory creation
  produced root-owned 0700 application directories. Retained for provenance.
- `build_once.py`: **future recipe correction, not executed for another build**.
  Keeps the transport workspace private while explicitly setting public image-code
  directories to 0755 and files to 0644. Requires separate review/authorization
  before another build. Refuses the existing review tag.
- `run_runtime.py`, `runtime_test.py`: bounded network-none runtime harness.
  Actual PostgreSQL/Redis initialization and UID1000 Django setup were executed;
  Django failed before migrations. Later API/Celery test bodies are prepared,
  **unexecuted and unvalidated**. This is not an accepted application matrix.
  Future review must also reconcile the fixture directory's UID1000 traversal
  permissions before exercising its client fixtures.
- `permission_probe.py`: actual UID/GID1000 filesystem diagnostic, using an
  explicitly non-grant marker. No application, provider or production state.
- `test_inputs.py`, `test_build_modes.py`: seven passing offline tests; no Docker
  calls. Covers source layering/hash refusal and the future directory-mode fix.
- `verification-results.json`: sanitized observed inputs/outputs, image identity,
  permissions, runtime boundary/failure, cleanup and regression log hashes.

Run offline verifier tests:

```sh
python3 -B -m unittest discover \
  -s configs/dispatcharr-iptv/hardened-image-integration -p 'test_*.py' -v
```

No installer or automatic deployment is supplied. The native policy directory's
root-only contract is separately incompatible with actual UID1000 application
workers; changing code-directory modes alone cannot make this release acceptable.
Do not chmod the private policy, run workers as root, substitute a synthetic grant,
change approved server source, or reuse this image for deployment.

The final offline integration selects a new future review tag
`local/dispatcharr-native-hardening:policy-lifecycle-review-v2`; the COPY-only
Dockerfile labels the unchanged approved application sources at 0b8ac7d.
`run_runtime.py` now requires an explicit new image ID matching its build receipt,
refuses the failed/base image and has no default image. Its public synthetic code
fixture directories use 0755 inside a private transport parent. The updated harness was later executed once; its socket-audit guard aborted
before a complete application result was retained. Later test bodies remain
unaccepted; see the runtime acceptance report for the exact evidence boundary.

## Offline socket-audit diagnostics

The corrected harness is reviewed separately in
[the diagnostics report](../../../docs/dispatcharr-runtime-audit-diagnostics.md).
It has not been rerun against the retained image. Application acceptance remains
NO-GO; one further isolated diagnostic run requires separate authorization.

`runtime_diagnostics.py` is a required public fixture payload alongside
`runtime_test.py`. It classifies socket operations without logging destination
values and preserves the existing literal local allowlist. Unknown, private and
public destinations still cause immediate exit 86. Local-looking byte/abstract
addresses are classified but are not newly permitted.

Phase completion is recorded only after the associated assertions pass. A
root-private or UID-private fsynced snapshot and a bounded inherited stdout
channel preserve sanitized records independently of the final result JSON.
`run_runtime.py` saves each future run under a new `runtime-attempt-*` directory
beside the existing build receipt, preserving older evidence. No new writable
bind is introduced. Its temporary container log has a per-container 1 MiB × 2
rotation bound; collection is limited to 1,000 lines / 2 MiB. Missing final JSON
is an explicit failure with recovered checkpoints, never implicit acceptance.

Run the pure event, redaction and crash-checkpoint tests:

```sh
python3 -B -m unittest discover \
  -s configs/dispatcharr-iptv/hardened-image-integration \
  -p test_runtime_diagnostics.py -v
```

Run those tests plus real Unix/loopback/refused-public socket fixtures in a
fresh unrouted user/network namespace (no Docker):

```sh
sh configs/dispatcharr-iptv/hardened-image-integration/run-audit-offline.sh
```

If isolated namespaces are unavailable, report the fixture gap; do not run the
public-address fixture in the host network namespace. The audit is diagnostic
coverage for Python connect/getaddrinfo events, not a substitute for network-none
isolation or evidence of a real AirVPN namespace grant.

## Bounded admission sequencing (offline implementation)

See [the sequencing review](../../../docs/dispatcharr-runtime-admission-sequencing.md)
before any separately authorized run. No image or application test was executed
while implementing this procedure.

The new runner requires an explicit unused `attempt_id` keyword and two reviewed
host-only payload entries, `host/runtime_admission.py` and `host/inspect_image.py`.
Their bytes must match `run_runtime.HOST_HELPERS`. The host entries are excluded
from the container fixture. Existing synthetic fixture hashes must also be
verified against the reviewed checkout; `expected-source-hashes.json` must match
all 18 pinned sources. The original verified build receipt is still required.

The runner now owns the complete sequence: reserve `runtime-attempt-<attempt_id>`
exclusively, verify the retained immutable image and all 18 source hashes once,
reap the export process, observe a fixed 120-second stabilization interval,
then make one final admission decision. Observations occur every 15 seconds;
load fluctuations never shorten or extend the interval. The hard ceiling is
180 seconds; timeout, stale evidence or interruption refuses creation. No
capacity gate is retried. Load ≤ 2, RAM ≥ 2 GiB and free disk ≥ 1 GiB remain
mandatory. The container limits and all socket-audit denial behavior are unchanged.

`admission.jsonl` is private, fsynced evidence of verification completion,
stabilization start/end, actual elapsed time, every capacity sample and the single
final decision. Image/production drift stops the sequence using cheap metadata
checks, without another image-layer scan. A failed or interrupted attempt consumes
its identity; never clear or reuse it. Old attempt receipts remain untouched.

A future authorized operator must reconcile transport/watchdog timing: image
verification + stabilization + the existing 240-second runtime deadline can exceed
a synchronous five-minute SSH helper call. Use a separately reviewed receipt-safe
execution/monitoring procedure; a transport timeout is not permission to invoke
`main` again. No transport timeout or runtime deadline is changed here.

Run sequencing and existing harness tests without Docker or real sleeping:

```sh
python3 -B -m unittest discover \
  -s configs/dispatcharr-iptv/hardened-image-integration -p 'test_*.py' -v
```

## Detached one-attempt transport (offline review only)

`runtime_transport.py` provides `launch` and read-only `status` around the exact
8ac8d18 runner. See [the transport plan](../../../docs/dispatcharr-runtime-test-transport.md)
for reviewed staging prerequisites, launch/monitor commands and failure recovery.
It was tested only with local synthetic runners; no application test was launched.

Launch reserves `transport-attempt-<id>` exclusively and double-forks a temporary
host supervisor independent of the SSH streams/session. The supervisor has a
20-minute overall budget, a five-second heartbeat and scoped process-group timeout
handling. The runner's verification, fixed 120-second stabilization, load/RAM/disk
thresholds, 240-second runtime watchdog and Docker isolation are unchanged.

Status never spawns work. It checks PID/start-time/boot identity and private
receipts; terminal status uses bounded read-only Docker queries for the exact
name, attempt label and known ID, plus original production/network/volume
fingerprints. Missing or conflicting evidence returns `uncertain`. A lost SSH
response must be followed only by status for the same ID, never another launch.

No permanent daemon, service, timer, listener or remote installer is supplied.
POSIX disconnect tests pass; existing host SSH/logind/cgroup teardown policy must
still be checked read-only before a separately authorized live launch. Do not
change that policy to make the transport work.
