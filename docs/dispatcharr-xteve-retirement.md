# Dispatcharr final verification and xTeVe retirement

2026-11-17 UTC. Rivendell `10.10.20.30`, Andrew's selected access. Running protected release `227122dcbe9ebc76be46b8a91231350d6c93bdb4`; deployment report `779b8388882c0e581ab7bdbc9b1228ca11983bc1`; preceding Jellyfin integration report `8345008099b7db146478e7c3887ba1b17e7ed0ec`.

**PASS with the explicitly permitted persistence-retention exception.** The exact obsolete Jellyfin tuner/provider/mapping are removed. Permanent DW English channel 9001, its guide and all four protected services remain healthy. `/docker/xteve` was **not moved or changed** because a complete directory scan found six unrecorded root-owned empty temporary directories. A verified root-private recovery copy was preserved. No playback test was initiated.

## Playback evidence and post-playback verification

The owner explicitly confirmed successful **interactive Jellyfin picture and audio, fast startup and no buffering**. Those are owner observations. No numerical time-to-picture, client decode, buffering or performance measurement was captured by this retirement task. The earlier headless API-client failure remains historical; it does not override the owner's later interactive success. Earlier preliminary codec metadata is not promoted to independently verified playback metadata.

Fresh checks before removal and final acceptance at **17:11:47 UTC** independently established:

- Four protected services healthy; stack and guard units active/exited with Result=success. Corrected running/security verifier and all **67 installed pins** pass.
- Trusted guard generation unchanged; guard/grant/policy/current namespace coherence passes. Exact nftables policy, VPN tun0 routing, DNS restrictions and disabled IPv6 remain valid.
- PostgreSQL/migration, authenticated Redis, both fresh uWSGI heartbeats and Default/DVR Celery readiness pass. Owned Dispatcharr channel **3** and stream **3** match their ledger and supported API detail records. Binding/exports remain current; no registration or rollback transaction is pending.
- No active Jellyfin playback session, recording or Dispatcharr FFmpeg/FFprobe process after playback ended.
- Relay counters are consistent with additional real media retrieval: **153 fetch attempts, 75 manifests, 78 segments, 197,148,975 bytes**. The prior bounded API attempt ended at 2 attempts/1 manifest/1 segment/2,630,249 bytes. No fatal or rejection state is recorded. These are cumulative counters, not an independently measured viewing duration or startup time.
- Counters were identical before and after retirement: **zero additional fetches during this task**. No media URL was opened.
- Container IDs, configuration/mounts, start times and restart counts, Docker process/network identities and unrelated services remain unchanged. No service reload/restart, image operation, deployment, firewall/VPN change, VM operation or new infrastructure occurred.

## Exact retirement preflight and recovery

The legacy tuner/provider still matched their saved original rows exactly, including URLs at unavailable `10.10.20.30:34400`. There is no listener on that port, no running/stopped xTeVe container, no xTeVe-named Docker volume, no xTeVe-named unit file, and no new reference in the bounded Compose/script/systemd/cron scan. The only active Jellyfin channel was the permanent DW English channel, mapped to the new local provider; it did not depend on the legacy tuner or mapping.

Before mutation, exact Live TV/general configuration, legacy rows/mapping, all container metadata and the complete persistence tree were saved privately under:

`/root/xteve-retirement-20261117/`

The directory is root-private (0700), with recovery/transaction receipts and archive files mode 0600. The recovery tar was created with numeric ownership, ACLs, xattrs and metadata preservation. Every archive member was checked against the source inventory for UID/GID, mode, and file payload SHA-256 without extraction.

| Recovery artifact | Identity |
|---|---|
| Exact configuration before-image | `preflight-private.json`, plus scoped `legacy-recovery-private.json` |
| Verified before/after removal transaction | `remove-intent-private.json`, `remove-verified-private.json` |
| Persistence recovery copy | `/root/xteve-retirement-20261117/xteve-recovery.tar` |
| Recovery tar SHA-256 | `324ae5f4da6acf7e2192172625834475f3d75957384832466e8c02fa26cae771` |
| Source metadata inventory | `recovery-verified.json` and `preflight-private.json` |

Credentials, tokens, source URLs, private configuration contents and raw recovery data are not committed.

## Supported Jellyfin API change

One conflict-checked POST to the supported `/System/Configuration/livetv` endpoint filtered **only** the exact legacy tuner and provider IDs from the current configuration. The fresh before-image matched the recorded working integration configuration. Every other top-level field and permanent row was preserved. The new provider remains first and retains its explicit mapping. No database reset, playback-default change or unrelated API mutation occurred.

Removed:

| Object | Exact identity |
|---|---|
| Legacy xTeVe M3U tuner | `e6c7eb23c33b4be996444b5564611bb2` |
| Legacy xTeVe XMLTV provider | `aaf9c49c3e204ba3a64f23dc19226709` |
| Nested obsolete mapping | `m3u_a7b38ddb7c80f3d2f2e378c282f3b79e0a679898bc5fa863dd0760a60e647840` → `1007` |

