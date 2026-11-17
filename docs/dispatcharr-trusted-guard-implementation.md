# Dispatcharr trusted guard lifecycle implementation

2026-11-17 UTC. Andrew’s Rivendell (`10.10.20.30`). Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.

**Offline implementation PASS. GO for review of the matched release and separate controlled-deployment authorization; this task does not authorize installation.** All **199 baseline tests plus 52 new regressions pass: 251 total**. Both original-three and permanent-four native unit syntax/dependency fixtures pass. No production connection, filesystem/configuration change, container operation, real nftables/DNS/VPN operation, application API write, Jellyfin change, image operation or playback occurred. The last verified production state remains the original healthy three-service deployment in `38855f7`; no fresh live-health claim is made.

Approved design: `ee7ec3e824fbf4c606fa64b92706225616dd57eb`; prior permanent candidate: `776f9843228148fe3d1fd744089f97fb0c82601e`. The containing commit is the new coordinated review identity. Do not install this as an isolated relay patch or treat the old candidate approval as approval of the new protected baseline.

## Implemented architecture and trusted writer

The architecture remains the existing VPN owner → patched AIO + unprivileged HLS relay → gateway, with the same images, networks, ports, application APIs and media path. Only readiness publication/consumption and managed ordering change.

`guard.py` now provides a serialized root-private writer protocol:

- Private `/run/dispatcharr-guard` must remain root:root **0700**. It holds the original digest `ready` (root:root 0644), a regular single-link writer lock, anchor identity, transaction and stopped-owner intent (root:root 0600). Existing unsafe permissions are refused, never chmod/chowned to make them pass.
- Public `/run/dispatcharr-guard-status` is root:root **0755** and contains **only** `guard.json` and `grant.json`, root:root 0644. No policy, WireGuard values, source URL, credentials or privileged control file is exposed.
- `guard.json` has exactly schema=1, host boot UUID, fresh cryptographic 256-bit generation G and expected policy SHA-256. `grant.json` adds only namespace device/inode. The owner ID and Config/HostConfig hashes remain private.
- Every apply/revoke/grant API takes the same private `flock`. Lock/metadata ownership, modes, regular-file type and link counts are verified. Atomic files are staged under the private directory, fsynced and renamed onto the same filesystem; parent directories are synced. No status file descriptor is retained as authorization.
- Revocation attempts every assertion/intent/legacy withdrawal and records failure even if one removal fails. It does not remove kernel rules. Unreadable/corrupt private transaction metadata is retained and cannot prevent attempting public unlink; it then blocks further mutation.
- Apply withdraws **before** policy and WireGuard validation. It retains the original nft syntax/apply transaction and exact accepted table semantics, then uses the existing pure semantic verifier to read back the table before any public publication. Legacy digest publication remains compatible with original root startup gates. G changes even with identical policy.
- Transaction phases are revoked → applying → publishing → applied → granting → granted. A crash/failed operation in applying/publishing/granting latches blocked=true during cleanup, preserving interrupted phase/generation. A later apply refuses. No automatic latch-reset/retry command is shipped; reconciliation or whole-baseline rollback needs explicit review.
- Mutating operations require root and the exact cgroup of the existing guard/stack units; grants/owner capture require the stack unit. Environment variables are not used as authority. Unsupported root mutation attempts withdraw before refusal where possible; this is fail-closed behavior, not an access-control defense against trusted root.

The anchor is initialized only for an empty public directory with no prior protocol transaction/owner metadata. A missing anchor alongside existing protocol state, changed inode/boot metadata, unexpected file, symlink or populated unknown directory is refused. Normal stops preserve the directory inode. Exceptional replacement must withdraw through the old anchor and stop all readers first; no silent adoption or populated rename is implemented.

## Namespace grant and managed startup

`lifecycle.prepare` first runs the stopped four-service contract and records the exact existing stopped VPN owner ID, immutable image, Config/HostConfig hashes, network ID and current G privately. Startup then:

