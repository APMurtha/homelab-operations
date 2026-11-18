# Original Dispatcharr restoration results

**NO-GO: stopped during preflight before installation or managed startup.** The approved diagnostic candidate cannot retain receipts at its configured path under the actual `/docker` permissions. Installed files: **0**. Managed starts: **0**. All four IPTV containers remain stopped. Recovery is not complete.

## Authorization and provenance

The owner authorized only the three-file diagnostic patch at `50bdb437b57d84b9f74237db04d862c12fa24424` and one managed restoration start. Exclusive administration was confirmed. NEST access selected Andrew's `andrew-media` system and `media` SSH profile; hostname `rivendell` and login UID1000 were verified before root inspection. Hardening work remained suspended.

Fresh observations were collected on 2026-11-18, 22:16–22:21 UTC. [Sanitized machine-readable evidence](../configs/dispatcharr-iptv/original-stack-restoration-results.json) retains the refusal, directory metadata, 33 container fingerprints, preservation comparisons and final protection checks. Private administrative receipts are retained under `/root/dispatcharr-original-restoration-20261118T221609Z`; historical receipts were not cleared.

## Exact preflight blocker

At 22:16:11 UTC the read-only preflight rejected the diagnostic receipt ancestry with `receipt_ancestor_unsafe`. The same rule in the approved candidate's `lifecycle._private_dir()` raises `diagnostic_ancestor_unsafe`: it requires `ROOT` and **every ancestor** to be a root:root directory without group/world write access.

| Path | UID:GID | Mode | Candidate ancestor rule |
| --- | --- | --- | --- |
| `/` | 0:0 | 0755 | Pass |
| `/docker` | **1000:988** | **0770** | **Fail** |
| `/docker/dispatcharr-iptv` | 0:0 | 0755 | Pass |
| `/docker/dispatcharr-iptv/private` | 0:0 | 0700 | Pass |
| `/docker/dispatcharr-iptv/private/backend-diagnostics` | Absent | — | Not created |

The missing child directory is expected before installation; the unsafe ancestor is the blocking incompatibility. Precreating the child would not fix the full-chain check. The candidate's offline integrity check passes, but does not establish real host-path compatibility. Its strict check was preserved; neither shared `/docker` permissions nor candidate code/hashes were altered.

This finding does **not** establish the cause of the earlier backend exit code 1, or demonstrate new production drift. That backend failure remains unclassified because no new backend invocation occurred.

## Source verification and installation status

All 67 original installed targets still match the verified original baseline, including root:root 0644 ownership/modes. The local candidate/original inventory and manifest-closure verifier returned `PASS_OFFLINE_CANDIDATE_ONLY` (three originals, three proposed replacements and 64 unchanged targets).

| File | Still-installed original SHA-256 | Approved candidate SHA-256; not installed |
| --- | --- | --- |
| `backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` |
| `lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` | `171530848e5623b3ab3a578798c83d3991b1299798202f544fc70fd92a26bc8f` |
| `manifest.json` | `9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c` | `1eb1a2b68e564b56cc105b31eb6281b610cf0e1f3684fea9246fd02eaabcc8f5` |

No rollback installation was needed: none of the three originals was replaced. No systemd lifecycle command, container lifecycle operation, Compose application, database/Redis change or application API mutation occurred.

## Recovery and incomplete gates

The independent Denethor checkpoint was freshly rehashed:

- Path: `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`.
- SHA-256: `ce8e254f78972dd7b1a14012e3a5b2cbc9c8c9fa506054b1e920ad8dc4d3deb7`; 236147 bytes.
- Archive mode0600, containing directory0700, UID1000.

The matching Rivendell archive recorded previously is `/root/dispatcharr-hardening-20261118T201302Z/recovery.tar.gz`. Its fresh source-side rehash was **not reached** in this preflight. No archive was extracted or restored.

Fresh CPU/memory/disk admission, local image-store verification and the remaining private-state/credential gates were also not completed after the ancestry refusal. This is a receipt-path failure, not a resource-admission failure. Stopped AIO metadata still references original image `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`; that observation alone does not prove current image-store availability.

## Backend stages and restoration acceptance

| Stage | Result |
| --- | --- |
| Pinned application sources | Not run |
| PostgreSQL and migration fingerprint | Not run |
| Authenticated Redis | Not run |
| Two fresh uWSGI witnesses | Not run |
| Default/DVR Celery responses | Not run |
| Managed registration/export rebind | Not run |
| Running application, gateway and Jellyfin channel discovery acceptance | Not run |

No same-invocation backend diagnostic receipt exists for this task. Existing DW English ownership files remain present; stopped-state file preservation is not fresh API verification or a restored binding.

## Final preservation and security

At 22:17:24 UTC, all 33 container IDs, images, start timestamps, restart counts, health/status fields and configuration fingerprints matched the prior incident baseline. All four IPTV containers remained exited, with retained unhealthy health fields. Jellyfin remained running/healthy. The other 29 container records were unchanged, including historical exited containers; this does not claim all unrelated containers are running or healthy. Docker process, networks and volume comparisons remained unchanged.

The final 22:21:28 UTC check confirmed exact kernel nftables policy, withdrawn public guard/grant assertions, empty provider projection, and guard transaction `phase=revoked`, `blocked=false`. Ownership-state directory entries remained only `lock` and `owned.json`, with no pending transaction file. The candidate diagnostic directory remained absent. No provider activation, external provider request, playback or Jellyfin configuration change occurred.

## Required next step

**NO-GO for declaring recovery complete or starting this candidate.** The smallest proposed correction is a separately reviewed offline diagnostic candidate retaining receipts beneath an independent root-private path, such as `/root/dispatcharr-backend-diagnostics`, with strict validation of that receipt path's own ancestor chain. It must preserve all readiness predicates, timeouts, scoped cleanup and bounded/redacted diagnostics, and update the matched inventory/hashes deliberately.

Do not change shared `/docker` ownership/permissions or weaken ancestry checks to force this candidate through. No such correction was implemented here. A corrected, reviewed candidate and separate installation/start authorization are required, followed by a complete fresh preflight. The original backend failure still requires evidence from that future invocation. Hardening deployment remains suspended.