The mapping was stored inside the removed provider. No independently stored legacy mapping or occurrence of those identities remains in the active Live TV configuration. No unrelated mapping was removed.

Canonical configuration SHA-256 uses sorted compact JSON:

| Configuration | SHA-256 |
|---|---|
| Before removal | `0ef993273eb4cbb5019926f5fa8387130e4ebc281d39651ef9d534a610b00854` |
| After removal | `133f81220c59c293a50116b5f9d20f8ecd422d0e9b46b0eeab1a63dbe9a09f0b` |

At **17:10:15 UTC**, the existing supported RefreshGuide task completed. Jellyfin has exactly one tuner, one provider and one discovered channel—DW English **9001**, with its labeled availability placeholder. No duplicate appeared. General Jellyfin configuration and unrelated Live TV fields matched their before-images.

Preserved identities:

| Component | Identity |
|---|---|
| Dispatcharr owned channel / stream | **3 / 3**, unchanged |
| Permanent Jellyfin tuner | `84512b75-27af-509d-9377-a29982f9722b` |
| Permanent XMLTV provider | `fa590b78-e345-5343-b34d-9c7b4c5f10db` |
| Jellyfin DW English item | `67d9ed9926f9e1ef90002ff7dbfd790f` |
| Explicit mapping | `m3u_72bdf3377216078a211cff2d20374229c8ace81a7c8cf374c785569d08a13c9e` → `dw-english-permanent` |
| Playlist / guide | `/config/iptv/permanent-dw/current/dispatcharr.m3u` and `guide.xml` |

The XMLTV programme remains **“DW English live stream — placeholder, not a programme schedule.”** No real broadcaster programme listings are claimed. Existing hourly local renewal and 24-hour Jellyfin guide refresh are unchanged.

## Persistence retained under the exception rule

The two known demo files match exactly:

| File | Size | SHA-256 |
|---|---:|---|
| `/docker/xteve/config/demo.m3u` | 125 bytes | `b0ffe31bed0ebd70604aebd4b839f0246a4cfe0c2c6cb3c289193ed875dfa1b9` |
| `/docker/xteve/config/demo.xml` | 328 bytes | `7de3c1eb0b4be95ef29e83f70564b6c16e2fda73099c80941ac059ab831700f8` |

However, the earlier file-only inventory had not recorded these **root:root 0755 empty directories** beneath `/docker/xteve/tmp/`:

- `2026-01-U382-REOD96`
- `2026-05-TIVH-OHJSP7`
- `2026-03-6UW3-E7G6PM`
- `2026-03-W8ZN-VGMUWY`
- `2026-01-VBRQ-6DM0V2`
- `2026-01-7H3O-4KH419`

The main directory, `config`, `demo`, `tmp` and two files are UID/GID 1000; the six nested directories are UID/GID 0. This is an incomplete historical ownership inventory, not proof that those directories were recently created or changed. No permissions or ownership were relaxed to force a match.

Under the task's explicit exception, **the entire `/docker/xteve` tree remains in place**. Recorded UID/GID, modes, mtimes, types, file sizes and hashes are unchanged after retirement. The tar is a recovery **copy**, not a claim that the active persistence path was moved. No permanent deletion, source rename or unidentified-volume removal occurred. A separately reviewed decision is required before moving this broader tree.

Dependency checks covered current Docker metadata, Compose paths declared by containers, the previously selected Docker scripts/configuration paths, systemd and cron locations, and named unit files. Root and murth have no installed crontab. No unknown external automation or unattributed volume was assumed safe to delete.

## Recovery and final decision

For a separately authorized Jellyfin restoration: verify the current Live TV configuration still equals `remove-verified-private.json`'s after-image and the permanent rows are unchanged; refuse conflicting administrative edits. Restore only the two exact saved legacy rows at their prior positions (the mapping is nested in the saved provider), preserving the permanent tuner/provider/mapping. The exact saved before-image is usable only when all unrelated configuration still matches. Verify a fresh API read, then invoke the existing guide refresh. No database/filesystem reset is required. Restoring those obsolete endpoints would restore references to an unavailable service, not make xTeVe operational.

No persistence restoration is presently needed: `/docker/xteve` is unchanged. The verified archive preserves original metadata and payloads if later separately authorized recovery is required. Do not extract over a changed directory or permanently delete the recovery copy.

**Final PASS with documented persistence retention.** Obsolete Jellyfin references are retired; permanent DW English and the four-service protected stack remain operational. The remaining housekeeping item is review of the six unrecorded empty root-owned temporary directories before any future persistence move. The owner-confirmed playback was not repeated, and no new playback/performance claim is made. Stop after publication.
