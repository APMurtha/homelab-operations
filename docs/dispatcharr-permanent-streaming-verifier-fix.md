# Dispatcharr permanent-streaming verifier correction

2026-11-17 UTC. Andrew’s Rivendell (`10.10.20.30`). Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.

**Offline correction PASS. GO to review/authorize the corrected candidate for a new bounded deployment; NO-GO for deployment under the previous candidate approval or for Jellyfin integration/playback.** Publication is the endpoint of this task. No server connection, container operation, API call, installation, systemd reload or production configuration change occurred.

Original candidate: `f7115a8339685ba3e5314d8e54a40f239c5e3723`. Correction is based on the failure report at `18bdf54fe9e0d0c431a2c61f930f911285a31106`, which remains unchanged as historical evidence. The commit containing this report and the candidate is the new review identity; do not deploy `f7115a8` again.

## Root cause and exact correction

The failed deployment’s newly created stopped relay correctly had exactly six bind mounts in Docker `Mounts`, with `/tmp` specified instead in `HostConfig.Tmpfs`. The original verifier required `/tmp` in `Mounts` unconditionally and never verified its tmpfs options. Its Compose-derived fixture represented every container as running, with a tmpfs entry already present, so it missed the real stopped representation. Running the original verifier against the corrected stopped fixture reproduces `unexpected_relay_mount`; the corrected verifier accepts that same fixture.

`contracts.py` now requires this exact map in every lifecycle state:

```json
{"/tmp":"rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700"}
```

The six bind destinations are checked independently: `/opt/permanent`, `/etc/resolv.conf`, `/guard` and `/run/credentials/relay.json` retain exact sources and read-only status; `/runtime` and `/exports` retain their exact sources and writable status. No extra bind or volume is accepted. Bind propagation must remain private. Duplicate destinations are rejected before building the mount index (including protected mounts of the other dedicated services); a later duplicate cannot conceal an earlier unsafe mount.

For a stopped relay, `/tmp` may be absent from `Mounts`, matching the failed creation, or present as a safe tmpfs entry retained from a prior run. For a running relay it must be present. Whenever present it must have type `tmpfs`, be writable, have no host source, and have no unexpected Mode/Propagation. The exact size, UID/GID, mode and nosuid/nodev/noexec options are always enforced through `HostConfig.Tmpfs`; omission from stopped `Mounts` never exempts that check. Missing, altered or additional tmpfs configuration fails closed.

Existing UID/GID 1000 execution, read-only root filesystem/source mounts, capabilities, no-new-privileges, VPN-owner namespace, published-port restrictions, 256 MiB memory/swap, 0.5 CPU and 64-PID restrictions remain enforced. File ownership/private-credential permission verification remains byte-for-byte unchanged in `verify.py`.

## Diagnostic inventory correction

The failed deployment used an ad hoc diagnostic helper with the original three-name exclusion list. That helper was outside the committed candidate. The correction adds a reusable `diagnostic_inventory.py` and documents its use for future before/after snapshots instead of modifying the installed three-service baseline verifier.

It derives its exclusion set from the existing four-service `contracts.NAMES`, exactly:

- `rivendell-iptv-vpn`
- `dispatcharr`
- `rivendell-iptv-relay`
- `rivendell-iptv-gateway`

The comparator accepts the private snapshot schema used by the prior deployment, reads local JSON only, and prints value-free results. It requires the same genuinely unrelated container set, IDs, image IDs, HostConfig hashes, start times, running/health state, restart policy and restart count; Docker process and both network identity records must also match. Missing fields, duplicate names, newly added/removed unrelated services or any changed comparison field fail closed. Similar names such as `relay` or `rivendell-iptv-relay-extra` remain unrelated. This is stricter than the old helper’s health-regression-only comparison; no unrelated identity/configuration check was removed.

## Changed-file inventory and SHA-256

Paths below are relative to `configs/dispatcharr-iptv/permanent-streaming/`. The exhaustive comparison against `f7115a8` found only these nine candidate files changed/added, with no deletions. This new report is the sole additional documentation file in the correction commit; its own digest is not self-embedded.

| File | SHA-256 | Reason |
|---|---|---|
| `README.md` | `f3bbfb404331c95af9a7e5be9c3e1a75d24ea9c0c00caa689af84675fb42f779` | Document lifecycle-aware mount checks and the four-name diagnostic comparator. |
| `contracts.py` | `71da7561a97b279a058f1fe65477ab76864307cc4327ad487d061367ae9fc038` | Validate exact HostConfig.Tmpfs, six binds and lifecycle-specific tmpfs enumeration; reject duplicate targets and unsafe bind propagation. |
| `diagnostic_inventory.py` | `2e83b5e7a11f247ed7d8e382c64f62375aa4086ce517629c052be8b08ff16126` | New read-only offline snapshot comparator; exclude exactly four dedicated names and strictly compare unrelated records, Docker and networks. |
| `manifest.json` | `3d5ae000603fc8d3bf7796deb996c39f863ab877f45160edd22ebf9a65648ae4` | Update only four changed source/test entries and add three correction-specific files; retain every other original entry. |
| `validation-results.json` | `70bebbb697b3804c238cd45f0309ddd5a0ff518b3e2a3c3fa124afebc011f5a5` | Record this correction’s 157 offline tests and distinguish prior live checks from checks not repeated here. |
| `tests/run-offline.sh` | `369749fc567eb1545729a56d8a39ca11f33d92ebfb14dab336020cdd9efdd9b5` | Add the diagnostic inventory regression suite to the existing offline runner. |
| `tests/test_contract.py` | `1a1fa266cce482175113ff8ce35fd9cccc92a4f2e56bc923c9522347dad35a9f` | Model HostConfig.Tmpfs and stopped state correctly; add seven lifecycle/security regressions. |
| `tests/test_inventory.py` | `535c0427773fa268aa26a6ef5d35d7e02ecfeb1bff6fbaf10c5cbbd4ac2caf79` | Seven new diagnostic scope and strict-identity regressions. |
| `tests/fixtures/relay-stopped-18bdf54.json` | `cbd455cfa1797347362e0a96244886398ea3388e59a013cd7a315bf59cbd884c` | Sanitized projection of the mount facts recorded in the failed deployment report; no secrets or full raw inspect. |

