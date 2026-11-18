# Dispatcharr production image-binding review

**Decision: GO for a separately authorized matched production transition, conditional on all fresh preflight and rollback gates below. No deployment authorization is inferred.** This review prepares an unapplied candidate. The active repository release contract remains `aio_image: null`; production public files and units were inspected read-only. No Docker operation, application API/credential access, image operation, service change, provider request or playback was performed.

## Accepted image and evidence chain

- Source correction: `8764cfdaff97b8d94102f03d9b367f1e1de6c317`.
- Corrected build: `e0da9ff06ab827f6eaf79397d15dd8ce6399fe10`, `docs/dispatcharr-corrected-hardened-image-build.md`.
- Test-only binding: `e5e8080`, `docs/dispatcharr-corrected-image-runtime-binding.md`.
- Runtime acceptance: `d5225934a6d6ff8f919e01aae4219d36dba635d6`, `docs/dispatcharr-corrected-image-runtime-acceptance.md` and its pinned `corrected-runtime-acceptance-results.json`.
- Accepted image: `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439`.
- Known-good production AIO/rollback image: `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.

Acceptance attempt `corrected-20261118-c118f7fa` explicitly completed **11 tests, zero errors, failures, skips or socket-audit refusals**. It executed UID/GID1000 Django, disposable PostgreSQL migrations (184; fingerprint `b00f51e91c5b882cd84d3b2579d074ca`), authenticated Redis, actual non-eager Redis-backed Celery worker/task/queue probes, native API/discovery/channel/XMLTV operations, partial-failure ownership handling and two real uWSGI worker heartbeats. Its positive VPN/route/DNS witnesses were synthetic; no real AirVPN grant or provider interoperability was established. Transport completed with cleanup verified and all 33 original container identities, configuration fingerprints, networks and volumes unchanged. Historical receipts were preserved.

The exact 14 hardened outputs plus four inherited readiness files agree across build verification, acceptance verification and the proposed contract. No expected source hashes were regenerated:

| Installed application path | SHA-256 |
| --- | --- |
| `apps/epg/api_views.py` | `6fafed61eb78ebfdd669ab60745001948a63f708dd549175e8d4950a68ce0051` |
| `apps/epg/signals.py` | `a55f451c8af899edb79f201802e3533cf2139199c37abdb95fa4978a8dac2d8c` |
| `apps/epg/tasks.py` | `3d94f0c6aa4eed6520d584d97ad85b62760a9ae80efeac640a690eabacc427c6` |
| `apps/m3u/api_views.py` | `6c48c35abc821efbb428a74c832e7c8c018eef472d6f987505169cd83d902936` |
| `apps/m3u/signals.py` | `7b7b35c2931f401ef179b132648496749c49c07fabf0dd85d6c019e10dbacd92` |
| `apps/m3u/tasks.py` | `75a6eb9276ec96b0e5de2ae2b1274a63ffe47ef89cc8d6c1620a89e049467fb1` |
| `apps/proxy/live_proxy/input/buffer.py` | `17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810` |
| `apps/proxy/live_proxy/input/manager.py` | `ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf` |
| `apps/proxy/live_proxy/output/ts/generator.py` | `db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b` |
| `apps/proxy/live_proxy/readiness.py` | `fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b` |
| `core/api_urls.py` | `8ba3069abff1d26ff9d0070fd83194097c8b6f565b0b0391f46f0709155de324` |
| `core/provider_dns.py` | `28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a` |
| `core/provider_policy.py` | `2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639` |
| `core/provider_readiness.py` | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` |
| `core/provider_security.py` | `8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004` |
| `core/provider_security_view.py` | `b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b` |
| `core/provider_transport.py` | `4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39` |
| `core/xtream_codes.py` | `ed31daaf05ee812cfa7750b423c8b8840ab19bca48cc3ee560202857848133fa` |

## Current baseline and proposed binding

