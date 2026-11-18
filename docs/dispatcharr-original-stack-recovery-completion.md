# Original Dispatcharr IPTV recovery attempt

**FAIL: restoration reached backend readiness and stopped at `celery_command_failed`. One managed start was issued; no retry occurred.** Managed cleanup left all four original IPTV containers stopped, kernel protection intact, public guard/grant assertions withdrawn and provider authorization revoked. Jellyfin remains healthy. Original-stack availability is **not restored**; hardening remains suspended.

## Minimal diagnostic correction

The authorized delta moves receipts from `/docker/dispatcharr-iptv/private/backend-diagnostics` to `/root/dispatcharr-backend-diagnostics`. Only the candidate lifecycle's receipt-path handling changed: validate the actual receipt parent and every ancestor, then require root:root 0700 on the parent and receipt directory. Root-only writer checks, no-follow/exclusive opens, held-directory identity checks, root:root 0600 single-link receipts, fsync, bounded capture and strict redacted record validation remain in place. `/docker` ownership/mode was not altered.

The candidate is based on `50bdb437b57d84b9f74237db04d862c12fa24424`, with this task's explicit authorization for the path correction. The original byte-for-byte rollback copies remain unchanged. `backend.py` is unchanged from that approved diagnostic candidate. Only the candidate lifecycle hash and matched manifest/inventory were revised; the review patch, verifier, README and permission fixture were updated consistently. No application source, image pin, Compose file, unit, admission threshold, timeout, guard, VPN or gateway policy changed.

Offline results: **152 unit tests PASS** (69 diagnostics, 28 admission, 12 persistence, 26 rollback and 17 security-contract tests), plus **16 actual filesystem checks PASS** in a disposable user/network namespace/chroot with UID0 and UID1000. The existing diagnostic tests retain the original readiness-function AST projection and lifecycle prepare/start/stop/rollback ordering. Filesystem checks include private receipt denial for UID1000, independent root-private receipt success with a UID1000:GID988 0770 application ancestor, unsafe receipt-ancestor refusal, wrong ownership/modes, symlink/hardlink/collision refusal, no-follow behavior and replaced-directory rejection. The namespace runner initially could not use `newuidmap` inside the Codex sandbox; the identical isolated fixture passed outside that sandbox. No production fixture or Docker test container was used.

`verify_candidate.py` passes original hash checks and complete 67-target manifest closure. These offline results do not claim the production application is healthy.

## Fresh preflight

At **2026-11-18 22:29:33 UTC**, Andrew's selected NEST `andrew-media` / `media` SSH context verified hostname Rivendell and login `murth`, UID1000, followed by authorized root operations. The owner's exclusive-administration confirmation remained applicable to this restoration window.

- All **67 original installed public files**, including owner/mode checks, matched the original baseline. All **33** container fingerprints matched the prior incident state; the four IPTV containers were identifiable and stopped, and Jellyfin was healthy.
- The original AIO image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` was verified in the local image store.
- Exact nftables semantic verification passed. Guard transaction was revoked/unblocked; public guard/grant files were absent. Provider projection was empty, runtime anchor checks passed and private configuration permissions matched.
- Ownership state contained only `lock` and `owned.json`; its content hash matched the checkpoint. No pending/uncertain ownership transaction was found. Original persistent data mount and database-cluster marker were available.
- The source recovery archive and independent Denethor copy both matched SHA-256 `ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`. The source manifest and original public-file/ownership records were checked without extraction or restoration. The independent archive remains mode0600 under a 0700 directory.
- Available RAM: **4,630,089,728 bytes**; Docker filesystem available space: **7,685,038,080 bytes**. Read-only installed admission passed in **15.003 seconds**: idle 94.702–97.738%, steal 0–0.05%, one-minute load 0.04–0.05. Installed thresholds and sampling were preserved.

Recovery archives remain at `/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` on Rivendell and `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz` on Denethor. No database reset, restore or replacement backup was performed.

## Installation and exact hashes

At **22:30:14 UTC**, exactly these three targets under `/docker/dispatcharr-iptv/permanent-streaming/` were installed root:root 0644 and verified:

| Installed file | SHA-256 |
| --- | --- |
| `backend.py` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` |
| `lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` |
| `manifest.json` | `07faa8cce4c643c0a580787b2514c955ddbc4cd0cbff77b61209de9dd97815a4` |

All **64 unchanged targets** matched; all 67 matched the resulting candidate inventory. Exact original rollback bytes were preserved privately under `/root/dispatcharr-emergency-restoration-20261118T222912Z/original/`, in addition to the historical archive and repository originals. The root-private receipt directory was created and validated. The installed original `verify.py inputs` passed. No native40 drop-in or 80-target transition was installed; the original four-service configuration and image identities were retained.

## Single managed start and diagnostics

At **22:30:40 UTC**, one `systemctl start --no-block dispatcharr-stack.service` request was submitted. The nonblocking flag only decoupled SSH from the normal systemd-managed operation; it did not bypass any lifecycle gate. Return0 accepted the request, and was not treated as successful recovery. Subsequent operations only inspected the same invocation `772dd60f81324e03bda94dd7a9dee2b8`.