The runtime manifest now has **42 entries**: the original 39 plus three narrowly scoped additions. Four original entry hashes changed, and the other 35 are identical. Manifest updates were allowlisted and audited against the original commit before hashing; the broad refresh script was not used. As before, `manifest.json` and `validation-results.json` are excluded from the runtime manifest; their digests appear above.

All remaining candidate files are byte-identical to `f7115a8`, including `compose.yaml`, image pins, `verify.py`, API source pins, relay/fetch/DNS/TLS/HLS code and request budget, registrar/API behavior, gateway routing, exports/Jellyfin helpers, firewall template, lifecycle code and the systemd drop-in. Existing persistence/admission source outside the candidate is unchanged. The existing deployment report’s earlier historical differences from `f7115a8` predate this correction and are not changes made by this task.

The approved image references remain:

- Dispatcharr and relay: `local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`
- VPN: `qmcgaw/gluetun@sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209`
- Gateway: `caddy:2-alpine@sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9`

## Regression evidence and complete results

`tests/fixtures/relay-stopped-18bdf54.json` is an allowlisted projection of the actual stopped mount facts documented in the failure report, not a full raw Docker inspect export. It records six bind destinations/sources/access modes and the exact tmpfs map; no credentials, private broadcaster URL, opaque endpoint or recovery data is included. Other container state remains synthetic and Compose-derived. Running metadata is a synthetic fixture, not a new observation from a deployed relay.

Added regressions cover stopped acceptance using that projection, running acceptance, safe retained stopped tmpfs enumeration, missing/altered/extra tmpfs options, missing or unsafe running tmpfs, unexpected/missing/duplicate mounts, bind source/access/propagation changes, incorrect namespace, every relay resource bound and privilege/user restriction. Inventory regressions prove exact four-name exclusion, strict unrelated comparisons for every field, unrelated additions/removals, duplicate/malformed names, missing fields and Docker/network changes.

| Offline suite | Tests | Result |
|---|---:|---|
| Existing candidate policy, registration, exports, Jellyfin and lifecycle fixtures | 39 | PASS |
| Four-service security/mount contract | 16 | PASS |
| Four-service diagnostic inventory | 7 | PASS |
| Trial provenance and complete manifest | 3 | PASS |
| Existing minimal persistence | 12 | PASS |
| Existing boot admission | 28 | PASS |
| Isolated TLS/DNS/lifecycle/resource fixtures | 11 | PASS |
| Pinned native Caddy groups | 15 | PASS |
| Historical persistence controller (separate runner) | 26 | PASS |
| **Total** | **157** | **0 failures/errors/skips** |

Native `systemd-analyze verify` passed against temporary offline unit/dependency fixtures; no service manager was changed and no service executed. The isolated network fixtures used only loopback plus synthetic `93.184.216.34`, with no external interface/default route. The previously retained Caddy binary SHA-256 is `a563843e11cbce39c557bd429ebb787d56f49d51d9bbb3292cd9b36b37a60cdf`; all **91 synthetic requests** passed and external network availability was false. No binary download/build/pull was performed.

The first sandboxed run passed its Python suites but could not complete the native syntax fixture under sandbox restrictions. The complete runner then passed outside that sandbox with only local synthetic fixtures; the final run includes the additional private-bind-propagation check. Python emitted its existing multithreaded-fork deprecation warning in the synthetic multiprocessing test; all cases completed successfully.

Reproduce with:

```sh
CADDY_TEST_BINARY=/path/to/verified/caddy sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh
python3 -B -m unittest discover -s configs/dispatcharr-iptv/persistence-phase6b3/tests
```

No production source/API/credential compatibility or live Compose inspection was repeated in this offline task. Recorded prior live checks are not presented as new results in `validation-results.json`.

## Remaining prerequisites and decision

Before a separately authorized deployment, review/pin this correction commit and repeat the entire fresh health, idle-state, image availability, nine installed file hashes, recovery, security, credential/ACL and conflict preflight. Reconfirm Default Group ID **2**, locked streamcopy profile **1**, Jellyfin peer **172.20.0.2** and canonical ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e`.

The failed candidate’s source/private configuration remains staged but inactive according to the last verified rollback state. Future installation must explicitly reconcile those retained files with the newly approved source manifest and current private schemas/values; do not silently treat the old staged directory as corrected. Preserve the existing VPN owner, original accepted base files, guard/admission thresholds and safe scoped rollback. Use the new diagnostic comparator with fresh private snapshots. Stopped and running real-metadata acceptance is still required in the next bounded deployment; offline fixtures do not prove that installed runtime.

The last production verification in `18bdf54` left the original protected three-service stack healthy after safe rollback. This correction made no server contact and leaves that deployment untouched; no fresh production health claim is made. No API writes, media fetches, playback, Jellyfin changes, infrastructure operations or recovery exercise occurred.

**GO for review and separate deployment authorization of the corrected candidate. No deployment was attempted; no authorization for another stop/start cycle is inferred. Stop after publication.**