A NEST read-only public-file/unit inspection of Rivendell as Andrew's selected `media` account at **2026-11-18 18:21:39 UTC** matched all **67** working public installation mappings to release `227122dcbe9ebc76be46b8a91231350d6c93bdb4`, with root:root 0644 ownership/modes. The native 40 drop-in is absent. Stack and guard units were active/exited; Docker's unit was active/running. Stack timeouts remain 540/240 seconds; guard start/stop timeouts remain 60/90 seconds. The installed guard is `d25808d50ff14dd1f195397d34b1ead33c3ed8fa5b6aebc5a6c4bf2c120e91b0`; the reviewed native integration guard is `147cb62b0fa19e90d391b5583bde7e342f71bfca748e068f730ba3dd56e91f8a`.

This establishes installed public configuration and unit state, **not current container/application health**. The latest full Docker/Jellyfin health and fingerprint evidence is the accepted runtime report at `d522593`; deployment must collect fresh health/idle/security evidence. No private configuration, provider policy or credentials were read for this review.

The separate candidate is `configs/dispatcharr-iptv/production-image-binding/`. Its bound release contract changes only:

```json
{"aio_image":"sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439"}
```

The existing native lifecycle sets the same immutable value through `native_contract.image()`, and the candidate Compose overlay pins that exact literal. The AIO and relay image expectations remain separate. Unchanged pins:

