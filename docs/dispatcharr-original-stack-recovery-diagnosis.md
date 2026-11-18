# Dispatcharr original-stack recovery diagnosis

**Exact failing subcheck remains unknown.** The retained evidence proves that the original `backend.py` exited 1 before channel registration, but the original code discarded its detailed error. No confirmed static configuration/security defect or reason for database restoration or container recreation was found.

**NO-GO for an immediate blind/uninstrumented retry. Conditional GO for one separately authorized, instrumented managed restoration attempt**, after the narrowly scoped diagnostic changes below are reviewed and fresh safety checks pass. No start is authorized or performed by this report. All hardening work remains suspended.

## Current state and preservation

Read-only observation: **2026-11-18T21:24:07Z**. Final preservation check: **2026-11-18T21:31:53Z**.

- All four IPTV containers remain **exited/stopped**. The stack unit remains failed after the prior restoration attempt; it was not reset or started. The guard unit remains active/exited and Docker remains running.
- AIO container `0d34537414caa0b788415ef7017e77687768fd9344353a34e882bd5a5c027a04` references immutable image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. Its expected recreation during the prior rollback is not new drift.
- All 33 container IDs/images/start times/restart counts/health-state/configuration fingerprints exactly match the final incident record. Jellyfin is healthy. All 29 unrelated containers match their baseline;16 are running, with zero unhealthy running containers. Existing stopped trial/retired containers are not newly classified as outages.
- All 67 original installed public files are regular single-link root:root 0644 files whose hashes and ownership/modes match both the checkpoint manifest and original rollback map. No native release target was reintroduced.
- The exact accepted nftables policy passes its pure semantic comparison. No nftables/VPN/DNS/guard command was applied.
- Public `guard.json` and `grant.json` are absent, as expected after failure cleanup. The guard transaction is `revoked`, `blocked=false`. Its stable public anchor matches the current host boot and directory device/inode.
- The root-private legacy ready marker matches the retained policy digest. The private guard directory remains0700; the public status directory remains0755. Retaining the legacy marker during stack-only stop is intentional `revoke(False)` behavior, not proof that relay authorization is active.
- Provider projection is empty, with private/public directories retaining 0700/0755. No provider authorization was read, published or regenerated. Active ownership state contains only `lock` and `owned.json`, without journal/commit/DELETE intent.
- AIO's network-namespace reference still names the preserved VPN-owner container. Network and volume inventory digests match the incident's protected stopped state. No unrelated endpoint or network change was observed.

Required private input metadata is intact: app.env, WireGuard and egress policy root:root0600; registration/relay files UID/GID1000, mode0400, regular and single-link. Values were not displayed. No application API request or application code execution inside a container occurred.

### Recovery availability

Verified Rivendell archive:

`/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`

Independently reverified Denethor copy:

`/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`

Both are **236147 bytes**, SHA-256 `ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`. Source remains root-owned 0600; independent archive/directory remain 0600/0700. The private manifest hash matches `f6dca113c1bf2d5433f6ab69aa74e12bdde8aee3425698366ce9935464e3df7e`. Only that manifest was read to compare the 67 public files; nothing was extracted to disk or restored. Historical checkpoints and private incident receipts remain intact. Selected incident receipt hashes also match their published commitments.

## Which original source was inspected

This diagnosis uses the **actually installed original files**, validated against the checkpoint, not the newer uninstalled native lifecycle in the current repository tree:

| Installed source | SHA-256 |
| --- | --- |
| `permanent-streaming/backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` |
| `permanent-streaming/lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` |
| `permanent-streaming/manifest.json` | `9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c` |

The original lifecycle waits for Compose health, then runs the backend gate as UID/GID1000 after sourcing its generated application environment. Registration, export binding verification and gateway-last follow only if the gate succeeds.

## Backend readiness inventory

Checks run sequentially; every exception at the script boundary becomes the same generic exit 1:

| Check | Exact rejection conditions / dependency |
| --- | --- |
| Pinned API source | Read 14 expected application files under `/app`; wrong SHA produces `pinned_API_source_changed`. Missing/unsafe-to-read files or invalid pin JSON can raise other exceptions. This is a source check, not an authenticated live API/Django health check. |
| PostgreSQL and migrations | Map existing POSTGRES_* values into libpq environment; read-only `psql` query must return exactly `184:b00f51e91c5b882cd84d3b2579d074ca`. Nonzero command status or different output produces `database_or_migrations_changed`. Existing subprocess 15s, statement 10s and lock 3s bounds remain relevant. |
| Redis | Import client, connect with configured authentication; 3s connect/read bounds, PING must succeed. `Redis_not_ready` covers a false ping; authentication/connection/timeout/import exceptions also become generic exit 1. |
| uWSGI witnesses | Scan `live:worker:*:heartbeat`; parse PID, require current `/proc/PID/comm == uwsgi`, age `0 <= age <30s`, TTL>0, and exactly two fresh workers. Invalid entries are skipped; excess count or anything other than two fails. Worker process creation alone is insufficient. |
| Celery | Run `celery -A dispatcharr inspect ping --timeout=8`, subprocess bound 40s. Return code must be0; parsed stdout must contain exactly two `OK pong` nodes, roles exactly `default` and `dvr`. Ready log lines alone are insufficient. |

