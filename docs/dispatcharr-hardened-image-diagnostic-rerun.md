# Dispatcharr isolated runtime diagnostic rerun

**BLOCKED before container creation. NO-GO for image binding.**
One invocation of the approved runner stopped at its unchanged fresh capacity
gate with `test_capacity_gate_failed`. No test container was created or started,
no application test ran, and no socket event or phase completion was produced.
There was no automatic retry, rebuild, source correction or deployment.

## Identities and scope

- Approved diagnostics: `a84ee663653c8d2f3292edac05c24c7309087397`.
- Branch: `docs/udm-pro-max-migration-prep`.
- Retained image: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
- Access: Andrew's selected NEST `andrew-media` / `media` profile, pinned
  Rivendell host, authenticated SSH account `murth`.
- Owner confirmed no conflicting administrative operations for this window.
- Only this report and sanitized evidence JSON are changed in this publication.
  Application source, harness, allowlist, source pins and image bindings remain
  byte-for-byte unchanged.

## Preflight findings

The worktree was clean at the exact approved diagnostics commit. All approved
report/harness hashes matched. Read-only image-layer streaming verified the
**14 hardened outputs and four inherited readiness files** against the approved
release contract, without creating a probe container or extracting application
source into published evidence. The original private build receipt remains
`verified` and identifies the exact retained image; its SHA-256 is
`49ba5c723f5f960a3a3cc195b77de491d5633c73262dc6da1faffc1fad76ef78`.

All **33** original production container identities, images, start times, restart
counts, health/status and canonical Config/HostConfig/Mounts fingerprints matched
the prior runtime-acceptance evidence. The four Dispatcharr services and Jellyfin
were healthy. Docker remained version 29.9.2. The json-file logging driver was
available for the reviewed per-container 1 MiB × 2 bounded logging configuration.
The test name was unused. Original receipts and synthetic fixtures were available;
unchanged fixture files matched the prior run's hashes. The updated diagnostics
module and runner matched the approved commit. No credentials were installed or
production policies/databases accessed.

Two read-only comparison issues were resolved before any runner invocation:
Docker Compose is unavailable to the ordinary login's CLI plugin lookup but
available in the accepted root context (v5.6.0); no installation/change was needed.
My initial container fingerprint comparison used JSON whitespace that differed
from the published canonical format. Compact sorted JSON reproduces the prior
fingerprints for every container. This was a comparison correction, not evidence
of production drift, and no expected hash was regenerated.

The preflight sampled capacity at `2026-11-18T03:15:15Z`:

| Measurement | Value |
| --- | --- |
| MemAvailable | 3,570,446,336 bytes |
| Free disk | 7,701,266,432 bytes |
| Load 1 / 5 / 15 | 1.83203125 / 1.03125 / 0.68359375 |

That sample passed. The reviewed runner performs another check immediately before
container preparation and creation. **That later check failed**: MemAvailable must
be at least 2,147,483,648 bytes and one-minute load must be at most 2. The runner
emits only the fixed failure label; it did not preserve the exact failure-instant
values. Do not infer those values from a later sample.

Post-failure telemetry at `2026-11-18T03:17:58Z` showed MemAvailable
3,596,972,032 bytes and load
3.125 / 2.56689453125 /
1.37451171875. This later load exceeded 2 and is consistent with
the refusal. It is not a measurement at the exact gate-failure instant. No cause
for the host's load increase is asserted and no additional infrastructure
investigation was started.

## Execution and isolation boundary

A private exclusive intent receipt was created before calling the approved
runner, preventing automatic re-execution of this attempt. Its SHA-256 is
`ae1dc6cf227f4fd7663a047ad0ce783535d8c653aa219fd48ed83a2a7ba89386`. The runner then failed at the capacity gate,
before fixture/attempt-directory creation, `docker create` or `docker start`.
There was **one runner invocation, zero created containers and zero started
containers**. This is a blocked diagnostic attempt, not an application failure or
an accepted integration run.