| Service | Immutable reference |
| --- | --- |
| VPN | `qmcgaw/gluetun@sha256:a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209` |
| Relay | `local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` |
| Gateway | `caddy:2-alpine@sha256:78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |

Jellyfin is outside this Compose project; its image and settings are not proposed for change. No service, port, network, volume, capability or resource limit is added. Only the AIO image and its three reviewed read-only binds differ in the effective Compose preview. Source/target pairs are `/run/dispatcharr-guard-status` → `/guard-status`, `/run/dispatcharr-provider-status` → itself, and `/docker/dispatcharr-iptv/native-provider-hardening` → `/opt/native-provider-hardening`. All require existing host paths; no private provider directory is mounted.

### Production-only source-pin correction

The existing `backend.py`/registrar gate verifies 14 API files using `api-source-pins.json`. Two of those pins still describe the original AIO and would reject the accepted hardened image: `core/api_urls.py` and `apps/m3u/api_views.py`. The candidate updates exactly those two to the already accepted hashes above, updates its image metadata and preserves all twelve other hashes. No check or source file is removed. Isolated application acceptance did not execute this production source-pin gate.

The bound release-contract hash necessarily changes its minimal verifier pin. Candidate variants update only that `EXTRA_PINS` value, its source inventory and downstream base-input/permanent manifests. Original tracked files remain byte-identical. The complete proposed transition has **80 mappings: 52 unchanged, 15 existing replacements and 13 new targets**. There is no new target beyond the already reviewed native transition. This is a coordinated guard/control/verifier/unit transition, not an image-only substitution.

## Lifecycle and authorization boundaries

Effective native startup (20/30/40 drop-in composition): revoke provider assertions; withdraw public/private guard readiness; verify complete inputs; run unchanged admission; managed guard apply and semantic verification; prepare private/public anchors; verify stopped contracts; start/verify the preserved VPN owner; publish its verified namespace grant; start AIO and relay; verify AIO source contract, backend and owned registration; generate exports; start gateway last; run full running contract.

The guard's early withdrawal, guard unit hooks, admission drop-in, permanent 30/40 hooks and scoped cleanup all use the matched provider control integration. Stop/failure cleanup attempts provider withdrawal, guard withdrawal and protected-container stop even when a preceding action fails. Private-policy changes must use the trusted writer protocol and revoke first; ad hoc edits while authorization remains published are unsupported. Cleanup assertions run in the required managed cgroup; do not invoke guard mutations from an arbitrary root shell.

`provider_control.py prepare` creates/validates the root-private 0700 writer directory and stable root-owned 0755 public anchor, then requires an empty/revoked projection. It never publishes. The reviewed publisher requires the current guard and matching verified VPN grant; public records carry authorization metadata, not credentials/private URLs. Readers enforce ownership, modes, generation, boot/namespace binding and the existing five-minute lease. No automatic publication or renewal is introduced. With no provider authorization, native remote operations fail closed. Publication after private-policy changes, or any real provider activation, remains separately authorized work.

The guard private directory stays root:root 0700. The relay retains its existing public guard mount, image, request budget and restrictions. No provider destination is added to its broadcaster allowlist. Provider requests are separately restricted native application operations. Native provider credentials ultimately stored by Dispatcharr remain sensitive application-database data; this binding does not turn that database into an external credential vault.

Revocation is not instantaneous end-to-end enforcement: asynchronous failure cleanup, check-to-use windows and non-continuous kernel/VPN attestation remain documented limitations. Kernel nftables/VPN enforcement is separate from application-level readiness records. Stable public-directory anchors must not be replaced or unexplained populated directories adopted.

## Production versus isolated acceptance

| Area | Accepted isolated evidence | Required production gate |
| --- | --- | --- |
| Network | network-none; synthetic positive route/DNS/grant witnesses; real TLS and reader checks | Exact live nftables policy, Gluetun owner/tun0, DNS/IPv6 and guard/grant consistency |
| Processes | Real Django, Redis-backed solo-thread Celery and two uWSGI workers under fixture startup | Normal AIO entrypoint/supervision, default and DVR workers, current heartbeats |
| Data | Fresh disposable PostgreSQL, migrations184/fingerprint above | Existing persistent database, zero pending migrations and unchanged migration fingerprint; no restore/reset |
| Limits | 1CPU/1.5GiB/256PIDs, read-only root and tmpfs | Existing production AIO 2CPU/3GiB/512PIDs and its accepted writable root/data; only three new read-only binds |
| Lifecycle | Transport watchdog, explicit synthetic grants and fixture API workflow | Full managed 20/30/40 path, real source gates, existing DW ownership ledger and scoped failure cleanup |
| Maintenance | Plugin startup autodiscovery opted out; unrelated plugin periodic entry absent | Existing production maintenance configuration unchanged; inspect schedule before deployment |

Plugin maintenance is not covered by the native provider authorization contract. This review does not add an unreviewed production opt-out or claim all application background networking is disabled. Native Xtream/remote EPG automatic side effects remain denied/disabled by the reviewed hardening. If the deployment window requires additional maintenance isolation, that discrepancy must be resolved before deployment rather than silently changing production settings.

Known working DW identities from the published integration/retirement evidence: owned channel/stream **3/3**, channel number 9001, Default Group 2, streamcopy profile 1; approved ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e`; Jellyfin peer 172.20.0.2. Jellyfin tuner `84512b75-27af-509d-9377-a29982f9722b`, guide `fa590b78-e345-5343-b34d-9c7b4c5f10db`, channel item `67d9ed9926f9e1ef90002ff7dbfd790f`, mapping `m3u_72bdf3377216078a211cff2d20374229c8ace81a7c8cf374c785569d08a13c9e` → `dw-english-permanent`. LiveTV configuration digest recorded in retirement evidence is `133f81220c59c293a50116b5f9d20f8ecd422d0e9b46b0eeab1a63dbe9a09f0b`. Sources remain `/config/iptv/permanent-dw/current/dispatcharr.m3u` and `guide.xml`; guide content is an availability placeholder. These are evidence baselines to recheck, not new live API observations.

## Mandatory fresh deployment preflight

A future authorization must cover the matched 80-target transition and one scoped four-service stop/start, with **only the AIO recreated**. The installed unit owns all four services and has no supported AIO-only stop transaction. If permission is limited to stopping only the AIO, this plan is NO-GO; do not bypass the lifecycle or invent a unit.

Before any stop:

1. Verify approved review commit, clean checkout, proposal artifact hashes, original input pins, all 80 mappings and exact candidate variants. Never regenerate pins to accept drift.

2. Confirm Andrew's Rivendell account/host, exclusive administration, healthy and idle four-service stack/Jellyfin, no playback/recordings, no pending registration/DELETE intents or uncertain ownership receipts. Recheck channel3/stream3 through authoritative detail reads, no duplicates/shared ownership, group2/profile 1/ACL and Jellyfin peer/configuration.

