# Dispatcharr production hardening completion

**Outcome: FAIL / NO-GO. Recovery checkpoint and independent copy are verified. The candidate failed its installed-input gate. Original configuration was restored, but the single managed restoration start failed at backend readiness. All four IPTV containers are now stopped with the exact kernel guard intact.**

**DW English is unavailable.** Jellyfin itself remains healthy and unchanged. This is not a successful runtime rollback or a completed hardening deployment. No further start, candidate fix, provider activation or playback was attempted.

## Scope and identities

- Approved production plan: `92c802a69d6e9df2744797116dc096666dec6d69`.
- Starting failed-preflight evidence: `a4298993e2db3e7150c73762b2e159aeac72e619`.
- Accepted isolated runtime evidence: `d5225934a6d6ff8f919e01aae4219d36dba635d6`.
- Accepted hardened image, preserved but **never created/started in production**: `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439`.
- Final installed known-good AIO image: `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
- Selected access: NEST Andrew / andrew-media / media; authenticated Rivendell as murth UID 1000, authorized root lifecycle. Owner's exclusive-administration confirmation carried forward into this coordinated workflow.

One controlled transition was attempted: **one managed stop, 80 targets installed, zero hardened-AIO recreations/starts**. There was **one approved rollback AIO recreation and one managed restoration start**, with its automatic scoped cleanup. No second deployment attempt or additional restoration start occurred. No image build/pull/retag, database restore/reset, real-provider authorization/request, playback or unrelated service modification was performed.

## Complete current recovery checkpoint

Rivendell source:

`/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`

Independent Denethor copy:

`/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`

| Verification | Result |
| --- | --- |
| Capture completed | 2026-11-18T20:17:14Z |
| Archive bytes | 236147 |
| Archive SHA-256 | `ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7` |
| Private manifest SHA-256 | `f6dca113c1bf2d5433f6ab69aa74e12bdde8aee3425698366ce9935464e3df7e` |
| Regular-file members | 131 |
| Source protection | root:root, archive 0600, containing directory 0700 |
| Independent protection | owner UID 1000, archive 0600, directory 0700 |
| Source versus independent archive | Exact size and SHA-256 match; rechecked after the attempt |
| Every member | Hash/size/UID/GID/mode verified; directories and the reviewed link checked separately |
| Historical checkpoints | Preserved; new unique directory used |

The independent destination is on Denethor's existing `/dev/nvme1n1p1` Btrfs mount at `/mnt/data`, separate from Rivendell. Protection uses restrictive filesystem permissions; no additional archive-encryption claim is made.

The approved existing online recovery method was reused: PostgreSQL 17 `pg_dump --format=custom --compress=6 --no-password --lock-wait-timeout=5s`, read-only bounded libpq environment, and `pg_dumpall --roles-only --no-role-passwords --no-password`. No password entered argv or output. Matching PostgreSQL 17 `pg_restore --list` and complete `--file=/dev/null` payload decoding passed without restoring or connecting to another database.

Coverage includes the current database; roles without password hashes; required JWT/logos/uploads/scripts/plugins/M3U/EPG assets and current ownership/transaction state; all 67 public files and the four-service Compose/systemd/security contracts; scoped private app/registration/relay/WireGuard configuration; generated runtime environment; selected PostgreSQL configuration; all four container configurations/images/mounts/networks; exact nftables policy; scoped Jellyfin LiveTV configuration reference; original installation mappings and restoration instructions. Credentials/private configuration/database contents remain exclusively inside protected recovery storage and private receipts, excluded from Git/chat.

Raw live PGDATA, Redis/session runtime, disposable caches/logs and old native ZIPs were excluded. The registration state lock was held, and selected persistent-file hashes/metadata and production container configurations were unchanged across capture. This proves an MVCC-consistent database dump plus stable selected filesystem assets; it is **not an atomic snapshot of every live database/filesystem event**. No full restore/rehearsal occurred. The checkpoint remains the verified pre-transition baseline; old opaque bindings are historical and must be regenerated through the managed registrar during any later authorized recovery.

An initial capture refused the historical `retired-exports/current` symlink before a dump/archive existed. Inspection established its exact relative target hash and containment within the same historical directory. The complete capture preserved that one explicitly reviewed link as link metadata without following it; all other unexpected links still refused. No required live asset was skipped. The refusal receipt remains intact.

## Fresh preflight

The original stack and Jellyfin were healthy. All33 container configuration/start/restart/health fingerprints matched the accepted prior baseline. Both immutable images were present. All67 current installed public hashes/root ownership/modes matched the approved old release; all 13 proposed introduced targets were initially absent. Proposal artifacts and 80 target-source hashes matched the approved review without regeneration.

All 18 accepted image source/readiness hashes were freshly verified by the reviewed read-only image exporter, which exited successfully. Original corrected-build provenance and private receipt hashes were reconciled. No build, temporary test container, source substitution or repeated image scan was used.

Read-only application checks through the existing in-container API established:

- Owned DW English channel/stream 3/3, hidden channel 9001; ledger and authoritative detail responses match, no shared reference or duplicate, no pending journal/commit/rollback receipt.
- Default Group 2; unique locked streamcopy/MPEG-TS profile 1.
- Exact ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e` and Jellyfin peer 172.20.0.2.
- PostgreSQL migration count 184/fingerprint `b00f51e91c5b882cd84d3b2579d074ca`; actual Django MigrationExecutor reported **zero pending migrations**, with the supported plugin-autodiscovery opt-out for that read-only management query only.
- Authenticated Redis and existing backend gate passed; two fresh uWSGI witnesses and default/DVR responses passed before stopping.
- No live-channel Redis keys, queued Celery/DVR jobs, recordings, FFmpeg/FFprobe processes, playing Jellyfin sessions or timers.
- Jellyfin channel 9001 remained discoverable; canonical LiveTV digest `133f81220c59c293a50116b5f9d20f8ecd422d0e9b46b0eeab1a63dbe9a09f0b` matched. Its placeholder guide was not represented as broadcaster EPG.
- Existing running/security verifier passed: exact nftables, VPN namespace/tun0, DNS/IPv6, grant and mount/resource/source contracts.

