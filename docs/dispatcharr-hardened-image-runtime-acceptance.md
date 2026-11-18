# Corrected hardened image — partial runtime evidence, NO-GO for binding

Approved release: `b08b1167e277b6b4e551185e4a9d50035cb01a8c`.
Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.
Execution date: 2026-11-17 US/Eastern / 2026-11-18 UTC.

**One build completed successfully. Application acceptance aborted. NO-GO for
binding this image into the coordinated release.** No rebuild, production
installation, image binding change, real provider authorization or playback.

New immutable image:

`sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`

Retained review tag:
`local/dispatcharr-native-hardening:policy-lifecycle-review-v2`.

## Preflight and single build

The worktree was clean at the exact approved commit. Every changed-file hash from
the approved integration report and all 80 transition mappings matched. The
reviewed prepare.py reproduced the exact patch and 14 outputs from the eight
pinned upstream inputs. The COPY-only context contained 16 files: Dockerfile,
14 Python outputs and the image-local source manifest. No pin was regenerated.

Andrew's selected NEST profile verified host rivendell and SSH account murth.
The four production services and Jellyfin were healthy. The original local base
was present at its exact immutable ID:

`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`

Fresh stopped, network-none probes rechecked all eight upstream input hashes and
four inherited readiness hashes before the build. The new review tag was unused.
The previous failed image was neither used as a base nor used for testing.

Preflight capacity: 7,721,566,208 bytes free on the /tmp filesystem,
3,583,602,688 bytes MemAvailable, load 0.241/0.369/0.361. The recipe performed its
own fresh capacity gate before building. Docker 29.9.2's existing legacy builder
was used; no package or builder installation occurred.

Exactly one build command ran, exit 0: immutable local base, pull disabled,
network none, COPY-only Dockerfile with no RUN, 512 MiB build memory/swap ceiling,
0.5 CPU ceiling and bounded caller deadline. Dockerfile revision identifies the
unchanged approved application sources at 0b8ac7d. No production tag was replaced.

Image created `2026-11-18T02:04:37.281233096Z`; logical size 4,249,031,329 bytes.
All **14 hardened outputs plus four inherited readiness files** matched their
approved hashes after building and again inside the runtime container. Full
input/output hashes and the private build-log hash are in the sanitized evidence
JSON. Source bytes, Dockerfile and reviewed build recipe were not modified to
accommodate a failure.

## Actual ownership, modes and policy-reader results

Inside the actual image, all 18 checked source files are root:root 0644. Required
application-code parent directories, including /app/apps and /app/core, are
root:root 0755. The test validates every parent for the 14 overlay files before
application execution. The original packaging defect is resolved in this image.

The observed host transport and context roots remain mode 0700, owned by the
selected SSH account. Context application directories are 0755 and files 0644.
Only public synthetic fixture files were bind-mounted into the test container;
the private transport/context parent was not mounted. Docker COPY --chown=0:0
supplied root image ownership, rather than changing the host account's ownership.

The disposable root supervisor used the reviewed publisher with an explicitly
synthetic policy and synthetic guard/grant records. Children switched to actual UID/GID1000 with supplementary groups cleared and
demonstrated:

- Reading the current root-published authorization projection.
- Refusal to traverse the root-private provider policy directory.
- Refusal to write to the public status directory.
- Refusal after actual root withdrawal/unlink.
- A new opaque generation after explicit synthetic republication.

The source policy stayed root:root 0700/0600; public directory/records retained
0755/0644 ownership/modes and current test namespace binding. No real provider
policy or production grant was loaded. **These are filesystem/protocol checks,
not evidence of a real AirVPN connection or production namespace authorization.**
Additional negative-state fixtures were prepared, but their application test
results were not retained and are not claimed as passing image acceptance.

## Actual application progress and stop condition

The image's real PostgreSQL **17** initialized its disposable database. Its real
Redis passed authenticated PING. Application execution used UID/GID1000 and the
installed image's Python/Django/Celery components; no eager or mocked worker was
substituted for worker startup.

The retained application log reached the first native security API test:

```text
WARNING django.request Forbidden: /api/core/provider-security/
UNEXPECTED_EXTERNAL_NETWORK_ATTEMPT_BLOCKED
```

The audit guard introduced by this test fixture terminates the application before
an unallowlisted socket operation is allowed. It **did not capture the event's
socket family, address representation, call stack or destination**. Consequently,
the retained evidence cannot distinguish a genuine external attempt from a local
socket/hostname event rejected by an overly narrow test allowlist. The marker is
not proof that external traffic occurred. Network=none, loopback-only interfaces
and absence of an external route independently prevented WAN/provider access.

This diagnostic omission is a test-harness defect. It was not treated as proof
that server hardening failed, and was not bypassed or relaxed to obtain a pass.
Runtime testing stopped; no second test container or build was attempted. No
approved server source was changed. The exact executed fixture is published for
review with its SHA-256.

The parent reported application_result_missing because the audit guard exited
the child before its final JSON/unittest report was written. The runtime container
exited 1. Earlier warnings about missing settings/notification tables occurred on
fresh-database startup before migration; they are not established as the abort
cause.

### What is and is not established

| Area | Retained result |
|---|---|
| Packaging, 14 source outputs and four inherited readiness files | PASS |
| Actual UID1000 public/private policy permissions and root revocation | PASS |
| Disposable PostgreSQL17 and authenticated Redis bootstrap | PASS |
| Django initialization/migrate reaching test execution | Reached according to harness control flow and API log; migration count/fingerprint not retained |
| JWT/API setup and real Celery worker initialization | Reached according to setup ordering before the API test; independent worker/task receipts not retained |
| Successful Celery task execution / default and DVR queue probes | NOT VERIFIED |
| Complete native account/group/channel/XMLTV workflow | NOT VERIFIED |
| Programme/EPG mapping and ownership interruption scenarios | NOT VERIFIED |
| Missing/expired/inconsistent authorization application cases | NOT VERIFIED beyond the separate actual revocation/permission probes |
| Two uWSGI heartbeats and local HTTP health | NOT VERIFIED |
| DW English runtime compatibility and credential-redaction assertions | NOT VERIFIED; inherited source contracts preserved |
| Real AirVPN or live-provider behavior | NOT TESTED / NOT AUTHORIZED |

Successful Django initialization, migrations and worker-context entry are inferred
from the fixture's sequential control flow before the logged API test. Their
intermediate metadata was held in child memory and lost on termination. No exact
migration count/hash, application test count, completed task count or successful
native import is invented. This is **partial progress**, not application PASS.
The earlier approved 570 offline regressions are baseline evidence; they were not
rerun and are not presented as 570 runtime tests in this task.

## Test-only changes and reproducibility

runtime_test.py was updated before execution to remove obsolete expectations that
UID1000 must fail every native registration because policies are root-private.
It now uses the reviewed public projection, root permission/revocation probes,
actual source/mode checks and a separate unapproved fixture for uncertain writes.
Its synthetic DW-shaped records protect channel 9001 and the reserved identity;
its prepared positive path uses actual native APIs and a real Redis-backed Celery
worker. Later prepared uWSGI and queue probes were not accepted as executed.

Prepared positive transport fixtures stub only VPN context/route and synthetic DNS
answers, and redirect the specifically approved synthetic IP dial to loopback.
TLS certificate/hostname verification remains enabled. No such fixture modifies
image bytes or constitutes a real VPN grant. That positive workflow was not
accepted, so DNS/TLS/native fetch success is not claimed from it.

The published source matches byte-for-byte the runtime_test.py payload actually
sent to this test container. Static parsing passed. It remains an **unaccepted
runtime harness** until its audit diagnostics and phase evidence retention are
reviewed. Do not rerun it automatically or broaden its allowlist without review.
No server source, source pins, image expectation or production binding was edited.

## Isolation, resources and cleanup

One started application-test container:
`a77b4651fa150015079fb10ec20ea24342c05936c2a4fbdd88982ea2873062de`.
Two owned source-hash probes remained stopped and were removed. The build's
intermediate resources left no additional container behind.

