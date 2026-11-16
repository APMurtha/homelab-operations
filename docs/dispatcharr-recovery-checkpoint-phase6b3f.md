# Dispatcharr Phase 6B-3F — recovery checkpoint

**Reverified 2026-11-16:** archive hashes, host/path backing and rollback mirrors
remain valid. Denethor NVMe is independent; the earlier UNAS HTTP 500 is now
traced to direct SMB permission denial, not NAS unreachability. See
[storage reconciliation and split readiness conclusions](storage-source-of-truth-reconciliation.md).

2026-11-16 04:33–04:35 UTC (Nov 15 US/Eastern).
Target: Rivendell, 10.10.20.30. **Checkpoint preparation completed; persistence
units remain uninstalled.**

**Recommendation: GO for the minimum recovery checkpoint required before a
separately authorized controlled persistence installation.** Recheck identity,
file hashes and free space immediately before that installation. This is not
approval to install now or certification of unattended production recovery.

Current database/files were backed up without stopping PostgreSQL or Dispatcharr.
All archive-member integrity checks passed. **No full database/application restore
was performed.** The independent copy is on Denethor's existing secondary disk;
the attempted UNAS repository probe failed, and Orthanc's degraded pool is not
relied upon for this checkpoint.

## 1. Recovery inventory

### Database and application

| Asset | Verified source / treatment |
|---|---|
| PostgreSQL | Inside current Dispatcharr AIO, not a separate DB container |
| Database / application role | `dispatcharr` / `dispatch`; role has login, superuser, createdb and createrole |
| Server/client tools | PostgreSQL 17.11, matching pg_dump and pg_restore 17.11 |
| PGDATA | Container `/data/db` → host `/docker/dispatcharr-iptv/data/db`, UID/GID 1000:1000, mode 0700 |
| Database size | 13,285,043 bytes at inventory |
| Extensions | `plpgsql` 1.0 only |
| Tablespaces | `pg_default`, `pg_global`; no custom external tablespace |
| Persistent assets | `data/jwt`, logos, uploads, scripts, plugins, m3us and epgs; file contents/ownership/modes/hashes captured |
| Required secrets/config | Private app.env, WireGuard wg0.conf, egress-policy.json, generated application environment, selected PostgreSQL config files |
| Runtime environment | `/etc/profile.d/dispatcharr.sh` captured privately as recovery reference; secrets never printed |
| PostgreSQL configuration | postgresql.conf, pg_hba.conf, pg_ident.conf, PG_VERSION captured separately from raw PGDATA |

The first conventional OS-user `postgres` probe did not match this AIO layout.
The already-generated application environment was then used to establish the
actual database and authenticated role. No password was placed in command
arguments or diagnostic output. SQL inspection used read-only transactions.

### Deployment, security and rollback

Captured accepted Compose, guard.py/security.py, Caddyfile, resolver, startup
gates, VPN post-rules and pilot rollback source. **Coverage clarification from
read-only reconciliation:** the standalone application-check.sh/provider-audit.sql
files remain in the repository but were not members of these checkpoint archives;
the minimal runtime verifier/contracts are included in the source archive. Those
optional diagnostic sources are not required to restore the captured deployment
or reverse the two-unit installation. The running containers' exact IDs, image IDs/references, HostConfig,
mounts, network settings and health/start state were recorded privately; runtime
container Env was deliberately not dumped. Required secrets were captured from
the explicit protected configuration files instead.

Captured the dedicated Docker network's configuration, only the accepted scoped
nftables table (JSON and native representation), Docker service/socket configuration,
relevant systemd dependency/enabled/absence facts, and parent directory metadata.
No full-host firewall restore or unrelated media-service restoration is required.

Custom development recovery includes:

- Exact final Phase 4H Dockerfile, .dockerignore and four-file readiness overlay.
  **All six file hashes match the final build-input manifest.**
- Source commit `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`, base digest, normalization
  recipe, patches and build verification sources. Recorded deterministic context
  SHA-256 remains `04e270aebc98a9df5f1e5911e8417f0eba46f208a88a2b50e7913ed93b6221c1`.
  Recreate the normalized build context using the saved recipe; no rebuild was run.
- Phase 4M HLS relay artifact plus relay, deadline/telemetry, enforcement and test
  sources. No trial credentials, broadcaster requests or channel imports were
  needed. No relay is activated by this checkpoint.
- Minimal persistence candidate and installation/rollback documentation. The source
  archive contains 83 selected source/document files, not the entire homelab repo.

### Image identities

All are Linux/amd64; IDs/digests were read from the actual local image store.

| Image | Current image ID / recorded digest |
|---|---|
| Running Dispatcharr 0.33.0 | `sha256:96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` |
| Dedicated Gluetun | `sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` |
| Caddy | `sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |
| Retained custom test image | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` |

Standard downloadable image layers and disposable container filesystems were not
backed up. Custom image recovery is via its verified saved build context/recipe;
base-registry availability remains a dependency. Nothing was rebuilt or pruned.

