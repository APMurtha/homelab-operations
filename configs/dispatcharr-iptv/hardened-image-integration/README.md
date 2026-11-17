# Hardened image input verification and build context

**Build/application integration is blocked pending clarification of the permitted
test Docker daemon. No hardened image has been built.** See
[the current integration report](../../../docs/dispatcharr-hardened-image-integration.md).

Artifacts:

- `inspect_image.py`: stream through Andrew's selected NEST profile. It performs
  read-only image inspect/save, interprets layer order/whiteouts and returns only
  hashes of eight approved source files and four existing readiness overlays.
  It creates no container and transfers no source contents.
- `prepare_context.py`: checks that actual-image hash evidence matches all 12
  required files, runs the approved preparation code against local pinned public
  source, and requires exact patch bytes and all 13 approved output hashes.
  It creates a new local context; it does not invoke Docker, install or deploy.
- `Dockerfile`: immutable base image ID, revision label and one COPY instruction.
  No RUN, network fetch, package installation or production tag replacement.
- `test_inputs.py`: five offline verifier tests, including layering, whiteouts,
  no source disclosure and refusal of incomplete readiness evidence.
- `verification-results.json`: sanitized observed base/source/context identities
  and regression results. A null new-image ID means **not built**.

Example preparation, only after actual-image verification:

```sh
python3 configs/dispatcharr-iptv/hardened-image-integration/prepare_context.py \
  /PATH/TO/PINNED/PUBLIC/SOURCE /PATH/TO/NEW/LOCAL/CONTEXT /PRIVATE/IMAGE-HASH-EVIDENCE.json
python3 -B configs/dispatcharr-iptv/hardened-image-integration/test_inputs.py
```

Do not run build/test containers on Rivendell's daemon until the pending execution
boundary is clarified. Automatic approval review rejected even a stopped,
network-none probe there as a production-container change. A source-export
alternative was also rejected; the accepted replacement verifies hashes remotely
without exporting contents. No denied action ran.

No container runtime harness or installer is supplied in this checkpoint. Real
Django migrations, Celery workers and provider API integration have **not** been
executed; existing mock/source/namespace regressions do not substitute for them.
The report records the test matrix and matched transition proposal still required.
