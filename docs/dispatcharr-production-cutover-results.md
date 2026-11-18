# Dispatcharr production cutover results

**NO-GO — stopped during mandatory preflight. No production transition was issued.**

The owner authorized one controlled transition following plan `92c802a69d6e9df2744797116dc096666dec6d69`, accepted runtime evidence `d522593`, accepted hardened image `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439`, and known-good rollback image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. The owner separately confirmed no conflicting administration for this cutover window.

The required current consistent matched recovery coverage could not be established. Per the authorization and approved plan, this blocks any stop or installation. **Zero managed stops, starts, container recreations, installed targets or daemon reloads occurred.** No provider activation, playback, API-record write, backup creation/restore or rollback was performed. The existing working four-service stack remains running on the known-good image.

## Observed preflight

Fresh read-only production observation: **2026-11-18T19:07:29Z**; preservation verification: **2026-11-18T19:10:42Z**.

| Gate | Observed outcome |
| --- | --- |
| Target/account | NEST Andrew / andrew-media / media; authenticated Rivendell, murth UID1000; approved root lifecycle accessible |
| Approved checkout | Clean exact `92c802a`; proposal verifier PASS |
| Candidate integrity | All proposal artifact hashes verified; complete 80-target mapping/dependency checks pass; no regenerated pins |
| Original installed files | All 67 original public targets match known-good `227122d`, root:root 0644, regular single-link files |
| Native introduction | All 13 introduced targets absent, including 40-native-hardening.conf and native overlay; nothing staged/activated |
| Image identities | Accepted 71 and rollback 14c immutable IDs both present locally; no build/pull/retag |
| Production health | Four IPTV containers and Jellyfin healthy/running; all 33 container fingerprints exactly match prior accepted evidence |
| Existing security | Installed `verify.py running` PASS, mutations 0; repeated after recovery-gate stop |
| Media process observation | No ffmpeg/ffprobe process observed; this does not establish every session/recording idle predicate |
| Resources | Loads 1/5/15=[0.27294921875, 0.2294921875, 0.255859375]; available RAM=3453513728 bytes; Docker filesystem available=7604207616 bytes |
| Recovery | **BLOCKED: current matched recovery coverage not established** |

The installed running verifier checks the existing guard/public-grant coherence, exact kernel firewall semantics, VPN owner/namespace, routing, DNS/IPv6, source/mount/privilege/resource contracts. Its PASS describes the **existing release**, not activation of the proposed native provider lifecycle. No firewall/VPN/DNS policy was modified. Stack/guard units remained active/exited, Docker active/running with MainPID 1112.

An initial NEST doctor failed its Compose-version probe under the unprivileged SSH account. The approved execution context was checked separately: root reports **Docker Compose v5.6.0** successfully. No package, PATH, privilege or plugin configuration was changed; this was not the cutover blocker.

## Recovery gate and exact limitation

The independent Denethor reference remains accessible:

`/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`

All three archive sizes/hashes freshly matched its manifest:

| Archive | SHA-256 | Result |
| --- | --- | --- |
| `rivendell-recovery.tar.gz` | `e38c5d1b42b89c5b0837fa782d960e51c9b22df030ae443388469e9751980c38` | PASS |
| `runtime-and-rollback.tar.gz` | `4a5e8bc0042accf48a3994f7e8abd19fcac578126931b08b5419012b10a04a82` | PASS |
| `source-and-install-plan.tar.gz` | `6186fedc4f8369e61903ef5cfeced8674eafdaf9504d0dee647f36bc03961def` | PASS |

That reference is dated **2026-11-16**, before the permanent four-service deployment and working DW English/Jellyfin integration. Existing Rivendell directories `/root/dispatcharr-minimal-recovery-20261116T043509Z` and `/root/dispatcharr-minimal-recovery-20261116T051539Z` contain historical public rollback files/receipts. Metadata was inspected; no claim of a new current matched recovery set is made.

The native backup directory `/docker/dispatcharr-iptv/data/backups` contains ZIPs for November 16, 17, 18. Latest is `dispatcharr-backup-2026.11.18.03.00.00.zip`, **49,339 bytes**, modified **2026-11-18T08:00:00Z**. ZIP central-directory inspection found exactly two members:

| Member | Uncompressed bytes |
| --- | ---: |
| `database.dump` | 253,627 |
| `metadata.json` | 173 |