Active/reserved/scheduled control reads found zero jobs on both default and DVR workers. CLI startup text preceded the JSON response; the safe parser required exactly those two nodes and list schemas rather than treating the banner as an application failure. The original unsuccessful read-only parser receipt was retained.

Existing production plugin/version maintenance remains enabled, with one plugin-repository record. There is one STD account and no EPG sources. No native provider account/credential was created. These existing maintenance paths are separate from native provider authorization and may make non-provider maintenance requests; no schedule was changed or maintenance task triggered for this workflow. No claim is made that every application background HTTP path uses the native provider-policy reader.

## Timeline

| UTC | Event |
| --- | --- |
| 2026-11-18T20:17:14Z | Current online checkpoint complete; source archive verified |
| 2026-11-18T20:14:46Z | Initial application/API state captured (first live PASS20:14:46) |
| 2026-11-18T20:25:16Z | Repeated fresh application, migration, idle and configuration checks PASS |
| 2026-11-18T20:25:16Z | Sole old-unit stop issued |
| 2026-11-18T20:30:37Z | Successful stop reconciled; exact kernel protection checked |
| 2026-11-18T20:30:38Z | 80 targets installed and hash/mode verified; native input gate then refuses |
| 2026-11-18T20:33:32Z | Conflict-checked rollback safety PASS |
| 2026-11-18T20:34:56Z | Original 67 restored, introduced13 archived; only old AIO recreated stopped |
| 2026-11-18T20:35:39Z | Sole managed restoration start issued |
| 2026-11-18T20:36:43Z | Restoration command exits1 after managed cleanup |
| 2026-11-18T20:38:44Z | Original configuration verified; four IPTV services stopped/protected; unrelated services unchanged |