1. Start/wait **VPN owner only**, with the existing no-build/no-pull/no-recreate options.
2. Under the trusted writer lock, verify current guard/private/public coherence and exact kernel table; compare the running owner with the stopped-owner intent and immutable image.
3. Verify healthy/running owner, exact network ID/name/bridge membership and IPv4 address, tun0 default routing, OUTPUT DROP/embedded-DNS rejection, loopback resolver, all/default IPv6 disabled, pinned image’s local healthcheck, namespace different from host, then re-read owner/namespace and guard before publication.
4. Publish matching grant. A namespace inode alone is never sufficient; missing or changed owner intent/security evidence refuses and withdraws public readiness.
5. Start/wait patched AIO + relay with `--no-deps`; run existing backend gate, supported-API owned-channel registration and export verification; start gateway last.
6. Running acceptance retains all original image/source/namespace/mount/resource/VPN checks and correlates current trusted G/grant, actual owner namespace and relay stats G before binding acceptance.

Grant publication attests observations at that time. It is not a continuous Docker-owner or kernel monitor. Original API registration, uncertain-write journal/rollback semantics, streamcopy profile, M3U/XMLTV behavior and gateway routing remain unchanged.

## Unprivileged reader and unchanged security controls

New `guard_readiness.py` performs bounded current-path lookups through the **read-only directory bind** at `/guard-status`. It enforces exact root ownership/modes, regular single-link status files, no-follow/nonblocking file opens (including FIFO refusal), at most two approved filenames, <=2048-byte JSON records, no duplicate/extra fields, exact integer schema, canonical boot UUID, 64-character hex digests/generations and positive integer namespace fields. Directory identity is pinned too.

At bootstrap it pins G/grant for that process lifetime. Every check reads guard → grant → guard, rejects inconsistency/change, compares actual host boot and configured policy digest, and matches `/proc/self/ns/net`. No new G is adopted by a running relay. `Relay.check()` invokes this reader at the existing startup/resource/fetch/health/state-writer boundaries; pinned G is included in stats. Revocation latches failure and uses the existing stop/cancel/endpoint-removal path.

Compose replaces **only** relay’s obsolete read-only private `/guard` bind with `/run/dispatcharr-guard-status:/guard-status:ro`. The other five bind mounts, exact tmpfs, readonly root/source/config, UID/GID 1000, no capabilities, no-new-privileges, 0.5 CPU, 256 MiB memory/swap, 64 PIDs, namespace and published-port restrictions are retained. Corrected stopped/running tmpfs contracts remain in effect. The original AIO/VPN private guard mounts/gates are unchanged.

The 120-attempt/60-second rolling budget, four fetch slots, TLS/DNS/destination/redirect/HLS enforcement, 12-second deadlines and existing size/resource/telemetry bounds are unchanged. AST provenance still compares every previously unchanged security method except the deliberately replaced `check()`; that new boundary is covered by actual publisher/reader tests. Original trial reference bytes are not rewritten.

## Systemd integration and original-three compatibility

A new guard-unit **20-trusted-readiness.conf** preserves the public RuntimeDirectory across stops/restarts at mode 0755, inserts fixed-path withdrawal **before** source verification, and adds stop/failure revocation. The original guard base unit is unchanged. The effective stack **20** and candidate **30** lists likewise withdraw before inputs/admission, preserve inputs → unchanged admission → guard apply ordering, and retain original timeouts/dependencies/restart policies.

Fixed-path coreutils withdrawal is a manager-ordered, denial-only backstop that can run even if publisher code cannot start. It relies on the supported unit/exclusive-administration ordering; it is not a separate concurrent publication API. The normal writer operations are serialized by the private lock.

One small addition beyond the design’s file list is **minimal-phase6b3d/cleanup.py**: an original-three one-shot cleanup aggregator. It attempts guard withdrawal, the exact original scoped Compose stop, and withdrawal verification even after an individual error/timeout, then reports failure. This avoids silently ignoring a failed revoke or skipping the container stop when changed guard code cannot run. Candidate `lifecycle.stop` has the same attempt-all/fail-if-any behavior. An initial unit-level ignored coreutils unlink only permits cleanup to continue; it is not used as proof of successful withdrawal.

Original root AIO/VPN gates still receive the exact private digest + newline. Original three-service startup needs no relay grant; full semantic/public guard coherence remains required. The base stack/guard/Docker-order units, base Compose/persistence overlay, nftables template, security.py, admit.py and all image pins remain byte-identical. Of the original nine installed persistence/admission files, only the minimal verifier and 20 drop-in change; new cleanup and guard-unit drop-in add two protected paths. Guard.py changes separately in its source contract. Retired controller/source pins remain deliberately old and refuse the new guard.

