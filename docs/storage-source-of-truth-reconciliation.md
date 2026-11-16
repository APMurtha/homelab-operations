# Storage source-of-truth reconciliation

2026-11-16 UTC / 2026-11-15 Eastern. Andrew's homelab; read-only infrastructure
inspection with repository/NEST source documentation corrections only.

**Scoped persistence installation: GO for the existing recovery prerequisite,
subject to fresh preflight and explicit installation authorization.** No new
backup, VM, full production restore or legacy-pool repair is required for that
non-migrating service-ordering change. **Unattended production readiness remains
incomplete.** Nothing was installed or activated.

Evidence labels used below:

- **Verified live:** observed in this inspection, including current metadata and
  read-only network/file queries; it does not imply a failure or restore test.
- **Verified from configuration:** actual current file/settings/dependency evidence.
- **Historical documentation:** retained dated records or owner console results.
- **Unverified:** cannot be concluded from available access/evidence.

The existing authoritative inventory is [network.md](network.md#storage-source-of-truth),
with [naming.md](naming.md) defining identities. This document is the reconciliation
and evidence report, not a competing inventory.

## 1. Current storage topology

| Resource | Evidence and current role |
|---|---|
| **Moria, 10.10.10.8** | **Verified live:** public UniFi OS `/api/system` reports name `Moria`, hardware shortname `UNASPRO8` (UniFi UNAS Pro 8). HTTPS, SMB and NFS reachable from Rivendell and Denethor |
| Primary media storage | **Verified live:** six NFSv3 exports from Moria back Rivendell `/data/books`, `/data/downloads`, `/data/movies`, `/data/shows`, `/data/music`, `/data/podcasts`; container mount namespaces agree |
| Additional NAS export | **Verified live:** `data` export is advertised to Rivendell, but it is not a currently mounted replacement for `/data/media`; purpose/completeness unverified |
| **Orthanc, 10.10.10.2** | **Historical documentation:** remains a Proxmox node; local ZFS pool named `moria` confirmed in owner's Nov 15 console. **Verified live:** its distinct `/moria` NFS export is still active |
| Remaining legacy mount | **Verified live:** Rivendell mounts `10.10.10.2:/moria` at `/mnt/moria`, NFSv4.2. `/data/media` still resolves to `10.10.10.2:/moria/media` |
| Host `/data` | **Verified live:** Rivendell root ext4 directory, with multiple distinct nested mounts; not one uniformly NAS-backed tree |
| Dispatcharr persistent data | **Verified live:** `/docker/dispatcharr-iptv/data`, including `db`, is on Rivendell local root ext4. Container `/data` is this bind, not host `/data` |
| Denethor checkpoint | **Verified live:** local secondary NVMe Btrfs `/mnt/data`; neither UNAS nor Orthanc |

### Actual export and mount configuration

**Verified from configuration and live mounts:** Rivendell fstab and active mounts
agree for all six UNAS media paths. The current server export prefix is:

```text
10.10.10.8:/volume/e5ff6758-b2fb-4b57-9962-1562e37ccdf7/.srv/.unifi-drive/<share>/.data
```

Shares `books`, `downloads`, `movies`, `shows`, `music`, `podcasts` are mounted;
`data` is additionally advertised. `showmount -e` lists each scoped to Rivendell
10.10.20.30. They use NFSv3/TCP and fstab automount options. The existing legacy
entry is NFSv4.2 `10.10.10.2:/moria` at `/mnt/moria`, with a separate bind entry
`/mnt/moria/media` → `/data/media`. Generated mount-unit What/Where/SourcePath
metadata was inspected; no mount configuration was changed or remounted.

**Verified live:** Audiobookshelf `/library` is NAS books; Jellyfin `/media/movies`
and `/media/shows` are NAS mounts. NZBGet, qBittorrent, Radarr, Sonarr and Bazarr
bind parent `/data`. The NZBGet namespace explicitly shows the legacy `/data/media`
mount as well as UNAS mounts. A bind reference proves exposure, not that a service
has recently opened a particular legacy file. Do not equate mounted/configured
with actively consumed, and do not assume an old directory is disposable.

### Capacity, access and health boundary

**Verified live:** NFS reports approximately **38.18 TiB total / 34.17 TiB available**
for the UNAS volume. The six share readings describe the same volume and must not
be added together. SMB share enumeration with the existing Denethor account
shows `denethor_backup`; that is the account-visible list, not necessarily every
share configured on the NAS.

**Unverified:** current NAS RAID/pool/disk health, redundancy and SMART status.
The public identity endpoint is available; the authenticated system endpoint
returns 401 without a NAS administrative session. Available NFS capacity and
successful media access do not establish disk health. No SMB credentials were
reused as a NAS administrator login and no permissions were changed.

## 2. Historical versus current Moria

**Verified live / configuration:** two resources still coexist:

- **Moria UNAS Pro 8 — 10.10.10.8:** primary media NFS and configured SMB backup
  destination. It is not the ZFS device inspected through Orthanc's console.
- **Orthanc legacy pool/export — 10.10.10.2:/moria:** a same-named resource on a
  valid Proxmox node, still mounted and still referenced by the old backup job and
  `/data/media` configuration.

**Historical documentation:** the Nov 15 authenticated Orthanc console showed
single-device `moria`, `/dev/sdb1`, 22 read errors, degraded state, no known
permanent data errors. Those findings apply to that legacy local ZFS pool,
**not the UNAS**. The old VM backup and Nov 2 media backup archives are additional
important legacy recovery references; Phase 6B-3F/3E recently verified their
accessibility/metadata. This task did not scan datasets or archives there again.

**Verified live:** Orthanc RPC advertises `/moria` to 10.10.20.30 and 10.10.20.70,
and existing mounts remain usable. **Unverified:** a fresh Orthanc-host pool
status, all Proxmox storage consumers and every host-side dataset use. No authorized
Orthanc SSH profile was available; prior denied authentication was not retried.
Current export names alone cannot prove physical backing. The dated console is
retained as the latest host-side evidence, not silently promoted to a new query.

Thus migration of the six primary media trees is established, but complete
retirement of Orthanc storage is **not** established. No cleanup/migration follows
from this reconciliation.

## 3. Incorrect assumptions and audit classification

I failed to carry the existing primary-UNAS service map consistently into the
Dispatcharr backup discussion. Following the currently failing legacy backup
script into Orthanc diagnostics found a real remaining dependency, but allowing
that wider storage problem to become a blanket installation gate was unnecessary
once the independent scoped checkpoint existed. The evidence does not support
rewriting every Orthanc reference as obsolete.

| Finding/source | Classification and correction |
|---|---|
| README/network/naming and Nov 4 migration record already distinguish UNAS vs Orthanc | **Current and verified**, but operational detail was incomplete; current maps now include nested mounts, backup protocols and checkpoint backing |
| NEST Andrew media/network source maps already identify NAS .8 and separate export .2 | **Current and verified**, not wholly wrong; expanded in place with current evidence and mandatory backing checks |
| Installed NEST 2.1.0 generic system descriptions still say Andrew deployment not yet verified | **Outdated** packaged discovery metadata; source maps/registry are newer. Installed cache remains immutable; no claim it was rebuilt |
| Orthanc ZFS health report | **Historical but valid** for that pool; annotated to prevent interpreting it as UNAS health |
| Phase 6B-1/2 legacy backup findings | **Historical but valid**, and the job remains configured. Proposed old source-check repair is not a current destination decision |
| Treating legacy pool repair or full DR certification as prerequisite for two-unit rollback | **Outdated** scope assumption; superseded by verified independent Phase 6B-3F checkpoint |
| Phase 6B-3E recovery NO-GO | **Historical but valid at collection**, before checkpoint creation; annotated with current scoped readiness |
| Restic HTTP500 interpreted as general UNAS unavailability | **Outdated/incomplete diagnosis**; direct SMB now reports permission denied |
| Rivendell backup destination should simply become .8 by replacing .2 | **Ambiguous / requires verification**; actual NAS backup export/access contract is not established by its media shares |
| `/data/media`, old media job, Proxmox `moria-data` references | **Current references / historical placement evidence**; not globally removed or rewritten |
| Denethor `/mnt/data` interpreted as UNAS | **Incorrect**; verified local NVMe backing |
| Denethor/Omarchy agent note about secondary Sabrent data drive | **Current and verified**; left unchanged |
| Accepted Compose bind paths and firewall manifests | **Current and verified** within their scope; no infrastructure code changed |

The search covered relevant homelab docs, diagrams, runbooks, deployment/backup
sources, NEST source contexts/skills and agent guidance. Historical migration
records, test fixtures, Proxmox node IPs and unchanged live scripts were not
subjected to a global replacement.

## 4. Authoritative documentation and NEST corrections

**Verified from source changes:** updated existing homelab README, network storage
inventory, naming notes and service-placement diagram. Deployment and Denethor
backup runbooks now point to the reconciled inventory. Dated Dispatcharr backup,
ZFS, production audit and preflight reports gained clearly dated scope notes;
their original evidence and proposed diffs remain intact. The Phase 6B-3F report
links this newer verification without changing the checkpoint archives.

**NEST source corrected locally:**

```text
Projects/nest/home-foundation/context/systems/andrew-media/start-here.md
Projects/nest/home-foundation/context/systems/andrew-network/start-here.md
```

Guidance now requires live mount/container backing checks, distinguishes the two
Moria resources and local checkpoint disk, and separates scoped rollback from
full DR. Conflicting old scripts must be reconciled before destructive/recovery
work. It records the concrete SMB error without storing credentials/private logs.

**Installed-package boundary:**

```text
/home/murth/.codex/plugins/cache/nest-shared/nest-home/2.1.0/
```

This cache was not edited, rebuilt, installed or published. The matching source
corrections are prepared in `Projects/nest` for its normal reviewed release path;
they are not falsely described as already loaded by the installed plugin. Its
`SYSTEMS.md`/skills retain the existing person/system selection rules. No new
household profile or competing inventory was initialized. No skill or runtime
framework was changed. Existing unrelated source changes were preserved.

## 5. Existing Dispatcharr checkpoint: actual backing and verification

| Location | Host and backing | Independence |
|---|---|---|
| `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z` | **Verified live:** Denethor; actual mounted `/dev/nvme1n1p1`, Btrfs UUID `48542bca-0466-4022-95e4-e01a576ffbc0` | Independent of Rivendell root and original application data; also different from Denethor root UUID `8a1bd44c-2161-4d9f-ae03-461589fa1efe`. Not UNAS and not Orthanc |
| `/root/dispatcharr-minimal-recovery-20261116T043509Z` | **Verified live:** Rivendell; `/dev/mapper/ubuntu--vg-ubuntu--lv`, ext4 UUID `dab2054e-ee53-4b16-8c46-4aa17f643609` | Same filesystem as original `/docker/dispatcharr-iptv/data/db`; convenient local rollback, **not independent** |

An autofs layer appears at Denethor `/mnt/data`, but the active underlying
filesystem is the local NVMe Btrfs device above, not a network share. The VM's
LVM device is guest storage; current physical Proxmox disk placement was not
independently re-queried in this task.

**Verified live:** both locations remain accessible. All three independent
archive sizes and SHA-256 hashes match the Phase 6B-3F receipt. All four local
rollback files match their mirrored bytes inside the independent archive. Current
Compose, guard/parser, gateway, startup/resolver/VPN configuration and JWT hashes
match the captured deployment. No new backup or checkpoint was created. The member-name audit also corrected an overbroad
Phase 6B-3F description: standalone application-check/provider-audit sources
remain in the repository, not those archives. The required minimal runtime
verifier/contracts, custom build and relay sources are included; no rollback
dependency or existing artifact was removed.

**Verified live, bounded recovery-path test:** the existing 244,987-byte archive
was read on Denethor and sent over the selected authenticated SSH transport to
Rivendell, where its size/hash were verified entirely in RAM. Nothing was written
or restored on Rivendell. This demonstrates current off-host access and retrieval,
not merely a successful local archive checksum.

**Historical documentation revalidated by unchanged hashes:** matching PostgreSQL
17 tools had parsed and fully decoded the custom dump without connecting to a
restore target; asset and source-member hashes passed. Those archive-integrity
results remain applicable to identical bytes. **Unverified:** actual SQL replay,
complete application recovery and retrieval after loss of Denethor/network/SSH
credentials. No full restore was simulated or claimed. Owner-only checkpoint
permissions remain important; the archives are not additionally encrypted and
are not automatically covered by Denethor's ordinary home-backup schedule.

## 6. Cause of failed UNAS access

**Verified live:** from both relevant clients, NAS TCP443/445/2049 is reachable.
Public identity is Moria/UNASPRO8. From Denethor using the configured SMB remote,
server share enumeration succeeds and includes `denethor_backup`. Both listing
that share and stat'ing `denethor_backup/denethor-restic/config` fail with
`permission denied`. Credentials/obscured passwords were neither printed nor
changed; no alternative account was tried.

**Verified from configuration:** the existing Restic backend invokes Rclone SMB
against literal 10.10.10.8, so this access does not depend on a stale DNS alias or
Orthanc NFS pathname. The SMB endpoint/share name is not obsolete on the available
evidence. Rclone's underlying access denial explains the generic Restic backend
HTTP500 seen in Phase 6B-3F. It did not establish NAS offline or damaged storage.

**Unverified:** which NAS share ACL/filesystem permission/account mapping causes
the denial, and whether the encrypted repository folder remains present behind
that denial. Client metadata cannot distinguish all server-side ACL layers.
No authenticated NAS admin session was available, and none was fabricated by
reusing another service's credentials. That narrow NAS-side access review is
future work; no remount, firewall change, permission change or credential reset
was performed.

## 7. Existing backup configuration requiring future correction

| Job | Evidence and smallest next decision; no changes made |
|---|---|
| Rivendell `/usr/local/libexec/rivendell-media-backup.py` | **Verified from configuration:** destination `/mnt/moria/backups/rivendell`; guard expects `10.10.10.2:/moria/backups` but actual mount is `10.10.10.2:/moria`. This exact mismatch fails before backup data copying |
| Rivendell backup service/timer | **Verified live:** service failed exit 1; timer enabled/active, next recorded Nov 16 ~08:33 UTC. **Historical documentation:** last success Nov 2; scope excludes dedicated Dispatcharr |
| Denethor `~/.local/bin/denethor-backup` | **Verified from configuration:** encrypted Restic via Rclone SMB to NAS .8/share denethor_backup; no obsolete Orthanc source in this job |
| Denethor backup status | **Verified live/receipt:** last success Nov 14 16:00 UTC; service currently failed, 11:00 Eastern timer enabled. Current access denial is separate from Rivendell's NFS-validation failure |

For Rivendell, first reconcile intended destination with the owner. If legacy
Orthanc is intentionally retained, a future scoped fix must validate actual
source `10.10.10.2:/moria`, mountpoint `/mnt/moria`, NFS type and exact backup
directory, with no local-root fallback. The old proposal alone does not authorize
retaining that destination after a migration.

If the intended target is now the UNAS, first establish an existing suitable
backup share/export and authorized Rivendell access. The advertised NAS `data`
export is not automatically a backup destination, and Denethor's SMB share is not
a mounted Rivendell NFS target. A future approved correction would update the
mount/destination contract and script's exact source/target validation together,
preserving encryption/retention/scope. Do **not** replace the IP alone or accept
any filesystem. None of these script/mount/schedule edits was made here.

For Denethor, inspect the current NAS-side SMB access mapping for the existing
account/share; the evidence does not justify changing protocol/host or broadly
relaxing permissions. This is a narrow access issue, not a request to redesign
homelab backup architecture.

## 8. Dispatcharr readiness: two separate conclusions

### A. Scoped minimal persistence installation

**GO — recovery prerequisite satisfied, with explicit installation approval still
required.** The transaction-consistent PostgreSQL backup, required environment/
JWT/WireGuard/security inputs, persistent assets, verified custom image/relay
sources and precise local rollback baseline remain accessible and intact. The
independent copy is physically on Denethor, and transfer back to Rivendell was
verified without a restore.

Installing the two units/override neither upgrades images nor migrates the database.
Normal rollback preserves existing database/data and restores only the dedicated
Compose/restart-policy/unit state. A complete production restore test would not
be proportionate as a new blanket prerequisite for this scoped change. Refresh
preflight or checkpoint only if actual deployment/configuration drift is found;
do not repeat the completed backup unnecessarily.

Neither repairing Orthanc's old pool/job nor fixing the UNAS SMB share is a blocker
for this already independent checkpoint. No new VM, controller architecture or
backup execution is proposed. Follow the approved minimal plan in its maintenance
window; this task does not activate it.

### B. Unattended production operation

**Not yet certified.** Genuine remaining work includes the intended routine
backup destination/access and Dispatcharr coverage; encrypted/off-host durability
and retention policy; a proportionate isolated restore rehearsal; NAS/legacy
storage health as relevant to the services still using each; planned boot/restart
acceptance; and operational health/backup-age/disk monitoring. No automated
restarts based only on noisy buffering warnings are justified.

The single protected NVMe checkpoint is useful scoped recovery, not scheduled
NAS backup, redundancy, immutability or full DR certification. These broader
limits must not be conflated with installing two service-ordering units.

## 9. Files changed and validation

**Homelab documentation updated in place:**

- `README.md`, `docs/network.md`, `docs/naming.md`.
- `diagrams/service-placement.mmd`.
- `runbooks/dispatcharr-rivendell-deployment.md`, `runbooks/denethor-moria-backup.md`.
- Dated scope annotations in `docs/dispatcharr-backup-storage-phase6b1.md`,
  `dispatcharr-backup-repair-phase6b2.md`, `orthanc-zfs-health-phase6b2a.md`,
  `dispatcharr-production-readiness-phase6a.md`, `dispatcharr-installation-preflight-phase6b3e.md`
  and `dispatcharr-recovery-checkpoint-phase6b3f.md`.
- This reconciliation report.

**NEST source:** the two existing Andrew system start-here contexts listed above.
No installed cache, credential, live backup script or deployment manifest changed.

**Validation:** live mount/export/container backing and port queries; bounded
public NAS/SMB metadata checks; archive/current-source/rollback hash comparisons;
RAM-only retrieval test; relevant link/inventory consistency checks. NEST's
required `./scripts/validate` completed successfully: **184 tests passed**. Raw
private metadata/diagnostics remain in `.ai-local/storage-reconciliation/`, not
public knowledge or Git. Existing checkpoint archives were not altered.

No backup, new checkpoint, remount, Docker change, service restart, database
restore, cleanup, firewall/VPN edit, Jellyfin change, unit installation or new
infrastructure was performed. Documentation corrections authorize none of those
operations.