3. Capture all 33 production container IDs, images, start times, restart counts, health and Config/HostConfig/Mounts fingerprints; network/volume inventories; Docker unit identity; effective systemd ordering/timeouts; current guard/VPN/kernel policy and owner/network identities. Use the existing private sanitized collectors; never dump native account/EPG responses containing credentials.

4. Verify accepted71 and rollback14c images locally, build provenance and all 18 hashes without pulling/building. Verify native source contract, candidate Compose agreement and exact public installed baseline. Reconcile inactive staged files by exact hashes; unexplained files or anchors stop the transition.

5. Verify resources using the unchanged production admission policy, DNS/IPv6/tun0 restrictions, gateway filtering and root-private guard. Inspect scheduled tasks/queues and supported maintenance settings; no real provider policy or grant is to be installed.

6. Confirm a current consistent protected recovery set and independent Denethor checkpoint, plus a scoped snapshot of the **current working four-service** public baseline and private ownership/transaction state. Old three-service archives alone are insufficient. If a new stopped checkpoint is needed, obtain explicit coverage in the deployment authorization; do not perform a backup/restore exercise under this review.

7. Confirm the existing production migration table is184/fingerprint above, no pending migration/schema change and compatibility with the new image before starting it. The new outputs contain no migration files, but the normal production entrypoint was not exercised in isolated acceptance. Any schema/data uncertainty blocks both deployment and an assumed image-only rollback.

## Exact controlled sequence (future authorization only)

The following commands are a plan, **not executed**. Use a verified root-private source checkout at the eventual approved review commit; the candidate files are not copied to production during this review. `$REVIEW` denotes that checkout's absolute path. `$BASELINE` denotes a fresh root-private rollback snapshot with the original public target tree and separate private receipts. Neither variable may contain a credential or provider URL.

1. Run the offline review verifier and verify `artifact-hashes.json` against the checkout. Complete every preflight gate above and record the intended original 67/introduced 13 target reconciliation. Preserve original unit/drop-in set, accepted base Compose, private state and recovery references in `$BASELINE` before changing them.

2. Stop once through the accepted current unit:

```sh
sudo systemctl stop dispatcharr-stack.service
```

Confirm its four dedicated containers stopped, all unrelated containers unchanged, firewall still enforced and old cleanup succeeded. Keep the VPN-owner container/network identity; do not remove it. Install no new code if old stop state is uncertain.

3. Stage the matched payload by the explicit `installed-targets.proposed.json` map. For each target compare the recorded original hash (or reconciled inactive-file state); verify the source bytes before copying. Install root:root 0644 only. Copy dependency sources/publisher/guard/verifiers and candidate manifests first; install unit drop-ins last. Re-verify **all 80 target hashes, ownership and modes** before daemon reload or any start. This map is a review artifact, not an automatic installer. Per-file primitive:

```sh
sudo install -o 0 -g 0 -m 0644 -- "$REVIEW/<mapping.source>" "<mapping.target>"
```

Use only exact map entries, never literal angle-bracket placeholders or directory-wide speculative copying. Preserve base units, firewall policy, WireGuard config, existing data, owner/network and private registration credentials. Root-owned code directories are 0755; protected private directories remain 0700. The native bundle contains only reviewed public code/contracts; no private policy is copied into it.

4. Prepare the provider anchor through the reviewed helper, not manual JSON construction:

```sh
sudo python3 -B /docker/dispatcharr-iptv/provider_control.py prepare
sudo python3 -B /docker/dispatcharr-iptv/provider_control.py assert-revoked
sudo python3 -B /docker/dispatcharr-iptv/permanent-streaming/verify.py inputs --native
```

Existing public/private anchors must validate without replacement. Do not publish/renew authorization. Verify the existing relay runtime/export permissions unchanged and private guard 0700/public guard 0755 anchors preserved.