All four images are unchanged: VPN `a2d964…2209`, patched AIO/relay `14c837…cad21`, gateway `78bd35…ade9`; original rollback AIO remains `96bc54…1d236`.

## Demonstrated tests and accepted limits

| Suite | Tests | Result |
|---|---:|---|
| Candidate policy/API saga/export/lifecycle cases | 39 | PASS |
| Stopped/running four-service security contracts | 16 | PASS |
| Strict unrelated-container inventory | 7 | PASS |
| Provenance/complete source manifest | 3 | PASS |
| Original minimal persistence | 12 | PASS |
| Boot admission and effective unit order | 28 | PASS |
| Actual trusted publisher/UID/reader/crash/cleanup/release tests | 50 | PASS |
| Isolated TLS/DNS/resources/active-fetch revocation | 13 | PASS |
| Pinned native Caddy groups | 15 | PASS |
| Historical persistence controller | 26 | PASS |
| Preserved historical guard-interface counterexamples | 14 | PASS |
| Approved lifecycle design model | 28 | PASS |
| **Total** | **251** | **0 failures/errors/skips** |

The original 199 cases are preserved, with expected pin/order/interface fixtures updated deliberately; 50 actual tests plus two network regressions are new. The 14 historical counterexamples now run against exact SHA-pinned original guard/776f984 relay/wrapper copies, rather than accidentally testing new code while asserting old behavior. Those references are test-only and absent from installed-file mapping. Actual implementation tests separately exercise the new writer, not the design model.

Real filesystem semantics use private tmpfs and readonly bind mounts in mapped user/mount/network namespaces. Real UID/GID 1000 has no supplementary groups/effective capabilities. Tests cover private traversal denial, valid publication/startup, fresh generations, unsafe files/ownership/FIFO/links/fields, early policy/WireGuard and late nft/readback failure, wrong owner/config/network/route/DNS/IPv6/health, incomplete/corrupt private state, anchor rules, publication/unlink failure, and six real SIGKILL boundary phases. The full actual relay starts unprivileged without media requests and exits/removes its endpoint after revocation. A delayed synthetic TLS fetch is rejected after revocation before returning media.

nft execution and Docker inspection/health are mocked; managed context is injected only in those mutation fixtures and the real cgroup checker is independently tested to refuse the fixture. Host-initial namespace identity is synthetic where namespace permissions prevent inspecting PID 1; reader namespace identities are real, and the preserved model tests also enter a genuinely different network namespace. Source/transition pin consistency and legacy marker compatibility are checked.

Both original-three and permanent-four **native systemd-analyze syntax/dependency fixtures pass**; no real unit was started/reloaded. Cleanup command failures/timeouts are control-flow fixtures, not a claim about a live manager. No real systemd manager/PID 1 was killed: manager absence/recovery is represented by deferred cleanup after synthetic publisher crashes. Native Caddy passes 91 synthetic requests with external networking unavailable. The pre-existing multiprocessing fork deprecation warning is non-fatal. No package/image was installed/downloaded/built.

Accepted design limitations remain explicit:

- A crash before the first withdrawal can leave old readiness until manager cleanup; a completed check cannot recall its issued decision. Tests demonstrate both windows.
- A crash after public commit but before successful process exit needs manager cleanup. Exception/finally handlers do not handle SIGKILL; they are not a substitute for unit hooks.
- If every public unlink fails, an old reader can still accept until protected processes stop. Cleanup reports failure and attempts scoped stop; it does not claim synchronous revocation. Failed stopping/uncertain state blocks further attempts.
- A populated public directory renamed by privileged code outside the trusted protocol can remain visible through an old bind. The protocol forbids that sequence; metadata mismatch prevents new publication, not retroactive discovery by the old mount.
- Existing two-second checks and 12-second deadlines are not guaranteed shutdown wall-clock bounds under CPU/I/O stalls. Already transmitted/buffered data cannot be recalled.
- A readiness record and cached grant do not continuously prove kernel enforcement, VPN-owner survival or current routing. Existing kernel/VPN protection and fresh host acceptance remain independent requirements.