AIO's Compose healthcheck separately requests its local HTTP root. An HTTP200 does not establish these database/Redis/witness/Celery conditions. The backend script does **not directly check guard/grant or namespace state**; those are established by earlier managed lifecycle gates and independently enforced by firewall/VPN controls. They must remain intact during any future attempt.

## Retained failure evidence

The systemd receipt shows original inputs, admission, managed guard apply, lifecycle preparation and prestart all passed. Admission took 15.002s with idle 94.548–97.885%, steal 0–0.05%, load1 0.19–0.23. This was not a resource-admission failure.

Docker exec events identify one backend invocation:

- Created: **2026-11-18T20:36:29.681656+00:00**.
- Exited: **2026-11-18T20:36:39.909418+00:00**, exit 1.
- Elapsed: **10.227761813s**.
- No register.py invocation followed. Ownership ledger remains unchanged and no registration journal exists.

Existing bounded AIO logs, including their Docker UTC timestamps, show:

| UTC | Event |
| --- | --- |
| 2026-11-18T20:36:10.156315914Z | no_pending_migrations |
| 2026-11-18T20:36:14.233786468Z | uWSGI_worker_spawn |
| 2026-11-18T20:36:14.233790712Z | uWSGI_worker_spawn |
| 2026-11-18T20:36:30.015064672Z | DVR_Celery_ready |
| 2026-11-18T20:36:31.869296682Z | default_Celery_ready |

The previous last100 lines omitted an earlier migration message; the bounded last300 and current persistent application log include **“No migrations to apply.”** Two uWSGI spawns and both Celery-ready messages are present. Fixed-pattern inspection found no PostgreSQL authentication, Redis authentication, permission-denied, traceback or OOM evidence in these bounded logs. These are negative observations within the inspected window, not proof that the corresponding backend predicate passed.

Both Celery-ready messages follow backend invocation start. A startup-ordering race is therefore **plausible**, but not confirmed: neither the instant `inspect ping` was invoked nor its actual replies/return code were retained. A 10.228s total is compatible with more than one bounded dependency path and cannot identify the subcheck. Do not fix this by adding an unexplained delay, increasing timeouts, weakening freshness or assuming Celery was at fault.

### Why the exact error cannot be recovered from current evidence

There are two independent information losses:

1. `backend.py` catches every exception and exits with only `Backend readiness refused; values withheld.`, discarding the specific condition/exception classification.
2. The original lifecycle uses `subprocess.run(..., capture_output=True)` and raises only `scoped_command_failed` on nonzero status. The captured backend stdout/stderr is not retained or forwarded.

Docker logs do not contain exec-stream output by default, and the retained exec events contain timing/exit status rather than stderr. Journal and receipt inspection establishes the boundary, not the lost condition. Live PostgreSQL, Redis keys/TTL/freshness and exact Celery replies cannot be rechecked while those processes are stopped under this authorization.

Read-only Docker archive metadata queries were also inconclusive. The versioned API inspected the same stopped container successfully, but archive HEAD/GET returned 404 for `/app`, the generated profile and even `/`, `/data` and the known host-bound `/opt/permanent/backend.py`. This interface does **not provide usable stopped-filesystem evidence here**; it does not demonstrate that application files vanished or justify recreating the container. No archive contents were extracted or application code executed to work around it. The required host-bound files remain hash-verified.

## Recovery prerequisites: expected versus defective

| Observation | Assessment |
| --- | --- |
| Four containers stopped; live VPN/backend unavailable | Expected result of scoped failure cleanup; not evidence of corrupted data. |
| Public guard/grant absent; transaction revoked/unblocked | Expected fail-closed state. Do not republish or clear manually. |
| Legacy root-private marker retained and policy matches | Expected stack-stop behavior while the guard service remains active. Fresh managed apply withdraws/replaces it before startup. |
| `/run/dispatcharr-permanent` absent | Expected systemd RuntimeDirectory cleanup. The unit recreates the 0700 parent; existing lifecycle prepares the 1000:1000 relay child before container startup. Do not create it simply to make stopped-state reads succeed. |
| Current anchor matches boot/device/inode | No stale/replaced public anchor was found. |
| Preserved VPN-owner ID and AIO namespace reference agree | No namespace-reference defect found. Running kernel namespace/grant checks must still occur during a future managed start. |
| Original 67 sources and required private-file metadata match | No static installed-file drift or permission change was found. |
| Current ownership state has no pending mutation | No transaction conflict blocking a controlled attempt was found. |
| Failed stack unit | Preserve failure evidence. The existing managed start is the supported future entrypoint; no reset-failed, marker clearing or direct container start is warranted by this diagnosis. |

