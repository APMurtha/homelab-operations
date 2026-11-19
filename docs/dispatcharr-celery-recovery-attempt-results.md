# Original Dispatcharr recovery — Celery diagnostic attempt

**FAIL / NO-GO for original-stack recovery completion.** The one authorized managed start reached Celery readiness and failed. The inspection child returned **0**, but only one conforming `OK/pong` reply was parsed, from DVR; no conforming default-role reply was parsed. Its complete267-byte stdout did not match the reviewed formatter, so the fixed classification is **`celery_unclassified_failure`**. This is different from the previous return69 incident. It does not prove the default worker was absent or failed to send any response.

Managed cleanup is verified complete. All four IPTV containers are stopped and protected. The two approved diagnostic files remain installed; no retry or diagnostic rollback occurred. Jellyfin remains healthy and unchanged. Native hardening remains suspended.

## Authorization, identity and preflight

Approved correction: `1f73b94f05888927626c69a1b3b0db4246a090ee`; [reviewed correction](dispatcharr-celery-diagnostic-correction.md). Local checkout was clean at that exact commit. Offline candidate/rollback verification and complete67-target closure passed before host access.

NEST selected **Andrew / andrew-media / media**. Remote hostname Rivendell and SSH account `murth`, UID1000, were verified before authorized root operations. The owner's existing exclusive-administration confirmation was retained; fresh fingerprints matched and `who` showed no interactive logins. No target/account switch occurred.

Fresh preflight completed **2026-11-18 23:54:14 UTC**:

- All four original IPTV containers were identifiable and stopped. All33 container fingerprints matched the last failed-cleanup state, including Jellyfin running/healthy.
- All67 installed public files matched the **current diagnostic baseline**: backend `c3b52ec9…`, manifest `07faa8cc…`, unchanged lifecycle `0df62a94…`, and the other64 original targets. Ownership/modes were verified.
- Original AIO image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` was present locally with exact identity.
- Rivendell archive `/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` and independent Denethor copy `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` both freshly matched SHA-256 **`ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`**. Archive metadata/manifest and selected original public-file/ownership records were checked without extraction or restoration.
- Exact kernel nftables policy, withdrawn public guard/grant assertions, revoked/unblocked guard transaction, runtime anchors and inactive provider authorization passed. No pending/uncertain ownership state existed; the ownership ledger matched the checkpoint. Persistent data and database-cluster marker were available.
- Historical private diagnostic receipts and previous root-private rollback copies matched their approved hashes and permissions. They were not cleared or replaced.
- Available memory **4,608,245,760 bytes**; Docker filesystem free space **7,663,706,112 bytes**. Installed admission passed in **15.002s**, CPU idle92.904–97.286%, steal0–0.05%, load0.26–0.31. Existing thresholds/sampling were unchanged.

[Sanitized machine-readable evidence](../configs/dispatcharr-iptv/celery-recovery-attempt-results.json) retains the preflight, precise admission observations, current diagnostics and preservation comparisons. Private administrative receipts are under `/root/dispatcharr-celery-recovery-20261118T235349Z`.

## Installation

At **23:54:46 UTC**, only the following files under `/docker/dispatcharr-iptv/permanent-streaming/` were installed root:root0644:

| File | Installed SHA-256 |
| --- | --- |
| `backend.py` | `5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b` |
| `manifest.json` | `52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b` |

All65 unchanged files and complete67-target closure passed. Lifecycle remained **`0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac`**. The installed original inputs verifier passed. Existing receipt-directory identity/permissions and historical receipts were verified again.

Exact previous rollback versions were preserved under the private attempt journal's `original/` directory: backend **`c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8`** and manifest **`07faa8cce4c643c0a580787b2514c955ddbc4cd0cbff77b61209de9dd97815a4`**, root:root0600. No restoration of these files was performed after failure.

No Compose, systemd, image, broker, worker, firewall, VPN, DNS, guard or Jellyfin configuration changed. No daemon reload occurred. No containers were recreated.

## Single managed start

Exactly one `systemctl start --no-block dispatcharr-stack.service` request was issued at **23:55:18 UTC**. Request return0 was treated only as job acceptance. Subsequent monitoring inspected the same unit invocation **`be9457f7d9bb432d9260e8363b150395`** and never launched another start.

The managed admission gate passed in **15.002s**, CPU idle94.763–97.133%, steal0–0.101%, one-minute load0.33–0.39. The existing guard/VPN/backend/registration/gateway-last ordering was preserved. At23:55:52 UTC the VPN and relay were healthy, AIO was starting, and gateway remained stopped. These are startup observations, not final running acceptance.

The unit failed at **23:56:23 UTC**. Terminal status was retained at23:56:27 UTC. Scoped cleanup stopped all protected components. Backend failure prevented registration/export rebind and gateway startup.

## Same-invocation backend diagnostics

Backend invocation: **`1f131f6a3a1ee5d26654b9fbe7cc4065`**. Host capture accepted its strict fixed-schema records from that invocation only, retaining1576 diagnostic bytes. The backend process exited1 with reason `backend_stage_failed`.

| Readiness stage | Result | Producer elapsed seconds |
| --- | --- | --- |
| Pinned application sources | PASS;14 hashes | 0.007369 |
| PostgreSQL / migration fingerprint | PASS; return0 | 0.139043 |
| Redis readiness (existing authentication handling) | PASS under unchanged predicate | 0.597738 |
| Fresh uWSGI Redis-backed witnesses | PASS; exactly2 | 0.600052 |
| Celery default/DVR readiness | **FAIL; `celery_unclassified_failure`** | **9.748854** |

The PostgreSQL pass retains the original expected migration fingerprint `184:b00f51e91c5b882cd84d3b2579d074ca`. Earlier passes are evidence from the running invocation; these components are stopped after cleanup and are not currently healthy services.

### Celery result

| Field | Retained value |
| --- | --- |
| Monotonic capture/command start | `184635.704491` seconds |
| Monotonic capture/command end | `184644.852156` seconds |
| Elapsed | **9.147665 seconds** |
| Celery child return code | **0** |
| Observed stdout / stderr bytes | **267 /0** |
| Output capture complete | **true** |
| Reviewed reply-output format valid | **false** |
| Conforming OK/pong replies parsed | **1** |
| Parsed default-role reply present | **false** |
| Parsed DVR-role reply present | **true** |
| Fixed failure classification | **`celery_unclassified_failure`** |
| Broker comparison | **unknown** (`broker_comparison_known=false`) |

All broker equality flags are false because comparison is **unknown**, not because an effective-setting mismatch was demonstrated. No authoritative worker snapshots were invented. No broker configuration changed.

The original readiness requirement of exactly two conforming default/DVR replies independently fails on the retained count/role evidence, regardless of the extra strict-format refusal. This is not a successful recovery hidden by a zero process return code. Conversely, absence of a parsed default `OK/pong` is not proof of no default response: a nonconforming/error reply, unexpected output or startup/control behavior cannot be distinguished from these sanitized records. The raw267-byte stdout was intentionally neither retained nor published, so its contents must not be reconstructed or guessed. There was no stderr to classify into the reviewed return69 error signatures.

The eight-second Celery option,40-second subprocess bound,90-second backend limit, original role requirements and all security/readiness gates remained unchanged. No retry or delay was added during execution.

## Final preservation and protection

Read-only final verification at **23:57:46 UTC** confirmed:

- All four IPTV containers stopped. Original container IDs, image identities, configuration fingerprints and restart counts were unchanged. Managed startup changed expected protected-service timestamps; gateway was not started.
- All29 unrelated container rows matched preflight exactly, including start timestamps/restart counts/health/status. Jellyfin remained running/healthy. Historical unrelated stopped containers stayed unchanged; no blanket claim that all unrelated services are healthy/running is made.
- Docker process identity, stopped-state complete network inventory and volume inventory matched preflight. No new network or volume appeared.
- Kernel nftables policy remained exact; public guard/grant assertions were withdrawn; guard transaction was revoked/unblocked; provider projection empty; private/runtime-anchor checks passed. Final VPN/namespace running acceptance was **not completed**, because the stack is stopped and no current grant is published.
- DW English ownership ledger was byte-identical to the checkpoint, with no pending ownership transaction. Existing Jellyfin LiveTV configuration hash matched its checkpoint. Neither configuration was modified.
- All67 current diagnostic file hashes matched. Current and historical receipts remained private and intact; new rollback copies verified. The current two diagnostic files were deliberately **not rolled back**.

New result receipt: `/root/dispatcharr-backend-diagnostics/1f131f6a3a1ee5d26654b9fbe7cc4065.result.json`, root:root0600,1497 bytes, SHA-256 **`c0ba54ea4ec5bc600d9669afb0425637e1aff96cc56d50635b9440fd69ccf895`**. Historical `3bb14e…` intent/result hashes were rechecked unchanged. There is one new intent/result pair and no second invocation.

## DW English availability and decision

**DW English is unavailable through the stopped IPTV stack.** Ownership/channel-stream identities remain preserved, but API registration verification, fresh export rebind, gateway serving acceptance and Jellyfin channel-discovery verification were not reached. Existing exports were not manually deleted or rewritten; the recovery manifest had no matching individual export members for an independent byte-comparison baseline, so current export-byte preservation/health is not claimed. No playback or external provider request was initiated.

**NO-GO for original-stack recovery completion.** The remaining blocker is a Celery inspection result that fails the original default/DVR reply requirement and cannot be fully classified from the reviewed sanitized output grammar. Preserve this evidence and current installed diagnostics for review. No worker absence, broker mismatch or startup-race root cause is asserted. No functional fix, file rollback, extra observation requiring application execution, additional start, provider activation or hardening work was attempted. Further production action requires separate authorization.