The application container used network none, only lo, no external default route,
no published ports, read-only root filesystem, no privilege flag, no NET_ADMIN or
SYS_ADMIN, no restart, one CPU, 1.5 GiB RAM including swap ceiling and 256 PIDs.
Database, broker and application state used bounded tmpfs. Its three read-only
binds contained only this run's synthetic source/passwd/group fixtures. No
production network, volume, Docker socket, provider policy, credential or database
was available inside it. No host DNS/VPN/firewall setting was changed.

Observed cgroup peak memory: **287,543,296 bytes**. This is the aborted bootstrap/
early-test workload, not steady-state provider or playback resource usage.

The exact owned application container and both probes were removed. Disposable
PostgreSQL/Redis/application tmpfs data disappeared. Final full inventory is the
original **33 containers**, with no owned test container remaining. The new image,
review tag, private build receipt/logs and public source context remain for review.
No image pruning, volume deletion or production rollback occurred.

## Production preservation

Before/after comparisons cover every original container's ID, immutable image,
StartedAt, restart count, status, health, and SHA-256 of Config/HostConfig/Mounts.
Configuration values, including environment data, were hashed on Rivendell in
memory only; no plaintext settings were returned, persisted in evidence or passed
to tests. Docker network definitions/endpoint membership and volume inventory
hashes also match. All full snapshots are equal before build and after cleanup.

| Service | Preserved container ID prefix | Final health / restarts |
|---|---|---|
| Dispatcharr | 7dbfca3d171d | healthy / 0 |
| Dedicated VPN | 1b9d20c93194 | healthy / 0 |
| Relay | 3aa41213fdc8 | healthy / 0 |
| Gateway | 448ceeb80a51 | healthy / 0 |
| Jellyfin | 6798247b9099 | healthy / 0 |

The production AIO and relay remain on the original 14c837…ad21 image. No
production Compose/systemd operation, configuration write, Redis/PostgreSQL access,
provider request, Jellyfin modification or playback was performed. This comparison
is not a fresh kernel-table/VPN attestation; those production controls were not
modified for the test.

## Decision and next review

**NO-GO for binding e37c7a…e64b4be into the coordinated release.**
release-contract.json still has aio_image=null. Production image pins are unchanged.

The new image resolves the demonstrated packaging and unprivileged policy-access
blockers, but the complete real application acceptance matrix did not finish.
Review the audit guard before authorizing another isolated test with this same
retained image: persist sanitized event family/address-class/stack and phase
checkpoints before termination, distinguish local IPC/loopback representations
from external operations, and retain migration/task/test receipts on every exit.
Do not assume the blocked event was harmless or modify server source without
specific evidence and approval.

No rebuild is justified by this result. A separately authorized diagnostic/test
run can reuse the exact immutable image after test-only corrections are reviewed.
Only a completed application matrix supports a later image-binding proposal.
Stop here; no automatic retry, deployment, provider activation or playback.

## Evidence hashes

Complete approved/observed source hashes, permissions, isolation, production
fingerprints and sanitized outcomes are in runtime-acceptance-results.json.
The report itself is identified by its enclosing Git commit.

| File | SHA-256 |
|---|---|
| configs/dispatcharr-iptv/hardened-image-integration/runtime_test.py | 9d789dc868276340fbca832c7d0f8d34741f57a450033188f75ae6bfb1aae6ca |
| configs/dispatcharr-iptv/hardened-image-integration/runtime-acceptance-results.json | d87754caf1ed874362f558eb7a17c17b09494a1030670ed12dbb2632c12df87e |
| configs/dispatcharr-iptv/hardened-image-integration/README.md | a1f090ed73ef9eed1699f74895df92f617a505a54cf42b566964d1f839c43087 |
| configs/dispatcharr-iptv/hardened-image-integration/build_once.py | 009c0a70be6b41aadcb726de821feba8ec825d0b1be3c76fb266aee772c5d7d6 |
| configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py | 1cafc87802fc6558d105e9860809a42e24be20cc933a928079efd7fe07e95c64 |
| configs/dispatcharr-iptv/hardened-image-integration/Dockerfile | 42dfee8640d31b41bca3db95009f8acd25f97c4909c0f707448c413a00a4dc25 |