The initial stop completed successfully. Two administrative helper assumptions delayed reconciliation before installation: stack stop deliberately calls `revoke(False)` and retains the root-private legacy marker while removing public assertions; Docker 29 updates protected-network endpoint membership **and** IPAM occupancy counters during stop. The helper initially asserted stricter/different representations. Pinned source, revoked/unblocked transaction, private policy digest and exact kernel semantics were verified. Reconstructing only the preserved VPN endpoint and its one-address occupancy in memory reproduced the exact original full network digest `51839910ef1955c6811a500972dea224445df3b93c5d4dc9a5afaafe49278192`. No network policy was changed, no guard record was fabricated, and the same stopped transaction continued without another stop/start. These helper pauses did not relax the protected verifier.

A local transport encoding error before remote execution and a host-loopback admin request to the deliberately isolated backend were also reconciled before capture; the established in-container API path was then used. Those were not production deployment retries. All private refusal/intent receipts are retained.

## Confirmed candidate defect

All 80 mapped targets were installed and individually verified, including the systemd copy of 40-native-hardening.conf. Native `verify.py inputs --native` then refused with:

```text
FileNotFoundError:
/docker/dispatcharr-iptv/permanent-streaming/40-native-hardening.conf
```

The candidate permanent manifest contains `40-native-hardening.conf`, and `verify.inputs` first resolves every manifest entry relative to its own directory. The 80-target map contains only:

```text
/etc/systemd/system/dispatcharr-stack.service.d/40-native-hardening.conf
```

It omits the separate HERE-relative source-copy path required by that loop. Expected bytes are already pinned to SHA-256 `c0688992469db9c181faa9be16530db14fe734d5939de3b988c5ab8c90d6dd64`. An offline closure check reproduces **exactly one missing input mapping**.

**The previous review missed this file-closure requirement.** Its checker special-cased the unit mapping and its 15 passing tests did not execute the complete installed `inputs()` path. The source/image hashes were not wrong; target coverage was incomplete. No extra 81st target was added, source or manifest edited, hash regenerated, verifier weakened or candidate start attempted. Correcting this host packaging defect does not itself require rebuilding the accepted image, but requires a separately reviewed complete transition and an actual installed-input closure regression.

The candidate failure occurred before AIO creation, systemd reload for the native release, application bootstrap or registration. Provider anchors had been prepared with exact ownership/modes and confirmed empty/revoked; no authorization was published.

## Scoped rollback and failed restoration

Before rollback, every installed candidate target was conflict-checked, all protected containers were stopped, exact kernel protection persisted, public guard/grant assertions were absent, provider projection was empty, and the guard transaction was revoked/unblocked. The ownership ledger hash matched the checkpoint; state contained only `lock` and `owned.json`. No candidate application execution or API mutation had occurred, so no candidate schema/provider-job side effect existed. All unrelated fingerprints matched. Rollback prerequisites were verified rather than inferred from image availability.

The complete original 67 public files/root ownership/modes were restored from the protected snapshot. All 13 introduced files, including 40-native-hardening.conf and the native overlay, were renamed intact into the root-private inactive-candidate archive after exact candidate-hash checks. Revoked provider anchors/private metadata were preserved; no stale authorization was restored.

Per the reviewed rollback procedure, only AIO was recreated stopped from the original Compose with image 14c. VPN/relay/gateway container IDs and the dedicated network were preserved. Original input/stopped contracts and native systemd unit syntax/dependencies passed; the original 20/30 drop-ins were reloaded, without 40 or native commands.

The one authorized managed restoration start had these actual outcomes:

| Stage | Result |
| --- | --- |
| Original input verification | PASS |
| Unchanged resource admission | PASS in 15.002s |
| Managed guard application | PASS |
| Original lifecycle preparation/prestart | PASS |
| VPN and relay during startup | Observed healthy before cleanup |
| AIO HTTP health during startup | A successful health exit was observed; not full backend acceptance |
| `backend.py` via Docker exec | **Exit 1** |
| Registration/export rebind/gateway-last | Not reached |
| Managed ExecStart | Exit 1 |
| Automatic scoped failure cleanup | Four protected containers stopped; public assertions withdrawn |

Admission samples:

| Elapsed s | Idle % | Steal % | Load1 |
| ---: | ---: | ---: | ---: |
| 5.001 | 97.535 | 0.05 | 0.23 |
| 10.002 | 94.548 | 0.05 | 0.21 |
| 15.002 | 97.885 | 0.0 | 0.19 |