## Complete matched release and exact changed hashes

The non-executable [transition manifest](../configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json) records **65 installed target paths**, their exact sources/SHA-256/root:root 0644 modes, **44** expected previous staged candidate hashes, **17** accepted original-production hashes, new directory mode and private-schema migration. It contains no secret/private runtime values. It is a review/verification map, not an installer or authorization.

The candidate has **43** manifest entries plus manifest/validation receipt = **45 source files**. The only new candidate entry is guard_readiness.py. Every changed entry corresponds to a specifically reviewed changed source; other candidate bytes and all accepted image/security-policy/admission-helper identities remain unchanged. Packaging manifests update only actual reviewed code/tests/documentation/results. No production-derived regeneration or unexplained drift is accepted.

All paths below are relative to `configs/dispatcharr-iptv/`. This exhaustive inventory is relative to approved design commit ee7ec3e; this report itself is the sole additional file not self-hashed.

| Changed/added file | SHA-256 | Reason |
|---|---|---|
| `PERSISTENCE-STATUS.md` | `b82f4f0746da7fcd0d879d403e5ef75fbcd1b2ba08658c38bde7d0755379332b` | Clarify offline matched transition; production not installed. |
| `guard.py` | `d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0` | Trusted writer, anchor/transaction protocol, managed context, semantic readback and verified owner grant. |
| `boot-admission-phase6b3k/20-resource-admission.conf` | `578e03101e64c14da217e3d77f5bed9e0dbfbab9dad24b3f077c6b3891aed023` | Early fixed withdrawal and scoped cleanup; unchanged CPU helper/thresholds/timeouts. |
| `boot-admission-phase6b3k/README.md` | `9f3297e932bd70f172bc510f9365a559f717015cbb850014d6a240d3baef9f33` | Document effective baseline transition. |
| `boot-admission-phase6b3k/artifact-hashes.json` | `da9215bf441a218e40f120eacb00c9a1ef79eac32e045461553892ffd4c17fc1` | Reviewed changed 20/documentation/test package hashes only. |
| `boot-admission-phase6b3k/tests/test_admit.py` | `8eddc5fa13ce65bc15fb009bb43303924921e8c6000995e1268f943f2ef0d165` | Adapt exact expected hook order/cleanup while retaining all 28 cases. |
| `boot-admission-phase6b3k/tests/verify_units.py` | `b53509af6c446d1525fa46613336944be9a89ae6de41314f6067c04d7c715d3c` | Include new guard drop-in in native original-three fixture. |
| `guard-interface-review/reference/guard_accepted.py` | `df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd` | Exact accepted original guard, historical tests only; never installed. |
| `guard-interface-review/reference/relay_776f984.py` | `5eb958dbcf1ef6d2b92fa47ba4fb737511042486601969b955f7940241fb4b36` | Exact 776f984 relay for preserved historical counterexamples, not deployed. |
| `guard-interface-review/reference/relay_main_776f984.py` | `b273dd21d1ea8a89010a7304138046d7426c61a98d8aaeb0be3188cd38e69473` | Exact 776f984 wrapper for preserved historical experiments, not deployed. |
| `guard-interface-review/test_feasibility.py` | `73b86b8f88af019f0aafe7bf72a9bd32319bc494fecc7feb5859f7984820ffb1` | Bind the same 14 historical cases to pinned old implementation references. |
| `minimal-phase6b3d/README.md` | `5cbd68c3824bc4fb01ae6c03604f020f6dba2332dd9ea74d0f0fb6eea04ee3dd` | Document coordinated protected baseline. |
| `minimal-phase6b3d/artifact-hashes.json` | `db849dd60a6a3ffda72ec2d8a222ff9aea78c9bd2e7cb758adff3455851860e5` | Pin new cleanup/drop-in and changed verifier/tests/docs/results. |
| `minimal-phase6b3d/cleanup.py` | `bb1f7166cb6adeec352abdd2eccb21365c8ae61ff7892a0da028e4c1fee71432` | New one-shot original-three cleanup that attempts all actions and retains failure. |
| `minimal-phase6b3d/tests/test_minimal.py` | `595c943bdcc573c8b9375f87cf61729721c2f0066ca4abdb9e259fc0c05a4abc` | Update only the reviewed guard source-pin expectation; 12 cases retained. |
| `minimal-phase6b3d/units/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf` | `392994ee3a0eec4b87127b13aa1efb51ce058fd135fbbed52f17d30fde2dbefc` | Stable public runtime directory and early/stop/failure withdrawal. |
| `minimal-phase6b3d/validation-results.json` | `b5bd3619e53bdb2afb642834e0a6b98e9b45136663e4844fc629ef57eb71bdca` | Record offline transition validation. |
| `minimal-phase6b3d/verify.py` | `a809936e8b31c265c00738d60d24064578b32c255759f16151a048cb95408de7` | New approved source/unit pins, semantic-only mode and public/private coherence. |
| `permanent-streaming/30-permanent-streaming.conf` | `55ed3a21aec684c70b0599be358a915d2b91ffdfe088bee7a338e1774ce1a1c9` | Early and stop/failure withdrawal before managed lifecycle commands. |
| `permanent-streaming/README.md` | `cee2b638b746340f45fea72fdfc1c52700f645341bee6eb42b72767d7d9203e0` | Replace obsolete independent-install plan with coordinated install/rollback. |
| `permanent-streaming/base-input-pins.json` | `425ebd00cbae9c21180037d404cf38a1bba2c419145d77beafda4029bdf48227` | Match changed guard/minimal verifier and new cleanup source. |
| `permanent-streaming/compose.yaml` | `3f1993c109a9e9e18a0da04616e3a09dd3a132c478f57af15cd99cceef2c27de` | Replace ONLY relay private guard bind with read-only public directory bind. |
| `permanent-streaming/contracts.py` | `2cfd3e900d5f91b00e95e3e576142ea15d46af56f4acd11f0ebb714dc032249e` | Require exact public relay mount; all other restrictions retained. |
| `permanent-streaming/guard_readiness.py` | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` | New bounded strict reader with lifetime-pinned generation and real namespace checks. |
| `permanent-streaming/hls_relay.py` | `171461eb4bb83170a83d4b52aeca90d3f7ebc5d8486b615cdf654b7fc98078f5` | Use trusted reader at existing checks; add pinned generation to stats only. |
| `permanent-streaming/lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` | Capture stopped owner; start VPN, verify/grant, then AIO+relay; robust scoped cleanup. |
| `permanent-streaming/manifest.json` | `797dcdd7230efb89c2d133443c6d6e4371700e567299744f54d4245fc7d42a69` | Exact changed/new candidate source hashes; no unrelated drift. |
| `permanent-streaming/relay-config.schema.json` | `94cf3990b3e8f3d6237f7ef09f832b01b12f3fe8c8d529c44662e4b12076cf8b` | Migrate ready_file to guard_status_dir, all other private fields preserved. |
| `permanent-streaming/relay_main.py` | `830c87685643af37b9f008640b457d1a4e77bdf1fdef554f36fd82cec589f356` | Accept migrated interface field; existing startup/state writer remains. |
| `permanent-streaming/tests/run-offline.sh` | `238ed027c00afe6c52e0c42294e305259f42dba5fc2ff2335ef5222f9101823d` | Include actual trusted-guard implementation suite. |
| `permanent-streaming/tests/test_candidate.py` | `45e13af50ad9e76abd6f52cbd940ce6033831aa0622089851b09ad944441fdba` | Adapt readiness and lifecycle fixtures; retain all original policy/API cases. |
| `permanent-streaming/tests/test_contract.py` | `1cfcaed0882b06dae1ce7f2f48f8b8ca7ab64c277a8f694c289ef5b840ba2082` | Project historical stopped mounts onto new exact interface; retain stopped/running negatives. |
| `permanent-streaming/tests/test_network.py` | `952f1673076daae67f6c6e6ec413bafd9ec636c8f7327bf6828dbb0026bc666f` | Real new-reader fixture plus active-fetch revocation and no-rebind tests. |
| `permanent-streaming/tests/test_provenance.py` | `dee3b3a5360497574668d5eb9ad710c67f4e85ad7f2013357314cdbf4c194cfd` | Replace only obsolete unchanged-check AST expectation; preserve other trial methods. |
| `permanent-streaming/tests/verify_units.py` | `ef4d2b9c51c2c0f30ee913324185803e4a24206ea74face082ac5fdd45036524` | Include new guard drop-in in native four-service fixture. |
| `permanent-streaming/validation-results.json` | `df2efedc9cb4f198ed52d684e3da9b5bc8622bbda7b0a7fc9216ad2329baf22a` | Record 251 tests, preserved baseline, new regressions and no production contact. |
| `permanent-streaming/verify.py` | `9b6bb1eab509ae3d7c2e8d0143829ddd1b6b92e05b9340ed5c1bcdf99db0cfaa` | Updated exact pins/private schema and live guard/grant/owner/stats coherence. |
| `trusted-guard-tests/run-offline.sh` | `b7474762b317805693c94ec76b41f4c6c0af6f7e478cb2353c2ebb623b2ccf8f` | Run actual permission/crash/cleanup tests in isolated namespaces. |
| `trusted-guard-tests/test_implementation.py` | `63305daa3b6b34c04febdd740fb56e63b1a08c5ee1ca79a30ff6dc61089f427d` | 50 actual implementation and matched release/cleanup/security regressions. |
| `trusted-guard-tests/transition-manifest.json` | `75d6fbb8357c515058eb4acb145b0920d363055a11782c875247f09bc3df5f6b` | Exact new runtime map, prior staged map and complete original baseline references. |

Key new protected identities: guard.py `d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0`; minimal verifier `a809936e8b31c265c00738d60d24064578b32c255759f16151a048cb95408de7`; 20 resource drop-in `578e03101e64c14da217e3d77f5bed9e0dbfbab9dad24b3f077c6b3891aed023`. Full old/new identities are in the manifest, not abbreviated approval values.

## Coordinated installation procedure — NOT performed

1. Obtain separate approval of this exact release commit and a bounded installation/rollback window covering the protected baseline transition, source/unit changes and systemd reload. Freshly verify exclusive idle state, original health, all nine OLD hashes/root source pins, default group 2, locked profile 1, approved ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e`, current credentials, peer 172.20.0.2, local images and existing root rollback/independent Denethor checkpoint. Do not add a backup/restore exercise.
2. Verify local release bytes against the reviewed commit and transition map. Read the staged inactive candidate remotely against all 44 `previous_inactive_candidate_hashes`; stop on extra/missing/drifted files. Capture original private relay JSON privately for conflict-checked reversal. Do not print source/credential/token values or put them in arguments.
3. Stop the protected stack **through its currently accepted old unit**. Confirm only its three containers stopped, original VPN/network retained and unrelated Docker/Jellyfin configuration/identities unchanged. No protected file replacement while the old stack is serving.
4. Stage/install the complete matched guard, minimal verifier/cleanup, 20 resource drop-in, new guard-unit drop-in and all 45 candidate files. Copy only mapped changed/new runtime targets; verify unchanged mapped targets rather than rewriting them. Preserve base units, accepted policy/WireGuard/DNS/Compose and data. All sources root:root 0644, directories 0755, with explicit private/runtime exceptions below. Refuse mixed old/new pins.
5. **Before stopped Docker container creation**, prepare the new EMPTY public status directory root:root 0755 if absent. Refuse symlinks, unexpected/populated anchors or prior transaction metadata; do not delete/clear them to proceed. Preserve the original private guard directory exactly 0700. Prepare `/run/dispatcharr-permanent` root:root 0700 and child `relay` 1000:1000 0700; confirm export directory 1000:1000 0750. Preserve existing content or stop on unexplained state; no recursive permission changes. Publisher initializes a brand-new anchor only during managed activation. The new loaded guard drop-in preserves it thereafter; a separate guard-service restart is not needed merely to create the directory.
6. Migrate private relay JSON: remove `ready_file`, add `guard_status_dir` exactly `/guard-status`; preserve source, ready_hash, manifest/segment 12-second values and UID/GID 1000 mode 0400. Registrar configuration/credentials/ACL settings do not change. Validate both schemas/values without disclosure.
7. Preserve owner identity; stage ONLY patched AIO, relay and gateway **stopped** using:

