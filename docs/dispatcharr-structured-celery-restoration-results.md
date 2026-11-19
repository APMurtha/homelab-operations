# Original Dispatcharr — structured Celery restoration results

**FAIL / NO-GO for original-stack recovery completion.** Exactly one managed start was issued. Source pins, PostgreSQL/migrations, Redis and two fresh uWSGI witnesses passed. The Celery JSON-mode command returned0 with complete290-byte stdout and empty stderr, but its response was rejected by the reviewed structured contract: **`celery_unclassified_failure`**, `reply_output_valid=false`.

No trusted positive default/DVR witnesses were retained from the invalid response. Those false flags are **not evidence that both workers were absent**. The particular JSON/shape/payload rejection is unresolved. Scoped cleanup is verified complete: all four IPTV containers are stopped and protected. Jellyfin and unrelated services are preserved. No retry or diagnostic rollback occurred; native hardening remains suspended.

## Approved release and preflight

Correction: `ee7e6c85258d707bcab35f7521157bb26f9099ac`; [reviewed structured contract](dispatcharr-celery-structured-readiness-fix.md). Local checkout was clean at that exact commit. The candidate verifier checked current/historical rollback bytes and complete67-target closure before host access.

NEST used **Andrew / andrew-media / media**, verified Rivendell hostname and SSH account `murth` UID1000 before root operations. The owner's existing exclusive-administration confirmation was retained; fresh fingerprints matched and no interactive logins were present.

Fresh preflight completed **2026-11-19 00:41:23 UTC**:

- All four original IPTV containers were identifiable/stopped; all33 container fingerprints matched the prior failed-cleanup state. Jellyfin remained running/healthy.
- All67 installed public files matched the current diagnostic baseline: backend `5d37a1a5…`, manifest `52f8c8e1…`, lifecycle `0df62a94…` and all other targets, with exact ownership/modes.
- Original AIO image **`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`** was verified locally. No image build, pull, recreation or binding change occurred.
- Rivendell recovery archive `/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` and independent Denethor copy `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` freshly matched **`ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`**. Archive metadata/manifest, selected original public files and ownership baseline were verified without filesystem extraction or restoration.
- Exact kernel nftables policy, withdrawn public guard/grant assertions, revoked/unblocked guard transaction, private/runtime-anchor permissions and inactive provider authorization passed. No pending/uncertain ownership mutation existed. Persistent data and database-cluster marker were available.
- All four historical backend intent/result files and both earlier rollback generations verified intact and private. No historical receipt was cleared.
- Available RAM **4,624,494,592 bytes**; Docker filesystem free space **7,657,435,136 bytes**. Installed admission passed in **15.002s**, idle95.219–97.685%, steal0–0.05%, load0.40–0.47. Thresholds and sampling were unchanged.

[Sanitized machine-readable evidence](../configs/dispatcharr-iptv/structured-celery-restoration-results.json) retains the actual measurements, source identities, diagnostic records and preservation comparisons. Private administrative receipts remain under `/root/dispatcharr-structured-restoration-20261119T004101Z`.

## Exact installation

At **00:42:11 UTC**, only these two targets under `/docker/dispatcharr-iptv/permanent-streaming/` were installed root:root0644:

| Target | Installed SHA-256 |
| --- | --- |
| `backend.py` | `466b06a23af779d0093d2325d6dce3257a354e4d8899658fb849713e2b1a3065` |
| `manifest.json` | `8c8ea65df72c6ce18238faeb7262c6946b821ad711bdbf9b06174c10b2dc2a5f` |

All65 unchanged files and complete67-target closure passed. Lifecycle stayed **`0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac`**. The installed original inputs verifier passed, and private receipt-directory identity/permissions plus historical hashes were rechecked.

Exact previous backend **`5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b`** and manifest **`52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b`** were preserved root:root0600 under the new private journal's `original/` directory. They were not restored after failure.

No Compose, systemd/reload, guard, firewall, VPN, DNS, broker, worker or Jellyfin configuration change occurred. No protected or unrelated container was recreated.

## One managed start and timeline

At **00:42:40 UTC**, one `systemctl start --no-block dispatcharr-stack.service` request was issued. Return0 meant request acceptance only. Monitoring inspected the same invocation **`a5faf94c2eb046ae95e7980b02e38591`**; no second request followed.

Managed resource admission passed in **15.002s**, idle94.198–96.886%, steal0–0.05%, one-minute load0.35–0.40. The unchanged lifecycle operated through admission, guard/VPN/namespace setup and original AIO/relay startup.

At00:43:41 UTC, VPN, relay and AIO were healthy; gateway was still stopped while the backend check ran. These are point-in-time startup observations, not final running acceptance. The managed unit failed at **00:43:46 UTC**. Terminal status was retained at00:44:17 UTC. Backend failure prevented owned registration/export rebind and gateway-last startup, and the existing scoped cleanup stopped the protected components.

## Same-invocation backend result

