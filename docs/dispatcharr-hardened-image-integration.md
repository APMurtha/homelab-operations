# Hardened Dispatcharr image integration — build complete, runtime failure

2026-11-17 US/Eastern (build 2026-11-18 UTC).
Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.
Approved hardening `1124d9699097faa5a2b865ad8989da9f5743cfbf`; resumed checkpoint
`a956d711a1e843f91b6685e3fec9c50c913b09b8` after explicit authorization for temporary
isolated Docker containers. Production remains `227122dcbe9ebc76be46b8a91231350d6c93bdb4`.

**Build completed once. Real Django startup FAIL. NO-GO for deployment or live
provider onboarding.** No second build, deployment or production modification.

## Build provenance and source verification

Base, verified locally on Rivendell:
`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.

New immutable review image:
`sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78`.

Review-only tag `local/dispatcharr-native-hardening:1124d96-review`.
Created `2026-11-18T00:20:21.163271177Z`; linux/amd64. Logical size
4,249,021,342 bytes, 634,269 bytes above the verified base. This is logical image
metadata, not a measurement of allocated disk or application overhead.

Andrew's selected NEST profile verified Rivendell and SSH account murth. No other
identity, credential installation or host-key change was used. All 24 approved
hardening repository artifacts, eight original image source inputs, exact
server.patch and all 13 prepared Python outputs matched their approved hashes.
All 13 installed outputs and four inherited readiness overlays matched after the
build. `core/provider_contract_hashes.json` is also included in the verified
context. Full exact hashes are retained in
`configs/dispatcharr-iptv/hardened-image-integration/verification-results.json`.
No approved source/pin was changed or regenerated to accept drift.

The inherited readiness hashes under `/app/` remain:

| Source | SHA-256 |
|---|---|
| apps/proxy/live_proxy/input/buffer.py | 17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810 |
| apps/proxy/live_proxy/input/manager.py | ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf |
| apps/proxy/live_proxy/output/ts/generator.py | db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b |
| apps/proxy/live_proxy/readiness.py | fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b |

The local base had no ONBUILD actions or declared volumes. Existing Docker 29.9.2
legacy builder was used because Compose/Buildx are absent. No tooling or package
was installed. Dockerfile has immutable FROM, label and COPY only. Build flags:
no pull, network none, no cache, 512 MiB memory/swap ceiling, 0.5 CPU ceiling and
180-second caller deadline. No RUN, package download, base upgrade or production
tag replacement. Read-only metadata-format adjustments happened before execution;
there was exactly **one actual build command**, exit 0.

Fresh capacity gate passed: 7,781,158,912 bytes free on /tmp filesystem,
3,537,104,896 bytes MemAvailable, load 0.477/0.324/0.231. Runtime gate required
at least 2 GiB available and load below 2. No admission thresholds were changed.

## Actual runtime sequence and failure boundary

A first network-none bootstrap stopped because the overridden entrypoint had not
created the stock `dispatch` account. No Django operation occurred. Inspection
of the pinned entrypoint and read-only production process IDs established the
real contract: default PUID/PGID1000; application/Celery/PostgreSQL/Redis workers
are UID/GID1000. A synthetic passwd/group fixture reproduced that identity without
reading production passwd, environment or credentials.

The resulting isolated test initialized the image's **real PostgreSQL 17**, created
its temporary database, and passed **authenticated real Redis PING**. It forked
the Django process at UID/GID1000. `django.setup()` then failed:

```text
ModuleNotFoundError: No module named 'apps.api'
```

Testing stopped at this confirmed image failure. No migration or native API test
was reached. A bounded filesystem-only diagnostic confirmed the explanation:

| Path / check | Base | Built image / UID1000 result |
|---|---|---|
| /app | root:root 0755 | root:root 0755 |
| /app/apps | root:root 0755 | root:root **0700** |
| /app/apps/api | root:root 0755 | 0755, inaccessible through parent |
| /app/core | root:root 0755 | root:root **0700** |
| /app/core/provider_security.py | not present in original base | root:root 0644, inaccessible through parent |
| Root-private synthetic policy directory/file | 0700/0600 fixture | UID1000 read refused |
| Separate root-public synthetic marker | 0755/0644 fixture | UID1000 read succeeds |

The build wrapper introduced the directory-mode defect: its private transport
workspace used umask 077; newly created application directories inherited 0700.
COPY --chown=0:0 preserved those modes. Hash equality proved source bytes, but did
not prove runtime readability. This is a packaging failure, not missing apps.api
source or evidence that dependency installation is needed.

`build_once.executed.py` preserves the executed wrapper without its appended
source payload, with its final newline normalized. `build_once.py` now contains an offline, unit-tested future recipe
correction: keep context root 0700, explicitly set public code directories 0755
and files 0644. **That correction was not built. The immutable image above still
has the defect.** It is not permission to retry.

A second, independent blocker exists in approved server code:
`provider_security.policy()` requires root-owned `/run/dispatcharr-provider` mode
0700, and its reader requires root-private policy files. Actual Django/Celery
workers are UID1000. Permission-faithful testing confirms they cannot read that
interface. This was established from pinned source plus real UID access, not a
successful API execution. No policy permissions were relaxed, no worker elevated,
and no server patch changed. A separately reviewed minimal unprivileged policy
interface is required before another candidate can be accepted.

Observed installed versions: Python 3.13.17, Django 6.0.9, Celery 5.6.3, OpenSSL
3.0.13. Library imports/version queries are not application or worker acceptance.

## Isolation, resources and cleanup

Runtime containers used network=none, only loopback, no default external route,
no published ports, no production network, volume, credentials, Redis/PostgreSQL
or Docker socket. No production source was bind-mounted. Three read-only binds
contained only this test's source and synthetic passwd/group. Root filesystem
was read-only; all database/runtime writes were bounded tmpfs. Limits: one CPU,
1.5 GiB memory including swap ceiling, 256 PIDs; no restart policy. Root supervisor
had only scoped AIO-style capabilities for isolated setup and dropping UID;
application executed without root. No privileged container or NET_ADMIN.

Observed cgroup memory peak for the failed application bootstrap: 143,413,248
bytes. This is not a steady-state provider workload measurement. No provider,
broadcaster or media request occurred. The later filesystem probe used only
SETUID/SETGID to demonstrate actual UID1000 reads. Its public marker explicitly
said it was not a grant. No real AirVPN/grant acceptance was fabricated.

Each exact owned test/probe container was removed; temporary databases and broker
state were tmpfs and disappeared. Final label inventory found no remaining test
containers. Public-source build context, failed image and private diagnostic
receipts remain for review in the task scratch directory; there are no permanent
test networks or volumes. Raw logs/payloads are not in Git.

All **33** pre-existing containers match the before-build ID, image, state,
StartedAt, restart-count and health snapshot. Test receipts also verified unchanged
Docker network inventories. This is an identity/health comparison, not a fresh
kernel firewall or VPN-grant attestation; production networking was not accessed
or changed for test setup.

## Regression results and application coverage

All **497 existing regressions PASS**, no failures/errors/skips. All **seven**
image-input/build-mode unit tests PASS. Synthetic isolated TLS/DNS and Caddy tests
had no external route; Caddy made 91 synthetic fixture requests.

| Existing suite | Passed |
|---|---:|
| Provider CLI / native adapter | 139 |
| Hardening source/policy fixtures | 66 |
| Isolated TLS/DNS/guard transport fixtures | 14 |
| Protected stack/security/admission/lifecycle/gateway groups | 210 |
| Historical persistence | 26 |
| Prior guard interface | 14 |
| Guard lifecycle design | 28 |

New tests cover layering, whiteouts, opaque roots, source/hash refusal and the
future build-context mode correction under real umask 077. They do not repair
the retained image. Suite counts and exact log hashes are in verification JSON.

| Real image matrix | Outcome |
|---|---|
| Bundled PostgreSQL initialization | PASS, isolated PostgreSQL17 |
| Authenticated bundled Redis | PASS |
| Actual UID1000 Django initialization | **FAIL**, inaccessible application directories |
| Migrations, Django routes/serializers/native account creation | NOT RUN |
| Celery task registration/execution and periodic restrictions | NOT RUN |
| Native group/stream resolution, bounded import and ownership | NOT RUN |
| XMLTV import/programmes, exact EPG mapping, interrupted mutations | NOT RUN |
| DW English runtime compatibility / backend readiness | NOT ACCEPTED; inherited hashes preserved only |
| Actual AirVPN namespace / provider grant | NOT TESTED; no real grant |

The remaining test bodies in runtime_test.py are prepared and **unexecuted,
unvalidated**. They must not be cited as passing integration evidence. Harness
review must also address UID1000 traversal of its private fixture directory
before the fixture client tests are attempted. Existing mocked/source tests
cannot substitute for this incomplete matrix.

## Matched deployment and rollback proposal — not installed

There is no deployable matched transition for this failed image. Before proposing
installation, review a policy-reader interface compatible with UID1000, authorize
a new single build with corrected code-directory modes and reviewed server pins,
then complete the real Django/Celery/API matrix above.

For a future accepted image, the coordinated proposal must:

1. Replace **AIO only** with a newly accepted immutable image. Keep VPN, relay and
   gateway pins unchanged. Split verify.py's currently shared PATCHED identity
   so the relay stays on 14c837…ad21 when AIO changes.
2. Update exact server source/API contracts, AIO image expectations and affected
   manifests together. Preserve all four readiness hashes, admission thresholds,
   timeouts, managed ordering and disabled historical controller.
3. Add the AIO's exact read-only public guard-status mount and a separately
   reviewed UID1000-readable provider-policy interface. The formerly proposed
   root-only policy mount is **not usable**; its replacement requires review.
   Preserve existing private guard consumers and all relay/gateway restrictions.
4. Preserve VPN owner, Docker network, published ports, nftables policy, DNS/IPv6,
   namespaces and resource caps. No new service or infrastructure is proposed.
5. Keep native live registration/removal gated until server acceptance, exact
   destination approval and separate owner authorization. DW relay is unchanged
   and is not a generic Xtream media transport. No Jellyfin export of new providers.

Future rollback must first establish known API/journal outcomes, withdraw native
provider approval, disable relevant sources/schedules and reconcile in-flight
provider jobs. Never restore an unhardened image with uncertain jobs capable of
network access. Restore the complete prior AIO image/source/mount/verifier set
through the reviewed managed lifecycle, preserving firewall, VPN owner, relay,
gateway and application data. Do not purge unrelated queues or force deletion.
This task required no production rollback because nothing was deployed.

## Final production state and recommendation

| Service | Preserved container ID prefix | Final health / restarts |
|---|---|---|
| Dispatcharr | 7dbfca3d171d | healthy / 0 |
| Dedicated VPN | 1b9d20c93194 | healthy / 0 |
| Relay | 3aa41213fdc8 | healthy / 0 |
| Gateway | 448ceeb80a51 | healthy / 0 |
| Jellyfin | 6798247b9099 | healthy / 0 |

No production container creation/recreation/start/stop/removal, application-data or
credential access, systemd change, firewall/VPN/DNS change, package installation,
image pull, playback or real-provider request. Working production tag and image
are unchanged.

**NO-GO for deployment or real-provider onboarding.** The single approved build
produced a precisely identified but unusable image. Required next review:
packaging-mode correction, unprivileged provider-policy design/implementation,
separately authorized new build, then complete real application acceptance.
Stop here; production remains healthy and unchanged.

## Artifact hashes

The following table covers this task's implementation/evidence files. The report
itself is identified by its enclosing Git commit to avoid a self-hash cycle.

| File under configs/dispatcharr-iptv/hardened-image-integration/ | SHA-256 |
|---|---|
| Dockerfile | ce726b756f63f42f90d24d447ec18aaf245781f0491738f238945f4a9e1a58ad |
| README.md | 3406bbb03474f3f298f9d1c34ce34d69fd3d4d55db4ae2437d256ccab47d9ac6 |
| build_once.executed.py | e09671f1063e9f939a07dce9bf647b8660af8bc750b752597ca65895919aa74e |
| build_once.py | 7e48d8844227dcc2c4ddb1ab274f5f882ecd7a3c84cb83f3b7662f588f9f48fb |
| inspect_image.py | 04018eb2fba2e89eb920120646dcf476258441e659edc375c20ce60574ee8c85 |
| permission_probe.py | 62a7917e37cecff941dfa0404a0598bac6e0e68fe1bf4a9a9edf93ed338ff122 |
| prepare_context.py | 3a62b3316a9f609ac6c9fd1c202c8e5f66bea30ff46eab5873d653dc63ce2463 |
| run_runtime.py | 14e443151ba46db5b905560a3728c189f543639aa0e7f0f6173c9e9c7e5925dd |
| runtime_test.py | 06f55562e7f314fef4ebed2baa52369dcaf2692c3c7ff18bc16de650f4715a2c |
| test_build_modes.py | f88eaa83c4a855fbf3afc2a93b8c01d4bebdca835f45f0176778451d27014a51 |
| test_inputs.py | 4486c489ca2b4bc2eade87d22f996fe0f9f4b8faf8d49d5f4c7775436e660889 |
| verification-results.json | 042a16eac25b00e28840d1025832c91084b5c6ab3395904cda03a4dfb3b8939c |