Excluded: raw live PostgreSQL files, cache/log/stream buffers, old native backup
ZIPs, downloaded server cache, unrelated media data/credentials and trial media.
The excluded models and recordings directories were checked and contain no files.
Redis live session/heartbeat state is ephemeral and is not restored as streaming
ownership. Existing durable application state is in PostgreSQL and captured assets.

## 2. Online PostgreSQL backup method

Used the running image's generated environment as UID/GID 1000:1000, privately
mapping POSTGRES_* to libpq PG* environment values. Passwords never entered argv.
The actual export used:

```text
pg_dump --format=custom --compress=6 --no-password --lock-wait-timeout=5s
pg_dumpall --roles-only --no-role-passwords --no-password
```

The environment selected database `dispatcharr` and role `dispatch`, with
`default_transaction_read_only=on`, a bounded statement timeout and lock timeout.
The custom dump is **252,129 bytes**, with 62 table-data entries. Role definitions
and grants are saved separately; password hashes are excluded from roles.sql.
The saved protected application environment supplies the role password during a
later authorized recovery.

pg_dump provides an online consistent database snapshot under concurrent use;
role/global objects require separate capture. It does not require a raw PGDATA
copy or service shutdown. [PostgreSQL 17 pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html),
[pg_dumpall](https://www.postgresql.org/docs/17/app-pg-dumpall.html).

Database bytes were held briefly in bounded remote memory and streamed over the
existing pinned/authenticated SSH connection with selected files. No database
archive was staged on Rivendell's root filesystem. Selected durable-file hashes
were compared before and after the database capture window and remained equal.
Container IDs/start times/configuration also remained equal.

This establishes a transaction-consistent **database** dump plus unchanged
selected filesystem assets across the window. It is not an atomic snapshot of
every live filesystem/database event. Before installation invalidate/refresh the
checkpoint if channels, credentials, profiles, uploads or deployment files change.
Do not rely on it after intervening user configuration changes.

## 3. Verified independent destination

Protected checkpoint on **Denethor**:

```text
/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z
```

Existing secondary disk: `/dev/nvme1n1p1`, Btrfs UUID
`48542bca-0466-4022-95e4-e01a576ffbc0`, mounted read/write outside the execution
sandbox, approximately 787 GiB available at initial check. It is a different
machine/device from Rivendell's root and is not Orthanc's `moria` pool.

The directory is owner-only 0700; archives are 0600. Writes were fsynced and read
back with SHA-256 verification. These local files are protected by filesystem
permissions, **not additional archive encryption**. Preserve those permissions;
never put the archives, dump, environment or JWT/keys in Git or chat.

| Archive | Bytes | Purpose |
|---|---:|---|
| `rivendell-recovery.tar.gz` | 244,987 | Database, role definitions, persistent assets, deployment/security inputs, build context, scoped baseline |
| `runtime-and-rollback.tar.gz` | 16,136 | Generated environment, PostgreSQL config, mirrored host rollback files |
| `source-and-install-plan.tar.gz` | 182,001 | Reviewed custom source, build/relay recipes and installation plan |

Total archive payload: **443,124 bytes**, approximately 433 KiB. Additional small
manifest/validation receipts sit beside them. Complete SHA-256 values are in
`checkpoint-manifest.json`; all member hashes were verified after transfer.

The configured separate Moria UNAS Restic repository at 10.10.10.8 was probed
using its existing private local configuration. The read-only metadata operation
returned repeated backend HTTP 500 errors and was canceled. It is **not verified
as available** for this checkpoint; no repository/credential/timer setting was
changed or backup scope expanded. This is a failed access probe, not a diagnosis
of NAS hardware failure. No repair was attempted.

The NVMe checkpoint is therefore the verified independent recovery copy. It is
not automatically covered by the existing Denethor home-backup job, and no
ongoing schedule or second off-host replica is claimed. Orthanc's degraded pool
and the old VM archive are additional historical evidence, not this destination.

## 4. Installation rollback snapshot

Created on **Rivendell**, with root ownership, directory 0700/files 0600:

```text
/root/dispatcharr-minimal-recovery-20261116T043509Z
```

| File | Bytes | Rollback use |
|---|---:|---|
| `base-compose-before.yaml` | 6,453 | Exact original Compose input |
| `containers-before.json` | 1,626 | Exact original IDs, images, start/health state, restart policies and absence facts |
| `guard-before.json` | 7,090 | Scoped semantic comparison/reference; not global ruleset restore |
| `docker-unit-before.txt` | 1,309 | Original Docker unit/drop-in baseline |

Only **16,478 bytes** of new rollback file content was written on Rivendell.
No large local archive, deployment edit or unit installation occurred. These
files are mirrored in the independent archive. All candidate target files/units
were absent; those absence facts are recorded so rollback removes only files
introduced by the later installation.

The more complete private `rollback-manifest.json` inside the main archive maps
file hashes, UID/GID/modes, containers, images, mounts, parent directories,
network configuration, systemd state and database requirements. Its expected
baseline is the existing base Compose with all three restart policies
`unless-stopped`. Installation must use only the new minimal override, not any
retired controller/cgroup override.

Ordinary persistence rollback does **not** restore a database: retain/reapply the
accepted guard, stop only the dedicated stack, confirm stopped, remove only
introduced units/drop-in, and recreate from the original base while preserving
its data. Use the [Phase 6B-3D rollback sequence](dispatcharr-minimal-persistence-phase6b3d.md),
with `R` set to the root directory above or a fresher approved receipt.
If Docker cannot confirm shutdown, stop/report; do not remove filters or signal
guessed processes. Do not restore unrelated media services or a global ruleset.

## 5. Recovery validation and restore procedure

**Completed nondisruptive validation:**

- Matching PostgreSQL 17.11 `pg_restore --list` parsed the TOC.
- Matching `pg_restore --file=/dev/null` read/decompressed the entire archive and
  generated SQL without connecting to a database. No restore SQL was executed.
- All expected archive member sizes and SHA-256 values matched after SSH transfer.
- Native custom build's six files match their recorded final input hashes.
- Required environment/WireGuard/JWT assets are present; raw live PGDATA is absent.
- Source archive and runtime/rollback archive member hashes passed.
- Protected directory/archive/root-receipt ownership and modes were checked.
- All dedicated and neighboring container IDs/start times were unchanged.

**Not completed:** an actual restored PostgreSQL cluster or running Dispatcharr
acceptance. A matching isolated PostgreSQL 17 server target was not available in
this phase. Denethor has pg_restore 18.6 client tools but no initdb/pg_ctl; no new
server, container, VM or production restore was started to manufacture a test.
Archive readability/SQL generation is not proof that constraints and application
behavior will pass on replay. [PostgreSQL 17 pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).

### Later authorized database recovery — never run against the live database

1. Verify outer and inner hashes; extract only into a new private directory.
   Use the stored ownership inventory; do not blindly overwrite a running bind.
2. Prepare an isolated empty PostgreSQL 17 instance with bootstrap administrator
   `postgres`, no external listener/provider egress and no Dispatcharr workers.
   This role does not conflict with the source's sole application role `dispatch`.
3. With connection variables explicitly set to that isolated local socket,
   restore `roles.sql` using `psql -X -v ON_ERROR_STOP=1 -d postgres -f roles.sql`.
   Set `dispatch`'s password privately from the captured environment using a
   parameterized administrative SQL operation; no password in argv/logs.
4. Restore the database with matching tools:
   `pg_restore --exit-on-error --create --dbname=postgres database.dump`.
   This preserves captured ownership/ACLs. Do not use --clean against production.
5. Verify database owner/role, plpgsql, schema/data counts, migrations and expected
   application records. Review source tablespaces/config before adapting paths.
6. Restore assets/secrets separately using recorded UID/GID/modes. Database files
   must be generated by PostgreSQL, not copied from a live old PGDATA. Preserve
   generated secret values through release-supported environment initialization;
   the saved profile is reference material, not a blindly overwritten executable.
7. Use the original pinned Dispatcharr image and PostgreSQL 17 binaries. Perform
   supported application/worker checks with no providers/streams enabled before
   accepting a recovered deployment. Full recovery requires separate approval.

No image/database migration is part of installing the persistence units. A
catastrophic database restore is an exceptional recovery operation, not the
normal rollback path for this service-ordering change.

## 6. Final state and remaining limits

Post-capture checks: Dispatcharr, dedicated Gluetun and gateway remain healthy;
original Gluetun, qBittorrent and Jellyfin remain healthy; NZBGet remains running.
All IDs, start times and original restart policies match the baseline. Models
and recordings remain empty. Candidate units/directory remain uninstalled.
Root available space is about 7.44 GiB; no large root staging was introduced.

Remaining limits are explicit:

- No full SQL/application restore rehearsal; only matching-version archive decode.
- Only one verified independent checkpoint copy, on Denethor's secondary disk;
  UNAS access failed, and no ongoing Dispatcharr backup schedule was added.
- Local checkpoint archives are owner-protected plaintext, so their private
  directory/permission boundary must be maintained.
- Source/base registry availability is required to reconstruct standard/custom
  images after total image-store loss; image layers were intentionally excluded.
- Refresh/revalidate the checkpoint if configuration changes before installation.
- Existing broader media-backup failure and Orthanc health concerns are unchanged;
  neither is claimed repaired by this scoped checkpoint.

## 7. Recommendation

**GO for the scoped recovery prerequisite for a controlled minimal-persistence
installation, with the restore-test limitation recorded.** The required current
logical dump, durable configuration/secrets, custom source and precise rollback
baseline now exist independently of Rivendell's root filesystem. Installation
still requires explicit authorization and fresh preflight; no unit, rule,
container configuration, Jellyfin setting or streaming deployment was changed.

Private receipts remain in
`.ai-local/dispatcharr-phase6b3f/` on Denethor and beside the independent checkpoint.
This report contains no credentials, keys, role password hashes or private URLs.