Actual managed resource admission passed in **15.006 seconds**, idle 94.304–96.623%, steal 0–0.05%, load0.38–0.45. The existing lifecycle applied the guard, verified/started the VPN owner and started AIO/relay. The first status at22:31:10 showed VPN and relay healthy, AIO still starting and gateway stopped.

The validated receipt from backend invocation **`3bb14e388660a22ed7f62a9aacb795ea`** records:

| Stage | Outcome | Completion elapsed seconds |
| --- | --- | --- |
| 14 pinned application sources | PASS | 0.018688 |
| PostgreSQL/migration fingerprint | PASS, return0 | 0.283854 |
| Authenticated Redis | PASS | 0.708244 |
| uWSGI Redis-backed heartbeat witnesses | PASS, exactly2 | 0.710157 |
| Celery default/DVR control responses | **FAIL, `celery_command_failed`, return69; zero parsed replies; both role-presence flags false** | **9.654352** |

The PostgreSQL pass establishes the unchanged original predicate `184:b00f51e91c5b882cd84d3b2579d074ca`. The failing command was the existing `celery -A dispatcharr inspect ping --timeout=8` under the original environment and 40-second subprocess bound. The backend itself exited1. No readiness predicate, deadline or retry behavior was changed.

This is direct evidence of the original failing **subcheck**. It does not establish why the Celery control command returned69, or prove that worker processes were absent. Raw command output, environment and exception text were deliberately not retained by the approved diagnostic projection. PostgreSQL/Redis/uWSGI success is point-in-time evidence from that invocation, not current running health after cleanup.

The unit reached failed state at **22:31:43 UTC**; status was retained at22:31:50. Registration/export rebind and gateway-last startup were **not reached**. No downstream application/Jellyfin discovery acceptance is claimed. No second start, individual-container start, recreation or recovery workaround was attempted.

## Final protected state

Final read-only verification at **22:32:38 UTC** established:

- All four IPTV containers stopped. Original IDs/images/configuration fingerprints/restart counts remained unchanged; their managed start timestamps changed as expected for the three services reached. Gateway was never started.
- All **29 unrelated** container rows matched exactly, including IDs, images, configuration, start timestamps, restart counts and health/status. Historical exited containers remain historical; this does not claim every unrelated container is healthy/running. Jellyfin remained running/healthy.
- Docker process identity, stopped-state full network inventory and volume inventory matched preflight. Exact kernel nftables protection remained intact; public guard/grant assertions were withdrawn, transaction revoked/unblocked and provider projection empty. Private permissions and anchors remained valid.
- DW English ownership ledger was byte-identical to the checkpoint, with no pending transaction. Existing Jellyfin LiveTV configuration's checkpoint hash matched. Neither configuration was changed by this task.
- Export rebind was not reached; no current export/serving-health claim is made. The recovery manifest comparison found no matching individual export file members to use as a hash baseline, so export-byte preservation is **not independently established** here. No export deletion or manual rewrite was performed.
- Installed diagnostic hashes and all64 unchanged file hashes still matched. The receipt directory is root:root0700; its single invocation intent/result files are root:root0600, regular, single-link and retained. No historical receipt was cleared.

Private diagnostic result: `/root/dispatcharr-backend-diagnostics/3bb14e388660a22ed7f62a9aacb795ea.result.json`, SHA-256 `5f5efba1fc7374931345410e247b7359df95ee319b1bcffe29535946b7e9fa51` (1166 bytes). Administrative evidence is retained under `/root/dispatcharr-emergency-restoration-20261118T222912Z`. [Sanitized evidence](../configs/dispatcharr-iptv/original-stack-recovery-completion-results.json) contains the fixed-schema records and preservation fingerprints, without credentials, provider URLs, database contents or raw logs.

## Changed candidate artifacts

These hashes describe the exact reviewed correction files; only the three runtime targets above were installed. All original rollback source bytes, backend diagnostic source bytes and unrelated files were preserved.

| Repository file | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/original-backend-diagnostics/README.md` | `07795a81883f45f34313aa1b9f0e18f55dfa85bf98c147db1d1bd2551b68093f` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate-inventory.json` | `524cc9aa8c34dc2215745541f0c6f0c5c767a81123561bc1021f737c0383efb7` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate.patch` | `8a9215ba68dc0fd66475e67fb7313cfc0af4d502fddf3e49143aa2bef51abbe4` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/manifest.json` | `07faa8cce4c643c0a580787b2514c955ddbc4cd0cbff77b61209de9dd97815a4` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/permission_fixture.py` | `35d658334a2f63594171239d0597fc1a02a287a19c497c9c39eebde6fcc59773` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py` | `e6448a19c69e98602a5bdd3fc0a15ab39102508530c72b559f9c2078e7d36f81` |

## Decision

**NO-GO for recovery completion.** The receipt-path incompatibility is resolved and diagnostics now identify the failing Celery command. Availability remains down, with the original stack safely stopped and protected. Further work requires separately authorized bounded diagnosis of Celery startup/control/broker behavior using retained evidence; the current record does not justify a worker, broker, timeout or security change. Any future start needs separate authorization. Do not resume hardening, activate providers or play media.