```sh
docker compose --project-name rivendell-iptv --project-directory /docker/dispatcharr-iptv \
  -f /docker/dispatcharr-iptv/permanent-streaming/compose.yaml up \
  --no-start --no-deps --no-build --pull never --force-recreate dispatcharr relay gateway
```

8. Install the reviewed 30 drop-in, then run source/private-input and pure stopped Docker workload checks appropriate to this stage. Public readiness is still absent and grant is intentionally absent; do not bypass a full readiness verifier to simulate runtime success. Check exact six relay binds and tmpfs via corrected stopped representation, no new port/network, all image/resource/owner pins. Native verify original+candidate unit definitions, daemon-reload and inspect actual effective order. Confirm real cgroup paths and preserved directory behavior; no timeouts/threshold edits.
9. Submit the separately authorized single systemd start. Let early withdrawal/admission/new apply/owner verification/grant/lifecycle operate normally. Do not manually create status/grant or start protected containers. On failure preserve private transaction/API receipts, permit scoped cleanup and stop; no automatic retry/latch reset.
10. Backend acceptance must include current host semantic table, G/grant/owner namespace and source/mount/image/resource contracts; VPN/DNS/IPv6, PostgreSQL, authenticated Redis, both uWSGI heartbeats, default/DVR Celery, no migrations/restart loops, exact owned registration and local exports, gateway after registration and strict unrelated comparator. No broadcaster fetch/playback or Jellyfin write. Publish separate sanitized live results.

