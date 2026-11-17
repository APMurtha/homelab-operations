# Hardened Dispatcharr image — verified inputs, execution blocked

2026-11-17. `APMurtha/homelab-operations`, branch
`docs/udm-pro-max-migration-prep`. Approved hardening:
`1124d9699097faa5a2b865ad8989da9f5743cfbf`.
Production remains release `227122dcbe9ebc76be46b8a91231350d6c93bdb4`.

**Input preflight PASS. Build and real application integration NOT RUN. NO-GO for
deployment.** No new immutable image identity exists. The authorized single build
attempt has not started. Automatic approval review blocked the proposed temporary
container execution boundary; clarification is pending. This report is a verified
preflight checkpoint, not successful image-build or application acceptance evidence.

## Build provenance and verified inputs

The exact approved commit and all 24 repository files listed in its hardening
report matched their recorded hashes. Andrew's existing pinned NEST profile
verified hostname Rivendell and account murth. No replacement identity, credential
installation or host-key change was used.

The local Rivendell image is exactly:

`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`

Observed logical image size: 4,248,387,073 bytes, linux/amd64. Working directory
/app, root/default image user, entrypoint /app/docker/entrypoint.sh. Config.Volumes
and Config.OnBuild are null. No production environment or credential file was read.

Read-only Docker image save was parsed on Rivendell, resolving layer order and
whiteouts. Only hashes left the host. **All eight source inputs exactly match
source-pins.json**, and these existing application-readiness modifications match:

| Image source under /app/ | SHA-256 |
|---|---|
| apps/proxy/live_proxy/input/buffer.py | 17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810 |
| apps/proxy/live_proxy/input/manager.py | ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf |
| apps/proxy/live_proxy/output/ts/generator.py | db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b |
| apps/proxy/live_proxy/readiness.py | fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b |

The retained historical build-context tar also matched the prior artifact review's
04e270ae…6221c1 hash. Its Dockerfile confirms these overlays belong under
/app/apps/proxy/live_proxy/. No historical image or source was substituted.

Four live host **public source-file hashes** also match this repository:
guard.py, security.py, permanent-streaming/guard_readiness.py and
boot-admission-phase6b3k/admit.py. No private guard state, policy, credentials,
PostgreSQL or Redis data was read. This verifies source identity; it is not a fresh
kernel-rule, tunnel or namespace-grant attestation.

The approved prepare.py reproduces the exact reviewed server.patch and all 13
output hashes from retained public source at pinned commit
2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e. A COPY-only context contains those 13 files,
the image-local provider_contract_hashes.json and Dockerfile. It contains no private
policy, provider data, certificate, runtime state or production configuration.
The four readiness overlays are outside the COPY set and remain inherited.

Complete observed input/context hashes are in
configs/dispatcharr-iptv/hardened-image-integration/verification-results.json.
No approved pin was regenerated to accept drift.

## Capacity and existing tooling

Rivendell reported four CPUs, load 0.17/0.20/0.18, approximately 3.3 GiB available
memory, no swap and 7.3 GiB free on the 58 GiB root filesystem. These observations
support a small COPY-only overlay and a bounded temporary test, subject to a fresh
capacity check before execution. They are not measurements of actual build/test
resource consumption. Proposed test ceiling is one CPU and 1.5 GiB memory; no
production resource-admission threshold or timeout is changed.