5. Recreate **only AIO, stopped** from exact accepted overlays:

```sh
sudo docker compose --project-name rivendell-iptv --project-directory /docker/dispatcharr-iptv \
  -f /docker/dispatcharr-iptv/permanent-streaming/compose.yaml \
  -f /docker/dispatcharr-iptv/permanent-streaming/compose.native.yaml \
  up --no-start --no-deps --no-build --pull never --force-recreate dispatcharr
sudo python3 -B -c "import sys; sys.path.insert(0,'/docker/dispatcharr-iptv/permanent-streaming'); import verify; verify.workload(verify.snapshot(),False,True)"
```

No relay/VPN/gateway recreation or manual container start. The direct stopped workload check intentionally omits guard readiness while revoked; the managed full `prestart --native` will run after guard application. Confirm image 71, all required read-only mounts, exact original limits/namespaces, relay tmpfs contract and unchanged other container IDs.

6. With all drop-ins installed, perform native unit syntax/dependency verification before reload, inspect effective 20/30/40 ordering after reload and keep original timeouts/admission thresholds:

```sh
sudo systemd-analyze verify /etc/systemd/system/dispatcharr-egress-guard.service /etc/systemd/system/dispatcharr-stack.service
sudo systemctl daemon-reload
sudo systemctl show dispatcharr-stack.service -p DropInPaths -p ExecStartPre -p ExecStart -p ExecStartPost -p ExecStopPost -p TimeoutStartUSec -p TimeoutStopUSec
sudo systemctl start dispatcharr-stack.service
```

Start exactly once. The lifecycle applies/reverifies guard under managed context, starts the preserved VPN owner, verifies its security/namespace and grants it, starts AIO+relay, checks 18 sources and backend, rebinds the existing owned DW channel/stream and exports, then starts gateway. No provider publication/refresh or media fetch is part of startup. On failure retain receipts and allow scoped cleanup; no retry.

7. Require successful automatic final `running --native`, plus explicit read-only acceptance:

```sh
sudo python3 -B /docker/dispatcharr-iptv/permanent-streaming/verify.py running --native
sudo python3 -B /docker/dispatcharr-iptv/provider_control.py assert-revoked
```

Collect authenticated local PostgreSQL/Redis, two fresh worker heartbeats, default/DVR Celery responses, migration fingerprint and no unexpected restart/migration; guard/grant/namespace/kernel/DNS/IPv6 checks; empty provider projection with UID1000 private-directory denial; health-only native security endpoint denial with no grant; unchanged owned DW 3/3, streamcopy/ACL, fresh matching relay binding and valid current M3U/XMLTV. No synthetic grant or real provider policy may be installed to make a check pass. Verify gateway health/access filtering and Jellyfin health/discovery/config digest without fetching a stream. Recompare all 33 production rows, allowing only the documented AIO recreation and scoped protected start-time changes; VPN/relay/gateway IDs and all unrelated rows/networks/volumes remain unchanged. Stop for separate provider/playback authorization even on success.

## Conflict-checked rollback (future authorization only)

Triggers: managed start/admission/guard/source/security failure; unhealthy workers/gateway; unexpected migrations, ownership writes or unrelated drift. Do not regard the old image's presence as sufficient rollback safety.

Preconditions: scoped cleanup is complete and all protected containers stopped; public provider projection empty; guard readiness withdrawn through the managed cleanup/assertion path; exact kernel protection retained; registration outcomes known with no pending/uncertain journal; no native account/EPG job or persistent-state mutation requiring the hardened implementation; migration/schema fingerprint unchanged; exact original public snapshot and rollback image verified. If any condition is uncertain, remain protected/stopped, preserve evidence and request review. Do not clear journals, purge queues, relax checks, reset Redis/PostgreSQL or delete volumes.

1. If the stack remains active, use its installed managed stop (not individual `docker stop`). Preserve all failure receipts and compare public status absence/cleanup result. The new helper can assert provider withdrawal:

```sh
sudo systemctl stop dispatcharr-stack.service
sudo python3 -B /docker/dispatcharr-iptv/provider_control.py assert-revoked
```