## Scoped rollback ordering — NOT performed

Use only separate rollback authority and known registration outcomes. Unknown API writes, edited/shared records, unexpected schema migration or guard/kernel uncertainty block blind reversal.

1. While backend readiness permits and only when owned-record preconditions are known, perform the existing registrar’s scoped owned-record rollback. Preserve journals; do not reset DB/Redis or import historical trial state.
2. Stop the protected unit and verify public guard/grant withdrawal through the **old anchor** plus protected processes stopped. If withdrawal or stop fails, preserve exact kernel protection and request scoped recovery. Do not rename a populated directory, force a new anchor, or clear fault/transaction records to retry.
3. Remove only the stopped new relay (no volume removal). Restore original AIO/gateway stopped from accepted original immutable Compose/image inputs; retain VPN owner/network/data and unrelated services.
4. Restore the WHOLE original protected baseline: original guard.py, original minimal verifier and original 20 drop-in/source pins, removing only the new guard-unit and 30 drop-ins and disabling new cleanup use. Check all 17 original mapped hashes, including original nine. Preserve failed new private metadata as evidence; old source does not consume it. Restore prior private interface schema only from matching captured after-image/preconditions, never overwrite newer credentials/source changes.
5. Ensure no public authorization remains; remove/retire only empty reviewed public objects when no reader can retain them, or retain them empty/inactive for evidence. Never restore a copied readiness token. Native verify and reload original unit definitions in the authorized window, then the approved single restoration start through original admission/guard apply. Verify original legacy digest, exact current nftables table, original three services and unrelated identity/configuration.