The failure boundary is established by retained Docker exec events: **backend.py exited 1 before register.py**. The original lifecycle captures/discards command stderr and exposes only the generic failure. The exact failing backend subcheck—API bytes, database/migrations, authenticated Redis, two fresh uWSGI witnesses or Celery responses—cannot be determined from retained output. No passing subcheck is inferred. An optional read-only stopped-container source-copy query also failed and was not used as hash-verification evidence. No additional start or runtime-directory change was made to obtain diagnostics.

There was no second restoration start, Redis/PostgreSQL reset, database restore, source fix or security bypass. Original configuration rollback is complete; **runtime restoration is not successful**.

## Final protected state

Final verification: **2026-11-18T20:38:44Z**.

| Service | Container ID | Image | State |
| --- | --- | --- | --- |
| `dispatcharr` | `0d34537414caa0b788415ef7017e77687768fd9344353a34e882bd5a5c027a04` | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` | exited |
| `rivendell-iptv-vpn` | `1b9d20c931948aee6e12bc97401c1626e3ecf42962b06dfd46d8308e95d44d2e` | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` | exited |
| `rivendell-iptv-relay` | `3aa41213fdc8cacb88f18ce20136bec082e55490baf58d79f2e01d55ba85be27` | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` | exited |
| `rivendell-iptv-gateway` | `448ceeb80a51e6660a04cda3449a140052c2cb0984040d727824894413606199` | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` | exited |
| `jellyfin` | `6798247b9099bc791892f7118f598aa48d0b7c21ecfc616bbbebfee43c22763b` | `sha256:baba630419915985442f315f08b0cf46d9f4c8a0cc4bd38e94a6d35751dd5ef5` | running |

The stack unit is failed after its sole restoration attempt. The guard's kernel policy remains exact. Public guard/grant records are absent; the legacy root-private marker matches the retained policy. The provider public projection is empty. Positive live VPN/backend/queue/heartbeat acceptance cannot be claimed while the containers are stopped.

Original 67 public hashes are restored; introduced13 active files are absent/archived. DW ownership ledger remains unchanged at 3/3, with no uncertain registration/DELETE state or API rebind. Existing exports were not deleted, but the stopped stack cannot serve them. Jellyfin's raw LiveTV XML hash matches the checkpoint, its container is healthy, and no settings changed.

All 29 genuinely unrelated containers retain exact IDs/images/configuration/start/restart/health fingerprints. Docker process identity is unchanged. Network configuration/IDs/unrelated memberships and all volumes are unchanged. The final full network digest is the verified **stopped-state** digest `323f303c08b51c7ca59bd25a054ca89276b5e6bd182c570000bdaa1e14382c01`; its difference from the running digest is the known protected VPN endpoint/occupancy removal, not a policy change.

Full sanitized receipts, attempted 80 target hashes, final 67 hashes, before/final fingerprints and source/image verification are in `configs/dispatcharr-iptv/production-image-binding/hardening-completion-results.json`. Private diagnostics/transaction receipts remain under `/root/dispatcharr-hardening-20261118T201302Z`. No credentials, tokens, broadcaster URLs, database contents or archive bytes are published.

## Remaining work and decision

1. Restore application availability only under separate authorization for the stopped original stack. Diagnose/preserve the detailed backend readiness failure before any further managed start; do not infer a safe retry or reset application state.
2. Correct and review the missing local 40 input mapping with a closed installed-file-tree verifier. The accepted image must remain unchanged unless a separately demonstrated application defect requires another reviewed correction.
3. Obtain a new explicit cutover authorization and repeat fresh recovery/state/security gates after review. The present single transition and restoration allowance are exhausted.
4. Only after successful hardened production acceptance consider separately authorized AirVPN-bound provider metadata authorization. Media destinations, provider activation, Jellyfin exports and playback remain separate approvals; native removal remains gated as documented.

**Final: recovery protection GO; production hardening/runtime availability/provider activation NO-GO.** Stop with the original configuration restored, four IPTV components protected and stopped, Jellyfin/unrelated services preserved, and all evidence retained. No claim of deployment completion is made.