Do not execute bare `guard.py revoke/assert-revoked` from an unmanaged shell; its supported context is the unit lifecycle. Failure to prove managed withdrawal blocks restoration.

2. Conflict-check every modified target against the installed candidate. Restore the complete original 67 public targets/root ownership/modes from `$BASELINE` according to `rollback-targets.json`; only after verification, archive the 13 introduced public targets outside active paths, including 40-native-hardening.conf and the native overlay. A target changed by another administrator must not be overwritten. Preserve revoked runtime anchors/private receipts; never remove unexplained runtime directories or working channel3/stream3. No database/application-data restore is performed by this plan.

3. Stage only the old AIO stopped from the restored base Compose (no native overlay):

```sh
sudo docker compose --project-name rivendell-iptv --project-directory /docker/dispatcharr-iptv \
  -f /docker/dispatcharr-iptv/permanent-streaming/compose.yaml \
  up --no-start --no-deps --no-build --pull never --force-recreate dispatcharr
sudo python3 -B /docker/dispatcharr-iptv/permanent-streaming/verify.py inputs
sudo python3 -B -c "import sys; sys.path.insert(0,'/docker/dispatcharr-iptv/permanent-streaming'); import verify; verify.workload(verify.snapshot(),False)"
sudo systemd-analyze verify /etc/systemd/system/dispatcharr-egress-guard.service /etc/systemd/system/dispatcharr-stack.service
sudo systemctl daemon-reload
sudo systemctl show dispatcharr-stack.service -p DropInPaths -p ExecStartPre -p ExecStart -p ExecStartPost
sudo systemctl start dispatcharr-stack.service
sudo python3 -B /docker/dispatcharr-iptv/permanent-streaming/verify.py running
```

Confirm no 40 drop-in, old guard/source pins, AIO 14c and original20/30 path. Use one authorized managed restoration start, with admission and guard intact. The unchanged registrar rebinds the existing DW records/export after the relay's fresh endpoint; it must not delete them. No old three-service 96bc fallback and no standalone owned-record rollback are part of this image restoration.

4. Verify all four services/Jellyfin, guard/VPN/kernel and fresh backend health, original owned records/ACL/guide settings and unrelated fingerprints. Stop on a failed restoration; no further startup retry or automatic database restore.

## Offline verification results

**743 distinct tests passed, zero failures/errors/skips.** There were 778 executions because 35 socket-diagnostic tests also run in the audit fixture. Counts: provider CLI 147, native hardening 106, runtime harness 140, persistence 26, permanent/security/lifecycle/units/network 210, guard permission review 14, guard-design 28, native network 14, provider permissions 40, new local audit fixtures 3, new binding proposal 15. Native unit verification and existing pinned Caddy routing/filter fixtures passed in isolated unrouted namespaces. Initial sandbox capability denials occurred before namespace fixtures executed; identical scripts passed with those local namespace capabilities available. No production or Docker test was run.

New tests validate exact image acceptance/old or mixed hash rejection, all 18 evidence hashes, actual existing native-contract resolution, two-only API pin correction, fixed other services/networks, three read-only mounts/no private policy exposure, exact 80 target scope and modes, original 67 rollback identity, revoke/admission ordering, no automatic publication and minimal verifier pin-only change. `verify_review.py` independently checks proposal manifests/dependency pins and original reviewed input hashes. Results/log digests are in `offline-results.json`. Reproduction:

```sh
python3 -B configs/dispatcharr-iptv/production-image-binding/verify_review.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/production-image-binding/tests -v
```

## Exact proposed changes and hashes

All source paths/full mappings are in `installed-targets.proposed.json`; rollback hashes are in `rollback-targets.json`. The 15 replacement and 13 new installed targets are:

| Target | Action | Candidate SHA-256 |
| --- | --- | --- |
| `/docker/dispatcharr-iptv/guard.py` | Replace | `147cb62b0fa19e90d391b5583bde7e342f71bfca748e068f730ba3dd56e91f8a` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/cleanup.py` | Replace | `0007aafcc865746e2186e3d491a9c913958985453e8ea66f7523e690dc5406f2` |
| `/docker/dispatcharr-iptv/minimal-phase6b3d/verify.py` | Replace | `eeebe55564ed845f202e99544b3d1d5ffdfb0be0043aa85f5831f3d319017e43` |
| `/docker/dispatcharr-iptv/native-provider-hardening/output-hashes.json` | New | `dc861e4615419508a43c16613f36bad1eca549980814fbbc51efb726566a4dd4` |
| `/docker/dispatcharr-iptv/native-provider-hardening/publish_policy.py` | New | `0e0a36dffeed12b092e97025ce0ec857dd1b470009321d677b3fd25796baa4e8` |
| `/docker/dispatcharr-iptv/native-provider-hardening/release-contract.json` | New | `f0a9f7bb35af077858ac85e69827053a29f9779968fdcbc0835a84504aaab0dd` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_dns.py` | New | `28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_policy.py` | New | `2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_readiness.py` | New | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_security.py` | New | `8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_security_view.py` | New | `b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b` |
| `/docker/dispatcharr-iptv/native-provider-hardening/runtime/provider_transport.py` | New | `4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39` |
| `/docker/dispatcharr-iptv/permanent-streaming/30-permanent-streaming.conf` | Replace | `8889cad7cf511579487a4472aac8deb89e23d9617e5b302b872732b8a7f44e86` |
| `/docker/dispatcharr-iptv/permanent-streaming/README.md` | Replace | `fe2744059edfbfa364f1efc837ebef844784e84810f255b213423acb3c6c45ff` |
| `/docker/dispatcharr-iptv/permanent-streaming/api-source-pins.json` | Replace | `fa9c370625a8c517ddbd515a9d0b2f03a47ebb17cd0b7a2720210680de986043` |
| `/docker/dispatcharr-iptv/permanent-streaming/base-input-pins.json` | Replace | `3be1bc2da6f91a78bd49a4b2aaad8444d924b4db52e562435603dbe72878257c` |
| `/docker/dispatcharr-iptv/permanent-streaming/compose.native.yaml` | New | `fe9fe961b9c1b6d5b7ecc45b655e4b4967e1d8355f48b2155d9b3fcc9e14d2d5` |
| `/docker/dispatcharr-iptv/permanent-streaming/contracts.py` | Replace | `570fea676d9d816667126db90e6dbcff5e5de7e1d08970eecf356d15a67b7cc3` |
| `/docker/dispatcharr-iptv/permanent-streaming/lifecycle.py` | Replace | `680a863d45216c272b9a2ac41df0723b0fe780ba19704a1976b6568b8f437649` |
| `/docker/dispatcharr-iptv/permanent-streaming/manifest.json` | Replace | `3fba1a65d5080b20baa76d8ebf8637c74c09d4cb17084c8cbdef24ded771e567` |
| `/docker/dispatcharr-iptv/permanent-streaming/native_contract.py` | New | `ce2d906d47285d4d9b09488c3e7e92bcaec5f0f195572a54e081dc7c46e356f9` |
| `/docker/dispatcharr-iptv/permanent-streaming/tests/verify_units.py` | Replace | `f863b1e09792617e6ae356bead33284d74d0c4abd36fc11c122af4a7737976a5` |
| `/docker/dispatcharr-iptv/permanent-streaming/verify.py` | Replace | `6f8e6fa2a3c222a575206b352debaa30ef9ac1b6e8b6fef839c9472c143c27e4` |
| `/docker/dispatcharr-iptv/provider_control.py` | New | `33fd56fc7a461ad9e416ba10f0bbdea175b2382e461e192bcb213a77e5844d24` |
| `/etc/systemd/system/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf` | Replace | `37226a0e1d77a14d2f0c0e16254f0f6699e7e0c543afcebfd24630cde0249a34` |
| `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` | Replace | `e639eab69f150f9f9ab833def8353c38f33bdbf00e3cb23e5ad0dfc595edd964` |
| `/etc/systemd/system/dispatcharr-stack.service.d/30-permanent-streaming.conf` | Replace | `8889cad7cf511579487a4472aac8deb89e23d9617e5b302b872732b8a7f44e86` |
| `/etc/systemd/system/dispatcharr-stack.service.d/40-native-hardening.conf` | New | `c0688992469db9c181faa9be16530db14fe734d5939de3b988c5ab8c90d6dd64` |

The complete proposal file inventory follows. `artifact-hashes.json` records these hashes; the report and that inventory file are excluded from their own contents to avoid circular digests. These are new review artifacts, not production writes.

| Review artifact (relative to production-image-binding/) | SHA-256 |
| --- | --- |
| `README.md` | `24ab88a98b6e34f0ef3ba20b9edd27933c248e6b074ec23967b885bfdcb001db` |
| `candidate/minimal-phase6b3d/artifact-hashes.json` | `7be1b02537744ac8f4a34dc69e45785f13a91490cee154a331e4bdeb5cd0a995` |
| `candidate/minimal-phase6b3d/verify.py` | `eeebe55564ed845f202e99544b3d1d5ffdfb0be0043aa85f5831f3d319017e43` |
| `candidate/native-provider-hardening/output-hashes.json` | `dc861e4615419508a43c16613f36bad1eca549980814fbbc51efb726566a4dd4` |
| `candidate/native-provider-hardening/release-contract.json` | `f0a9f7bb35af077858ac85e69827053a29f9779968fdcbc0835a84504aaab0dd` |
| `candidate/permanent-streaming/api-source-pins.json` | `fa9c370625a8c517ddbd515a9d0b2f03a47ebb17cd0b7a2720210680de986043` |
| `candidate/permanent-streaming/base-input-pins.json` | `3be1bc2da6f91a78bd49a4b2aaad8444d924b4db52e562435603dbe72878257c` |
| `candidate/permanent-streaming/compose.native.yaml` | `fe9fe961b9c1b6d5b7ecc45b655e4b4967e1d8355f48b2155d9b3fcc9e14d2d5` |
| `candidate/permanent-streaming/manifest.json` | `3fba1a65d5080b20baa76d8ebf8637c74c09d4cb17084c8cbdef24ded771e567` |
| `compose.effective.review.yaml` | `26782e4348068e2666efe1b988089c44959c69d2aac9068d62dbc1b75bba2365` |
| `installed-public-baseline.json` | `c3b250e08e5c5d46868119119551c816450fac1b68581eca653227bd3d9c7e4a` |
| `installed-targets.proposed.json` | `586c703eea209c28d36970926b756431b4e63c748041ec391249470227b2ba9a` |
| `offline-results.json` | `2e0b779ff8b7e557e06dbbe8230e56c4a6623598db31d0af94d8d624d90c0e22` |
| `review-input-pins.json` | `d9fc14ea5c69289a46817267ac6ba30b302c42a09bb6163dff89ea78e263a714` |
| `rollback-targets.json` | `91f418223774a9e154f9dd10ccf792a2c628636f6f0143775e19b6e89026df0a` |
| `tests/test_proposal.py` | `afff4b6864725298981afd8136c7a8e0b96c9ff33a405526241257d7867161da` |
| `verify_review.py` | `2fcf3c0c6414961754a144009a74ec11b343fcca133dd62c07ca1e586185dfa4` |

## Remaining gates and recommendation

No unresolved image/source mismatch remains in the proposal. The stale API pin discrepancy is corrected only in the separate candidate. The active release contract, base Compose, installed units, live images and Jellyfin settings remain unapplied/unchanged by this task.

**GO for separately authorized coordinated deployment review/execution only if all fresh preflight conditions pass and the owner accepts a scoped four-service stop/start with only AIO recreation.** Live production container health, provider-policy anchor reconciliation, current four-service recovery availability, queue/registration certainty and migration compatibility must be re-established at that time. No GO for real provider activation, playback or deployment under this review. Stop after publication.