No rollback deletes persistent volumes/data, flushes firewall rules, restarts Docker, changes policy/VPN/DNS, operates VMs or modifies Jellyfin. The release’s old hashes identify the accepted baseline; they are not authorization to run an archived helper out of its supported lifecycle.

## Remaining prerequisites and recommendation

The implementation is complete offline. Before installation, approve the full matched commit, verify current staged/production/private/recovery state, confirm real systemd cgroups and effective hooks, pinned VPN healthcheck/runtime namespace observations, public-directory lifecycle and one managed attempt with scoped rollback. Native fixtures validate syntax/control-flow; they do not establish real manager scheduling or runtime behavior. Private incomplete metadata requires review, never automatic clearing.

**GO for review and separate coordinated deployment authorization; no installation performed.** No further infrastructure task is begun. Stop after publication, leaving the existing protected stack untouched and awaiting authorization.

Reproduce all suites:

```sh
CADDY_TEST_BINARY=/path/to/verified/caddy sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh
sh configs/dispatcharr-iptv/guard-interface-review/run-offline.sh
sh configs/dispatcharr-iptv/trusted-guard-design/run-offline.sh
python3 -B -m unittest discover -s configs/dispatcharr-iptv/persistence-phase6b3/tests
python3 -B configs/dispatcharr-iptv/boot-admission-phase6b3k/tests/verify_units.py
```