No member data or database contents were read or extracted. This is evidence of a current database-backup artifact, **not proof of complete matched DB/assets/protected configuration/private transaction-state recovery coverage**. It was not declared corrupt or unusable. Historical deployment journals also do not establish that coverage by themselves. Bounded inspection of documented root recovery directories, application root/private metadata and native backups found no validated current matched set; this does not claim no other backup exists anywhere.

The existing export service and timer are inactive/dead, with no last trigger recorded. Neither was started or changed. No export, backup, database dump or stopped-state checkpoint was created to manufacture a passing prerequisite.

The approved review explicitly requires “a current consistent protected recovery set” and states “Old three-service archives alone are insufficient.” It also requires exact original public/private-state preservation before changes. We have a verified current public-hash inventory, but have **not** created a root-private byte snapshot or a current private transaction-state snapshot after this failed prerequisite. No production stop for backup was inferred from the cutover permission.

## Not completed after the recovery gate

The remaining preflight was not declared PASS: current authenticated owned-channel/stream/ACL reads; full playback/recording/session checks; pending registration/DELETE reconciliation; live migration count/fingerprint and pending migration plan; fresh 18-file image export/source verification; private receipt preservation/snapshot; plugin-maintenance schedule review and production-only outbound-behavior assessment. These remain mandatory before any future transition. No API credentials or provider secrets were accessed to continue after the blocker.

In particular, the proposed native image's successful isolated 11-test acceptance is preserved as historical evidence; it is not a fresh production database/worker/security-endpoint validation. No unsupported assertion was bypassed and no synthetic provider authorization was created.

## Image/configuration and service preservation

Current services at both observations:

| Service | Immutable installed image | Result |
| --- | --- | --- |
| `dispatcharr` | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` | healthy/running; unchanged |
| `rivendell-iptv-vpn` | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` | healthy/running; unchanged |
| `rivendell-iptv-relay` | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` | healthy/running; unchanged |
| `rivendell-iptv-gateway` | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` | healthy/running; unchanged |
| `jellyfin` | `sha256:baba630419915985442f315f08b0cf46d9f4c8a0cc4bd38e94a6d35751dd5ef5` | healthy/running; unchanged |

The preflight and postflight comparisons establish:

- All 33 container IDs, immutable images, start times, restart counts, health/state and Config/HostConfig/Mounts fingerprints unchanged.
- All 67 public file hashes/ownership/modes unchanged; all 13 introduced native targets still absent.
- Docker MainPID remains 1112. No daemon restart/reload was requested.
- Docker network inventory digest unchanged: `51839910ef1955c6811a500972dea224445df3b93c5d4dc9a5afaafe49278192`.
- Docker volume inventory digest unchanged: `62bba3105a84730f80f6a2027aab8ef6bda044be99c2d5375c5f8e98b9d2248a`.
- Existing running/security contract passes again after the decision to stop.

Jellyfin's container and mounts/configuration fingerprint remain unchanged and it remains healthy. No Jellyfin settings/API mutation or discovery refresh was issued. This task does not claim a new authenticated LiveTV-content comparison or playback measurement. Existing DW channel/stream ownership was not mutated; its fresh API acceptance was not reached.

The full exact original 67 installed hashes and all 33 before/after fingerprints are published in `configs/dispatcharr-iptv/production-image-binding/cutover-preflight-results.json`. The reviewed proposed 80-map hash is `586c703eea209c28d36970926b756431b4e63c748041ec391249470227b2ba9a`; this remains a proposal, not an installed mapping. The active repository native release remains `aio_image: null`; the accepted image remains available for later review.

## Validation, rollback and final decision

The read-only proposal verifier and **15 offline binding regression tests passed**, with no failures. Existing evidence/artifact pins were checked without regeneration. No application/runtime test was launched. Read-only scripts were streamed through NEST; no temporary host containers, volumes or networks were created, so none required removal.

**Rollback: not invoked and not needed.** No target or image was installed, no protected service was stopped, and no application mutation needs reconciliation. There is no failed-start or uncertain-transition state. The authorized single production transition was never initiated; this task ends at the preflight blocker and does not automatically proceed later.

**Final: NO-GO for this cutover and subsequent provider activation.** Resolve current matched recovery coverage through a separately reviewed/authorized procedure, or identify and verify an existing complete current checkpoint. Then repeat every remaining fresh prerequisite under a new explicit cutover instruction. No deployment or additional attempt is performed by this report. Production continues on the healthy known-good four-service baseline, with Jellyfin unchanged.
