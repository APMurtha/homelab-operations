# Dispatcharr PR 27 production preflight

**NO-GO for installation or a managed start at this checkpoint.** Rivendell matches the expected original-stack code and stopped topology. One interactive login was present, unrelated workloads have changed since November 19, and the independent recovery copy still needs a fresh read. The authorization for this inspection covers planning only.

Observed on Rivendell from **2026-11-23 03:30:21 to 03:31:47 UTC** through Bag-End’s pinned SSH connection. The host, address and login were checked. The reviewed candidate is `221245c6982e45fbbfde13033e56d31042404834`. Only sanitized findings are included. [Candidate and independent staging results](https://github.com/APMurtha/homelab-operations/pull/27#issuecomment-7090740603) · [November 19 reference receipt](../configs/dispatcharr-iptv/structured-celery-restoration-results.json)

## Current observations

| Container | Current state | Restart count | Last finish, UTC |
| --- | --- | ---: | --- |
| dispatcharr | Exited | 0 | Nov 19 17:31:24 |
| rivendell-iptv-relay | Exited | 0 | Nov 19 17:31:21 |
| rivendell-iptv-vpn | Exited | 0 | Nov 19 17:31:24 |
| rivendell-iptv-gateway | Exited | 0 | Nov 18 20:25:17 |
| jellyfin | Running, healthy | 0 | Nov 19 17:23:34 |

All five container IDs and image IDs matched the November 19 reference. The exited IPTV containers retain Docker’s last unhealthy label. The installed stopped-workload verifier passed its image, project membership and topology checks. The AIO image was present locally at the reviewed digest `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.

**Other services.** Docker was active. The stack was the only failed systemd unit (exit-code), the egress guard was active/exited successfully, and neither needed a daemon reload. Of 30 containers outside the IPTV project, including Jellyfin, 16 were running (five healthy and eleven without a health status) and 14 were exited (twelve without a health status, one last unhealthy and one last starting). Relative to November 19, one container was added and none disappeared. All 29 comparable status and health values matched. Sixteen start times, five container IDs, one image ID and one restart count differed. These observations establish drift, not its cause. One interactive login was visible; exclusive administration was unconfirmed.

**Capacity.** The pinned, read-only admission program passed in 15.002 seconds. Three consecutive five-second samples showed idle 96.477%, 94.869%, 96.175%, steal 0%, 0%, 0.05%, and one-minute load 0.52, 0.48, 0.44. The installed limits are four CPUs, idle ≥50%, steal ≤10%, load <4. Available memory was 12,736,086,016 bytes and Docker filesystem availability was 39,386,554,368 bytes. Admission must run again in the change window.

**Persistent state and recovery.** The original data bind was present and writable in the stopped AIO configuration. One cluster root contained a numeric PostgreSQL version marker, a base directory and a control file. This was a filesystem check. The ownership directory contained only its lock and ledger; the ledger was UID/GID 1000:1000, mode 0600, and matched the ledger member in the checkpoint archive byte-for-byte. The Rivendell archive was root:root 0600 under a 0700 directory, 236,147 bytes, with 147 archive members. Its SHA-256 was `ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`. This matches the independently recorded Denethor digest. The documented independent archive was unavailable at its recorded path on Rivendell and Bag-End had no verified route to read it during this check. Fresh independent-copy verification remains open. Nothing was extracted or backed up.

**Guard and authorization.** The live nftables table matched the reviewed semantic contract against the current private policy. Public guard and grant projections were empty, owner intent absent, private transaction revoked and unblocked, and the boot/device/inode anchor matched. The legacy private ready marker still contained the exact policy digest. The installed stop path calls `revoke(False)`, which preserves this marker, and the next start removes it before admission. Neither provider runtime directory existed, so no provider authorization was projected. The private policy and VPN files were root:root 0600 under a 0700 directory.

**Receipts.** All six files recorded at the first November 19 cleanup matched their published hashes. There are now four matched intent/result pairs, eight regular root:root 0600 single-link files under root:root 0700. The additional result at **2026-11-19 17:31:20 UTC** records `backend_stage_failed` and `celery_unclassified_failure`. This explains why the original cleanup snapshot cannot be reused as a current baseline. It does not identify the discarded reply or authorize another attempt.

## Installed pair and lifecycle

| Artifact | Installed SHA-256 | Reviewed PR 27 SHA-256 |
| --- | --- | --- |
| backend.py | `466b06a23af779d0093d2325d6dce3257a354e4d8899658fb849713e2b1a3065` | `040c28facf839b7afe5b6a37021dde195eaea04e43e71ce557784843542e17af` |
| manifest.json | `8c8ea65df72c6ce18238faeb7262c6946b821ad711bdbf9b06174c10b2dc2a5f` | `218ca99c53d08ea9ce355dcb3d1fa14eb811a50c33c66a1ebfb5f72b54b82475` |
| lifecycle.py | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` | Same bytes |

All three were regular root:root 0644 single-link files under `/docker/dispatcharr-iptv/permanent-streaming`. All 45 entries in the installed manifest matched the installed files. Both installed targets matched the November 19 pair and all 65 unchanged targets matched the candidate inventory. All 67 were root-owned regular files without group/other write permission. The installed input verifier passed, including private configuration shape and permissions. The stopped AIO has the host directory bound read-only at `/opt/permanent`. Its future producer uses that directory; the host lifecycle imports the receipt reader from the same host backend. The older strict reader cannot decode the candidate’s new failure field. A mixed pair is an abort condition.

## Managed entry point and effects

The loaded entry point is **`systemctl start --no-block dispatcharr-stack.service`**. The loaded unit has only the resource-admission and permanent-streaming drop-ins, restart policy `no`, start timeout nine minutes and stop timeout four minutes. The effective command sequence matched the installed historical unit, including its cleanup steps.

1. Pre-start clears public assertions and the legacy ready marker, verifies inputs, runs admission, applies the kernel guard, prepares runtime state and owner intent, then verifies pre-start protection.
2. The lifecycle starts the existing VPN, publishes the namespace-bound grant, starts AIO and relay, and performs the managed backend check. Existing Compose flags prohibit builds, pulls and recreation. This step can establish VPN connectivity, bring up the database, broker and workers, run application startup, and write normal service data. The backend uses one Celery inspection and creates a new private intent/result pair. A return of zero from the nonblocking systemctl request means only that the job was submitted.
3. After backend acceptance, registration can mutate owned records and exports. The lifecycle verifies the binding, starts the gateway last and runs the installed end checks, including health, VPN route/killswitch, namespace grant, resolver, relay generation and binding. The candidate does not enable native provider authorization. Any provider or playback test needs its own scope.
4. Failure before backend acceptance prevents downstream registration and gateway startup. The unit’s post-stop path withdraws public assertions, revokes the grant, stops only gateway, relay, AIO and VPN, and verifies revocation. Later-stage failures may already have changed owned records. The separate `rollback-integration` action can delete owned integration records; it is outside a two-file rollback.

## Conditional deployment and rollback plan

1. **Authorize and reconcile.** Approve this exact revision, a two-file installation and matched rollback, one managed start, scoped cleanup and an exclusive window. Reconcile the additional November 19 result, the interactive login and unrelated inventory drift with the owner. Establish a new private before-state for comparison. Recheck stopped topology, protected state, inactive provider projection, receipt/ledger state, capacity, and both recovery archives immediately before writing. Stop on unresolved drift, a pending ownership transaction, insufficient capacity, or an inaccessible or mismatched recovery copy.
2. **Preserve the actual pair first.** Only in the authorized window, create a fresh root:root 0700 rollback directory under a trusted root-private parent, outside the repository and service tree. Open the installed directory and both regular files without following links. Record directory/file identities, sizes, original owner/group/mode and the two installed hashes above. Copy exact bytes into exclusive new root:root 0600 files, fsync files and directory, reread and hash the copies, and recheck source/path identities and digests. The service directory is root:root 0755, but its `/docker` ancestor is UID 1000, GID 988, mode 0770. Hold directory descriptors, exclude concurrent renames and abort on identity change. Do not use the older rollback hashes in the candidate inventory or restore the full archive for a two-file change.
3. **Install and verify while stopped.** Validate the checkout and manifest offline. Under the exclusive no-start window, stage both candidate files in the pinned destination directory using exclusive new files, root:root 0644, hash and fsync them, then rename backend followed by manifest and fsync the directory. The two renames are individually atomic; the window must span both. If interrupted, reconcile both live hashes before doing anything else. Verify the candidate pair, unchanged lifecycle, 65 other targets and read-only bind. Run the installed input verifier. A partial pair, failed verification, unexpected start or conflicting operation is a hard stop.
4. **One attempt.** Record the pre-start unit state and private receipt set. Submit the managed start once, follow the same invocation to terminal state and compare the new receipt pair. Require all upstream stages plus valid default and DVR pongs, successful registration/export binding, gateway-last and final running checks. An invalid response, generic refusal, missing receipt or incomplete acceptance is a failed attempt. Do not issue an individual service start, manual ping, or retry.
5. **Abort or roll back.** On failure observe scoped cleanup, verify four stopped containers, empty public projections, revoked/unblocked transaction, intact kernel policy, preserved receipts and ledger, and unchanged unrelated inventory against the window baseline. On incomplete cleanup, ambiguous unit outcome or pending registration, stop and reconcile under explicit authority. If rollback was authorized and the stack is quiescent, restore the verified private pair together by the same staged-rename procedure, reset the installation modes to 0644, fsync, and verify both original hashes, unchanged lifecycle, full closure and input verifier. Restoring code does not reverse application data mutations. Leave the stack stopped and preserve all receipts; another start needs a separate decision.

### Verification commands for the change window

On the reviewed checkout, run `git rev-parse HEAD` and `python3 -B configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py`. On the respective archive hosts, run `sha256sum -- "$archive"` with the selected source or independent archive path and confirm the expected digest above. Confirm the independent file resides on the expected separate filesystem with `findmnt -T "$archive"`. Do not recopy a missing file as a substitute for checking the independent copy.

On Rivendell, the following read-only commands distinguish the installed, candidate and restored states. Compare digests and unit results to the applicable phase above. Inspect only structured, sanitized fields from the new receipt. Keep raw logs, private configuration and environment values off the PR.

```sh
cd /docker/dispatcharr-iptv/permanent-streaming
stat -c '%n %u:%g %a %h' backend.py manifest.json lifecycle.py
sha256sum -- backend.py manifest.json lifecycle.py
sudo -n /usr/bin/python3 -B verify.py inputs
sudo -n /usr/bin/python3 -B ../boot-admission-phase6b3k/admit.py
systemctl show dispatcharr-stack.service -p ActiveState -p SubState -p Result -p InvocationID
docker --host unix:///var/run/docker.sock inspect --format '{{.Name}} {{.State.Status}} {{.RestartCount}}' \
  dispatcharr rivendell-iptv-relay rivendell-iptv-vpn rivendell-iptv-gateway jellyfin
```

Use the pinned read-only guard table comparison on the host and compare only its verdict. The managed unit itself owns the pre-start and running verifiers. Production work in this review ended at inspection.
