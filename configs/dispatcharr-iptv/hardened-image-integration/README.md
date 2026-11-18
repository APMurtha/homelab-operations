# Hardened image build and isolated integration evidence

**One image built; application acceptance FAIL; NO-GO for deployment.**
See [the integration report](../../../docs/dispatcharr-hardened-image-integration.md).

Built immutable ID:
`sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78`.
It is a retained review artifact, not a deployable release. Production is unchanged.

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