The approved planned configuration remains network none, no published ports,
read-only root filesystem, no production networks/volumes/credentials/policies/
databases/socket, disposable tmpfs, no restart, 1 CPU, 1.5 GiB RAM and 256 PIDs,
with exactly the reviewed read-only synthetic fixture mounts. No runtime
isolation observation is claimed because no container existed. No destination
allowlist or resource threshold was changed.

## Application checkpoints and socket findings

| Phase | Result |
| --- | --- |
| PostgreSQL and authenticated Redis | NOT EXECUTED |
| UID1000 Django initialization | NOT EXECUTED |
| Migrations and fingerprint | NOT EXECUTED |
| Celery worker startup and task registration | NOT EXECUTED |
| Actual Redis-backed task execution | NOT EXECUTED |
| Native API and ownership operations | NOT EXECUTED |
| Synthetic Xtream account/group/channel workflow | NOT EXECUTED |
| XMLTV import and EPG mapping | NOT EXECUTED |
| Backend readiness and DW English compatibility | NOT EXECUTED |
| Final acceptance | NOT EXECUTED |

**Last completed application checkpoint: none.** No runtime test count, migration
fingerprint, codec/playback measurement or Celery result is invented. No new
socket-audit event exists to classify: family, operation, destination class,
application UID/test identifier and application call stack are not available.
The original unexpected socket event remains unresolved. The retained image's
previous observed application boundary remains as documented in the prior
[runtime acceptance report](dispatcharr-hardened-image-runtime-acceptance.md).
The earlier 608 offline diagnostic/regression passes are not new runtime results.

## Cleanup and production preservation

No temporary test container, network or volume was created; no removal was
necessary or attempted. The exact test-name lookup is empty, and no new
`runtime-attempt-*` directory exists. The original build receipt, image, previous
runtime receipts and diagnostic evidence remain intact. This attempt's private
intent/preflight/postflight receipts are retained alongside the original build
workspace; they are not copied into Git.

Postflight compared all 33 production records against the fresh preflight:
IDs, images, start times, restart counts, health/status and configuration hashes
are identical. Full Docker network and volume inspection fingerprints are also
identical. The four protected services and Jellyfin remain healthy. There was no
production container operation, application API write, systemd/firewall/VPN/DNS
change, image build/pull/tag change, provider request or playback.

## Published evidence and hashes

| File | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py` | `763839d42e80e933e52918349bd7f34dd816b546b2f2fe0c92b3ff69b326a90e` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_diagnostics.py` | `de5ed39ff92da1002e2f90507511d9dd3cfc878b8e5de55126fb30d467bae432` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_test.py` | `56c68d1412984d7b0351bd0ecc4cc6c4862c6a32bccb0eccd412e9500fca6333` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_diagnostics.py` | `3cbac9f04bf49805543d9e40f87e1f1c3a27af649f46880e4d221b8153142477` |
| `configs/dispatcharr-iptv/hardened-image-integration/diagnostic-rerun-results.json` | `2a19996e1bd8d09d5f36306a9af728496ccff7f7c1b0e4fc2248a8c195dd0934` |

The unchanged harness hashes above identify what was invoked, not modified files.
The JSON includes all 18 verified image source hashes, the reviewed fixture payload
hashes, before/after sanitized container identities, network/volume fingerprints,
receipt hashes, capacity samples and explicit not-executed phase states. This
report excludes its own hash. No raw container configuration, credentials,
provider URL, private policy, database data or recovery archive is published.

## Decision

**NO-GO for image binding or deployment.** The precise blocker is the reviewed
runner's fresh resource-capacity refusal before container creation. No application
source correction is indicated by this attempt because application code did not
run. Wait for a separately authorized attempt in an adequate capacity window,
repeat fresh preflight and preserve the same thresholds and isolation. Do not
reuse or remove the exclusive intent blindly. A future authorization must account
for the consumed runner invocation and explicitly permit another attempt.

No automatic retry, rebuild, provider activation or production change follows
this report.