Docker 29.9.2 is accessible through the selected profile. Compose and Buildx plugins
are absent. No package was installed. The existing CLI exposes legacy build help
with DOCKER_BUILDKIT=0, including no-pull, network, memory/CPU and image-ID-file
options. Docker documents that fallback for missing Buildx, while marking it
deprecated. [Docker deprecation documentation](https://docs.docker.com/engine/deprecated/)
No actual build was attempted, so daemon build success is not established.

Denethor has ample disk/memory, but its Docker socket is unavailable to the current
account. One noninteractive sudo check reported that a password is required; it was
not retried. No local privilege, group membership, daemon or system configuration
was changed. No other person's credentials were used.

## Execution blocker and actions not taken

Automatic approval review rejected creating/removing a stopped network-none source
probe on Rivendell's daemon, classifying any container creation there as a
production-container change. The command did **not** run. No probe was created.
The same execution boundary affects temporary application-test containers and
potential intermediate build containers on that daemon.

Review also rejected an alternative that would return base64 application source,
classifying it as source-data transfer beyond hash verification. That command did
**not** run either. The accepted alternative performs remote hash-only inspection;
no application source contents were transferred from Rivendell.

The owner was asked to clarify whether temporary build/test containers on
Rivendell's existing daemon are authorized, or to identify another approved Docker
engine. This pending question is not treated as approval. No indirect container
execution, alternate identity or privileged workaround was attempted.

New hardened image ID: **NOT CREATED**.
Build attempts: **0**. New test containers: **0**. Image pulls: **0**.
Production container/service/configuration changes: **0**.

## Tests actually executed

**All 497 existing tests pass**, with no failures, errors or skips. Five new
input-verifier tests also pass. These results are **not real Django/Celery image
integration results**.

| Suite | Tests and result |
|---|---|
| Existing provider/native-adapter/security-contract tests | 139 PASS |
| Existing hardening source/policy/application-dependency fixtures | 66 PASS |
| Existing synthetic TLS/DNS/guard namespace fixtures | 14 PASS |
| Existing protected stack/security/admission/guard/gateway groups | 39 + 26 + 17 + 7 + 3 + 12 + 28 + 50 + 13 + 15 PASS |
| Existing historical persistence / guard / lifecycle design | 26 + 14 + 28 PASS |
| New read-only image/context verifier fixtures | 5 PASS |

The new verifier checks that source bytes never appear in output, later layers
win, whiteouts and opaque app roots cannot adopt stale source, and incomplete
actual-base/readiness evidence refuses before context creation. Existing Caddy
fixtures made 91 isolated synthetic requests. Network fixtures have no external
route and did not contact Rivendell, a broadcaster or a real provider.

Real migrations, Django initialization/HTTP routes/serializers, installed-image
Celery registration/execution and native XC/XMLTV API import have **not run**.
No image runtime/package compatibility result is inferred from mocked dependencies
or source compilation. Sanitized suite counts/log hashes are recorded in the
verification-results file; raw private operational state is not committed.

## Remaining isolated application test matrix

After the execution boundary is resolved and source/capacity checks remain valid:

1. Build once from the verified local image, without pull/package/RUN instructions,
   with a new non-production tag, no network, bounded resources and an image-ID
   receipt. Refuse an existing target tag/context or uncertain prior attempt.
   Inspect the resulting immutable ID and all 13 installed hashes before testing.
2. Use one explicitly owned, temporary test container with network=none, no
   published ports, no production networks, volumes, credentials or Docker socket.
   Override the normal entrypoint. Use isolated tmpfs/application data and bundled
   PostgreSQL/Redis binaries, not production daemons or newly pulled images.
3. Run actual migrations and Django setup against that database. Verify routes,
   serializers, default/custom records, default source flags and admin permission
   handling. Create a separate local/custom DW-shaped fixture at channel 9001;
   preserve its identities and profile/mapping fields throughout native imports.
4. Execute the actual Celery worker/task code with the isolated broker, testing
   default/periodic denial, explicit jobs, account-create discovery, stream/group
   selection, owned import, XMLTV programme processing and safe uncertain outcomes.
   Do not substitute Celery eager/mocked functions for worker-execution evidence.
5. First verify the unmodified security endpoint/client refuses missing or
   non-AirVPN policy/grant state. The namespace has no real AirVPN owner. Happy
   synthetic cases may use clearly labeled in-memory transport/policy fixtures,
   but must report that boundary and cannot claim a production-ready grant.
   No host guard/VPN/DNS configuration is reused or modified.
6. Capture only safe test IDs, status/counts and redaction results. Compare bundled
   readiness/worker behavior, local/custom stream semantics and all original
   source/image contracts. Do not initiate media playback. Preserve diagnostics
   on failure; do not fix approved source and rebuild without review.
7. Remove only identified temporary test resources. Recheck the production
   identities/health and confirm no port, network, volume or tag changes there.

A tested application-runtime harness is still required. This checkpoint does not
include an unexecuted harness and label it accepted integration coverage.

## Matched deployment proposal — not installed

The proposal cannot be finalized with an immutable AIO pin until the build and
real application matrix pass. It is deliberately not an executable Compose
change or installer.

- Replace only the AIO image with its actual new immutable identity. Keep the VPN,
  relay and gateway image identities unchanged. In particular, verify.py currently
  shares PATCHED between AIO and relay: split their expected identities so updating
  the AIO does not silently upgrade or repin the relay.
- Update the AIO source/API image pins, all 13 hardened runtime expectations and
  affected candidate/lifecycle/transition manifest hashes as one reviewed set.
  Preserve original readiness hashes and keep the historical controller disabled.
- Add exactly two AIO read-only inputs: existing /run/dispatcharr-guard-status to
  /guard-status, and a separately approved root-private provider-policy directory
  to /run/dispatcharr-provider. Extend exact mount verification accordingly;
  continue rejecting extra, writable, duplicated or unsafe mounts. Preserve the
  existing private /guard mount and every relay mount, privilege and resource cap.
- Keep the existing VPN owner, Docker network, ports, DNS/IPv6, nftables, kernel
  policy, systemd lifecycle/drop-in ordering, timeouts and admission thresholds.
  No new daemon, port, bridge, secret store or privileged relay is needed.
- Review actual resource measurements. Source adds bounded transport/policy code
  and disables automatic remote provider scheduling; it adds no worker service.
  The image layer is expected to be small, but no built size or measured runtime
  overhead is claimed yet.
- Keep live native registration and removal disabled. Image deployment alone does
  not authorize provider destinations, credentials, media, Jellyfin or playback.

Before a future scoped rollback, withdraw provider approval and establish known
API/journal outcomes, inactive provider/source records, disabled schedules and
reconciled provider jobs. Do not restore the unhardened image while uncertain
native work can execute. Restore the complete previous AIO image/source/mount
verifier set through the approved managed lifecycle, retaining the firewall/VPN
owner and unrelated services. Do not purge unrelated queues, reset data or force
ownership deletion. No production rollback was needed or attempted in this task.

## Current production observations and recommendation

The four protected services and Jellyfin were healthy with restart count zero
before/after read-only verification. Container IDs remained:

| Service | Container ID prefix |
|---|---|
| Dispatcharr | 7dbfca3d171d |
| Dedicated VPN | 1b9d20c93194 |
| Managed relay | 3aa41213fdc8 |
| Gateway | 448ceeb80a51 |
| Jellyfin | 6798247b9099 |

No production database, Redis, credentials, playback, systemd, firewall, VPN, DNS,
network or container lifecycle operation occurred. No image was built or retagged.

**NO-GO for deployment and live onboarding.** Inputs pass and a reproducible
build context is ready, but no hardened image identity or real application
acceptance exists. Resolve the temporary-container execution boundary, then
resume the single authorized build and isolated integration matrix. This is an
execution-approval blocker, not evidence that the approved patch failed.

## Checkpoint artifact hashes

| File in configs/dispatcharr-iptv/hardened-image-integration/ | SHA-256 |
|---|---|
| `Dockerfile` | `ce726b756f63f42f90d24d447ec18aaf245781f0491738f238945f4a9e1a58ad` |
| `README.md` | `4a194a113da12b1c8935d880cc687d7025cb87b8cdaac4c2787511ef4c113f4e` |
| `inspect_image.py` | `04018eb2fba2e89eb920120646dcf476258441e659edc375c20ce60574ee8c85` |
| `prepare_context.py` | `3a62b3316a9f609ac6c9fd1c202c8e5f66bea30ff46eab5873d653dc63ce2463` |
| `test_inputs.py` | `4486c489ca2b4bc2eade87d22f996fe0f9f4b8faf8d49d5f4c7775436e660889` |
| `verification-results.json` | `ed5bb89b00ea86a1afb0a45b390ef70008b44728b79a685e27e2b8395fb9e299` |