Network digest `323f303c08b51c7ca59bd25a054ca89276b5e6bd182c570000bdaa1e14382c01` is the previously reconciled **stopped-state** digest; it differs from the running inventory because protected VPN endpoint membership/IPAM occupancy changed during shutdown. Configuration, IDs and unrelated memberships are unchanged. That normal distinction is not a reason to create a network or change policy.

No confirmed static safety/rollback condition currently requires database restoration, image replacement, container recreation, guard changes or firewall/VPN/DNS changes. This does not guarantee application readiness will pass on another start.

## Minimum instrumentation for one future attempt

**Proposal only; not implemented or installed.** Prepare a small diagnostic-only revision based on the installed original 227122d files above, not the current repository's uninstalled native lifecycle.

1. In the original `backend.py`, emit bounded fixed-enum start/completion/failure records for API pins, PostgreSQL/migrations, Redis, fresh uWSGI witnesses and Celery. Preserve the exact checks, order, exit behavior, timeouts, freshness limits and commands. Log only stage, elapsed time, fixed condition code, return code, counts and role-presence booleans; optional migration count/fingerprint is already non-secret. Known ValueError messages can map to fixed public codes. Map authentication/timeout/permission/missing-file errors to fixed classes; never log exception text, environment values, URLs or raw replies. Unexpected errors remain nonzero/fail-closed with a fixed `unclassified` code.
2. In the original `lifecycle.py`, retain/forward **only those validated, size-bounded records from the same backend invocation** into a protected receipt and/or the unit journal. Keep generic nonzero failure and existing cleanup. Do not print captured subprocess stdout/stderr wholesale. Absence of an initial diagnostic record must distinguish shell/profile/Python-launch failure from an entered backend check. Do not rerun the failed probe after cleanup and mistake a later observation for the original failure.
3. Review the changed backend/lifecycle hashes and their exact original permanent manifest entries as one matched, diagnostic-only delta. Update relevant inventory commitments deliberately; preserve every unrelated hash. Use focused offline failure/redaction checks before requesting installation/start authorization. No image build, Compose/mount/privilege change, new listener/daemon, new probe framework, source import or worker restart is needed.

This is the minimum reliable change because forwarding the existing generic stderr alone would still conceal the subcheck. No instrumentation, source patch, manifest regeneration or runtime-state write was made during this task.

## Proposed controlled restoration procedure

After separate approval for that reviewed log-only delta and **one** managed attempt:

1. Reconfirm exclusive administration, checkpoint/hash availability, all original baseline files plus the explicitly approved diagnostic delta, current guard/kernel/anchor/ownership state, unrelated fingerprints and fresh resource capacity. Keep hardening suspended.
2. Install only the approved diagnostic-only backend/lifecycle/manifest delta with the original ownership/modes. Preserve the untouched original files for removal of instrumentation. No container recreation, systemd dependency change or database restore is proposed.
3. Issue exactly once, through the original unit:

```sh
# FUTURE AUTHORIZATION ONLY — NOT EXECUTED IN THIS DIAGNOSIS
sudo systemctl start dispatcharr-stack.service
```

4. Monitor that same job and its sanitized stage records. Let unchanged admission, guard apply, VPN-owner verification/grant, backend gate, owned registration and gateway-last order operate normally. No direct container start, stale marker reuse, relaxed threshold or automatic retry.
5. On success, verify the original four-service stack, database/Redis, two fresh witnesses, both Celery roles, guard/grant/namespace, exports/ownership and Jellyfin/unrelated preservation. No playback/provider request unless separately authorized. On failure, retain the precise failing record and allow existing scoped cleanup; stop after that single attempt.

**Conditional GO for this separately reviewed/authorized instrumented attempt; NO-GO for a blind retry now.** The GO concerns a bounded fail-closed diagnostic procedure, not a prediction of availability. No evidence supports resetting Redis/PostgreSQL, restoring the database, recreating containers or changing security policy.

## Deliverable and stop

Sanitized fresh state, original 67 hashes, log classifications, timestamps, read-only helper hashes, checkpoint verification and final preservation are in `configs/dispatcharr-iptv/original-stack-recovery-diagnosis-results.json`. Private original logs/receipts remain in the existing root-private incident directory. Archive bytes, credentials, raw logs and provider URLs are excluded.

All 33 container fingerprints remained unchanged at the end of diagnosis. **Zero lifecycle operations, container application executions, application API calls, provider requests, restores or playback occurred.** The four IPTV containers remain stopped. Stop after publication and await separate restoration authorization.
