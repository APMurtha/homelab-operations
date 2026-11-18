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