Backend invocation: **`c6ff584cb5743e874bfbe94e45863d8b`**. The host retained1574 bytes of validated fixed-schema diagnostics from that invocation only; the backend process exited1 with `backend_stage_failed`.

| Stage | Outcome | Producer elapsed seconds |
| --- | --- | --- |
| Application source pins | PASS;14 hashes | 0.003423 |
| PostgreSQL/migration verification | PASS; return0 | 0.093354 |
| Redis readiness with existing authentication handling | PASS | 0.335667 |
| Fresh Redis-backed uWSGI witnesses | PASS; exactly2 | 0.337854 |
| Structured Celery readiness | **FAIL; `celery_unclassified_failure`** | **9.595837** |

The PostgreSQL pass establishes the unchanged expected migration predicate `184:b00f51e91c5b882cd84d3b2579d074ca`. Earlier passes do not imply those now-stopped services remain operational after cleanup.

### Structured Celery evidence

The exact installed backend was verified before/after startup; its one inspection argv is the approved `celery -A dispatcharr inspect ping --timeout=8 --json`.

| Field | Retained value |
| --- | --- |
| Monotonic command/capture start | `187481.132627` seconds |
| Monotonic command/capture end | `187490.390313` seconds |
| Measured duration | **9.257686s** |
| Celery child return code | **0** |
| Observed stdout / stderr bytes | **290 /0** |
| Capture complete | **true** |
| Reviewed JSON-response contract valid | **false** |
| Trusted positive replies retained | **0** |
| Positive default / DVR witness flags | **false /false** |
| Classification | **`celery_unclassified_failure`** |
| Effective broker comparison | **unknown** |

All broker equality flags are false because `broker_comparison_known=false`; they are not a confirmed mismatch. No authoritative worker snapshots were invented or broker settings changed.

**Interpretation boundary:** `reply_output_valid=false` does not isolate JSON decoding from other contract failures. The reviewed validator also rejects mixed output, duplicate/unexpected identities, error/non-pong payloads and unsupported shapes. It clears role witnesses when response validity cannot be established. The retained record therefore cannot identify which rejection occurred or prove either worker was absent/unhealthy. A valid mapping with just one positive role would have produced a specific missing-role code; this result did not establish that valid subset.

The290-byte raw stdout/JSON was deliberately neither retained nor published. Its content cannot be reconstructed from length, return code or previous attempts. Empty stderr does not make the stdout trustworthy. No claim of a confirmed parser defect, broker problem or startup race is made.

The required positive proofs from **both** roles were not established, so successful process exit could not authorize recovery. No source, timeout, output contract, role requirement, security rule, retry or delay was changed during the attempt. The8-second reply option,40-second subprocess bound and90-second backend limit remained intact.

## Final protection and production preservation

Read-only final verification at **00:45:11 UTC** confirmed:

- All four IPTV containers stopped. Their original IDs/images/configuration fingerprints/restart counts were unchanged; protected-service start timestamps changed as expected for this managed attempt. Gateway was not started.
- All29 unrelated container rows matched preflight exactly, including start/restart/health/status fields. Jellyfin remained running/healthy. Historical unrelated stopped services were unchanged; no blanket healthy/running claim is made.
- Docker process identity, stopped-state complete network inventory and volume inventory matched preflight. No additional network or volume appeared.
- Exact kernel nftables protection persisted. Public guard/grant assertions were withdrawn, guard transaction revoked/unblocked, provider projection empty and private/runtime-anchor checks valid. Full final VPN/grant running acceptance was not completed; the VPN is stopped and assertions are intentionally revoked.
- DW English ownership ledger remained byte-identical to the checkpoint with no pending transaction. Existing Jellyfin LiveTV configuration hash matched its checkpoint. No Jellyfin changes occurred.
- All67 current diagnostic file hashes, the two new private rollback copies and every historical receipt hash verified. The approved structured files remain installed; no automatic diagnostic rollback was performed.

Private result: `/root/dispatcharr-backend-diagnostics/c6ff584cb5743e874bfbe94e45863d8b.result.json`, root:root0600,1495 bytes, SHA-256 **`7280a73a8a7dcc08b05c7a4cb39018acbb1122782d441734f77c4c0add826838`**. There is exactly one new intent/result pair alongside the four unchanged historical files.

## DW English availability and decision

**DW English remains unavailable through the stopped IPTV stack.** Its ownership and Jellyfin configuration are preserved, but API registration readback, current export rebind, gateway serving acceptance and Jellyfin channel-discovery verification were not reached. Existing exports were not manually deleted or rewritten. The recovery manifest had no matching individual export members for an independent byte-baseline comparison, so export-byte preservation/current serving health is not asserted.

**NO-GO for original-stack recovery completion.** The precise blocker is failure to establish an accepted structured response with positive default and DVR pongs; the rejected response's cause remains unresolved. No retry, PostgreSQL/Redis reset, container recreation, broker/timeout/security change, provider activation, playback or native-hardening deployment occurred. Preserve current diagnostics and receipts for review. Further production changes or another managed start require separate authorization.
