# Dispatcharr permanent streaming implementation

2026-11-17 UTC. Andrew's Rivendell; repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.

**Candidate implemented; 117 offline tests pass. GO for review and a separately authorized controlled installation after the prerequisites below. NO-GO for claiming installed or accepted permanent streaming.** The original three-container deployment remains the installation baseline; no production configuration or lifecycle action was performed.

## Evidence and preserved identities

The [artifact review](dispatcharr-permanent-streaming-artifact-review.md) supplies verified trial identities. Phase 5H's successful sessions delivered H.264 720p50/AAC stereo with Jellyfin codec-copy remux; request-to-HLS-ready was 19.910/17.523 seconds and the user reported smooth playback after brief initial buffering. Phase 5I deliberately removed trial data, endpoint state, exports and its API token. This candidate reuses source and the retained image, not the historical trial database, identifiers or credentials.

Both AIO and relay pin `local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. No image rebuild or pull is required. Dedicated Gluetun remains pinned at `a2d96492aaac1e57d91e324fcf32382fc3c4b4f1fb59997fcf7c93effc582209`; Caddy remains `78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9`. The accepted base Compose SHA-256 is `08585e417a257c22f7a207c8440c82bc009edc48ab641b097ce733cde553915d`.

The successful trial relay is retained byte-for-byte as `reference/trial_hls_relay.py`, SHA-256 `15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75`. Its destination/HLS/resource validation, guard checking and shutdown methods are compared by AST to the candidate. The finite-fetch/DNS helpers and manifest telemetry match the review's original hashes. The existing four-file image readiness patch is unchanged.

The architecture remains Jellyfin → LAN Caddy → Dispatcharr TS/FFmpeg streamcopy → loopback HLS relay → broadcaster over the existing dedicated VPN. Caddy does not proxy directly to the HLS listener. Backend port stays 9191; no new published port, Docker network or host daemon is introduced.

## Request and resource policy

The process-wide 1,200-fetch lifetime counter is replaced with **120 attempts per trailing 60 monotonic seconds**, including failures. A fixed-length deque is pruned on each attempt; there is no lifetime exhaustion, retry queue or automatic backoff/retry loop. Exceeding the rate budget fails closed, latches relay failure and causes managed relay shutdown. It requires operator recovery rather than automatic restart. The private configuration cannot raise this budget.

All existing destination, fresh all-public DNS validation/IP pinning, verified TLS hostname/certificate, redirect, forbidden HLS tag and MPEG-TS segment checks remain. Per-fetch deadlines stay 12 seconds. Manifest/segment caps stay 1 MiB/8 MiB. Concurrent fetches remain four. A new bounded HTTP server limits connections/parser threads to eight, backlog to eight and socket operations to 12 seconds, including idle clients.

The relay has read-only root/source/config, UID/GID 1000, all capabilities dropped, no-new-privileges, 0.5 CPU, 256 MiB memory+swap ceiling, 64 PIDs and a 16 MiB temporary filesystem. Telemetry retains two rotating 8 MiB files and at most 1,024 queued records of <=1 KiB. Loss/I/O failure latches health failure. Resource/manifest maps remain bounded at 4,096 entries; diagnostic peer history retains the latest 64 addresses. Operational bounds remain deliberate safety controls.

## Managed startup and shutdown

`compose.yaml` is a complete four-service candidate derived from the unchanged accepted base and restart=no persistence overlay. It preserves VPN settings, published port and network exactly. AIO retains its original data, environment and VPN startup entrypoint. Its helper source and credentials are read-only binds; the relay runs the same verified image as an unprivileged Python runtime.

The new **30** drop-in leaves the base unit, original **20** admission drop-in and original guard inputs unchanged. It replaces only effective project lifecycle/check commands. Order:

1. Verify accepted base and candidate hashes, private configuration and installed drop-in.
2. Run the unchanged resource-admission helper (four CPUs, idle >=50%, steal <=10%, load1 <4, three consecutive five-second samples, maximum 300 seconds).
3. Reapply the exact accepted nftables policy; prepare only the dedicated runtime directory; verify stopped four-service topology.
4. Compose starts/waits for VPN, patched AIO and relay with no build, pull or recreation.
5. AIO checks pinned API source, PostgreSQL migration fingerprint, authenticated Redis, both fresh uWSGI heartbeats and default/DVR Celery responses.
6. Register the new relay instance through the supported API; verify the committed binding and export generation.
7. Start gateway only with `--no-deps`, then verify all four services, namespace/image/source/resource contracts, actual VPN route/killswitch/resolver/IPv6 restrictions and binding.

Stop/failure cleanup remains scoped: gateway, relay, AIO, VPN; no data deletion or firewall removal. Relay SIGTERM cancels/reaps active fetch/DNS work, closes the listener, writes stopped state and removes its endpoint descriptor. Existing Type=oneshot, restart=no and 540/240-second systemd timeouts remain inherited. No additional host supervisor is installed. Manual relay-only restarts are not a rebinding path: use the managed unit; stale identities fail verification.

## API registration and recovery

Compatibility was checked against official Dispatcharr source at `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`. All **14** stored source hashes match read-only checksums from the running original AIO; the patched image retains those base layers. Sources and hashes are listed in `api-source-pins.json`; the future backend gate rechecks them. See the pinned [channel serializers](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/serializers.py), [channel API routes](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/api_urls.py) and [account token routes](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/accounts/api_urls.py).

Registration uses a fresh JWT from `/api/accounts/token/`; supported single-object stream/channel POST/PATCH/GET/DELETE operations; and read-only profile, settings and group endpoints. It uses writable `stream_profile_id` and `streams` fields, relies on the pinned custom-account creation signal, and verifies readback. It never edits a profile, provider account, CoreSettings or database directly. Creating the channel passes an empty channel-profile list to avoid the release's default add-to-all-profiles behavior.

The one reserved identity is `dw-english-permanent`, channel number 9001. Existing collisions fail instead of being adopted. A private ownership ledger stores the newly created actual IDs/UUID; normal restarts preserve them and update only the stream's fresh opaque loopback URL. Health correlates the descriptor and live non-media instance challenge, with stale-state rejection. Registration rechecks the relay instance before commit. No broadcaster URL is placed in Dispatcharr's stream or Jellyfin exports.

A private write-ahead journal permits conditional rollback of confirmed effects. Unknown write outcomes, interrupted precommit work and conflicting edits block another start. An interrupted verified commit can be completed from its marker. Explicit reconciliation requires confirmation that no request remains in flight; it checks current state before reversing journaled effects. No blind POST retry or duplicate-record recovery is used. The release has no server-side idempotency key/CAS here, so installation requires an exclusive administrative window; client read guards are not claimed to make concurrent API edits atomic. Explicit owned-record rollback is provided and refuses adopted/shared or edited records.

## Exports, guide renewal and Jellyfin

The relay's existing state-writer thread publishes a two-file generation after registration and renews it every UTC hour. An atomic `current` symlink exposes the M3U/XMLTV pair, with at most two owned generations. M3U contains exactly channel 9001 and the canonical local TS URL using the actual registered UUID.

XMLTV contains one **explicitly labeled availability placeholder, not a broadcaster programme schedule**, covering a rolling 49-hour interval. No show titles are invented and no remote EPG/logo fetch is added. Jellyfin's existing native RefreshGuide schedule must be verified to run within 24 hours; it is not modified or replaced by a host timer.

`jellyfin.py` is an explicit future operation, not part of stack startup. It adds/checks one stable owned M3U tuner and associated XMLTV provider, preserving unrelated tuner/provider entries and every other setting. It retains count=1, sharing=true, looping=false, hardware transcoding=false, import-favorites=false and guide scoping to that tuner. Files are under `/config/iptv/permanent-dw/current/`. It saves a private intent/before/after receipt, accepts only scoped server-default normalization, checks changes, refreshes the existing guide task and supports conflict-checked rollback. It uses Jellyfin 12's MediaBrowser authorization. No library, user, DVR or playback-default endpoint is called.

## Offline validation

| Suite | Tests/result |
|---|---:|
| Budget, registration/failure/rollback, exports, Jellyfin, lifecycle | 39 passed |
| Four-service security/Compose/nftables contract | 9 passed |
| Exact trial provenance, security methods and manifest | 3 passed |
| Existing minimal persistence regressions | 12 passed |
| Existing boot-admission regressions | 28 passed |
| Isolated real TLS/DNS, bounded connections, telemetry, process startup/shutdown, active DNS cancellation | 11 passed |
| Pinned native Caddy adversarial/identity groups | 15 passed; 91 fixture requests |
| **Total** | **117 passed; zero failures/errors/skips** |

Native `systemd-analyze verify` passed using the exact base units and both drop-ins plus an offline Docker readiness fixture; no service was executed. The installed Compose CLI accepted candidate stdin using `config --quiet --no-env-resolution`; it wrote no configuration and performed no lifecycle action.

Network fixtures ran in an unshared user/network namespace containing only lo and synthetic 93.184.216.34, with no external interface/default route. TLS certificates, API records, credentials, HTTP responses and MPEG-TS packets were synthetic. Real certificate/hostname failures, redirect refusal, mixed/private DNS answers, finite deadlines, DNS reaping and SIGTERM cleanup were exercised. The pinned Caddy binary SHA-256 is `a563843e11cbce39c557bd429ebb787d56f49d51d9bbb3292cd9b36b37a60cdf`; it was copied read-only from the existing gateway and is not committed. Host tests used Python 3.14 and existing PyYAML 6.0.3; no package was installed.

Reproduce with `CADDY_TEST_BINARY=/path/to/verified/caddy sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh`. Source and test outcomes are in the manifest and `validation-results.json`. Docker-installed execution, authenticated live writes, Jellyfin discovery, broadcaster reachability and playback were deliberately not exercised.

## Installation, rollback and prerequisites

The [candidate README](../configs/dispatcharr-iptv/permanent-streaming/README.md) contains the exact staged installation and scoped rollback sequence. It leaves the current base Compose/Caddy/guard/minimal verifier/admission files untouched, installs the candidate alongside them and adds only the 30 drop-in. Replacement AIO/gateway and the new relay must be staged **stopped**; the existing unit's `--no-recreate` cannot itself promote an image. Preserve the exact VPN owner and namespace references. Only the subsequently authorized systemd start may perform admission/start.

Before installation obtain:

- Separate installation, playback and bounded rollback authorization; no active playback/DVR or conflicting administrative writes.
- Fresh accepted baseline/pins, local availability of the exact image, actual UID/GID and private directory/mount permissions.
- Privately entered **current accepted-AIO** credentials, guard digest and retained owner-selected source. Do not copy revoked trial credentials; private schemas deliberately contain no filled values.
- Reviewed exact observed stream-peer /32 ACLs and canonical ACL digest; M3U/EPG and XC remain loopback-only. The registrar refuses drift and never widens access. Any necessary current application-ACL adjustment needs an explicitly approved scope.
- Existing Default Group, unique locked streamcopy profile, verified Jellyfin session, read access to stable exports and native guide renewal schedule.
- The already established recovery reference and matched rollback inputs verified for that authorized window; no additional backup/restore exercise occurred here.

Rollback restores only captured Jellyfin tuner/provider state, stops candidate gateway/relay, conditionally removes only owned API records while the AIO remains available, then stops the protected unit. Restore original base+minimal project/image, remove only the new drop-in and stopped relay, retain data/VPN/guard, and start through the original gate only under rollback authorization. Conflicts/unknown outcomes preserve receipts and stop; no `down -v`, pruning, DB/Redis reset, full Jellyfin restore or threshold relaxation. Unexpected migrations require matched recovery, not an image-only reversal.

**Recommendation:** implementation and offline validation are complete. Proceed only with a separately authorized controlled installation and the live acceptance baseline from the artifact review. Actual DW playback must still demonstrate the previous streamcopy/remux behavior, guide visibility, absence of persistent visible buffering, clean consumer shutdown and managed recovery. No production readiness claim is made from fixtures.

## Exact candidate inventory

Paths below are relative to `configs/dispatcharr-iptv/permanent-streaming/`. The runtime manifest pins all source/tests including references, excluding its own recursive hash and the validation receipt. Both excluded files are independently hashed below. This report's own hash is available from its committed Git blob rather than a self-referential entry.

| File | SHA-256 |
|---|---|
| `.gitignore` | `6feaded4e28ea86e001a6751b4e3d960e8b7c31b9616ff9936b79297086e809b` |
| `30-permanent-streaming.conf` | `3be80cb6197f1fa756aa9c7c477dc8064cb4fd0d6a6ec59ef5eb18bf7817cb70` |
| `Caddyfile` | `8b7b661f80ab157957480b330d96861d3980370fd1830d0cb36df93b79a08ba6` |
| `README.md` | `9281f0b76c7fc3091680debe4f37d5953871da62c259159f80e4250ec69ce582` |
| `accepted-table.template.json` | `90976136177701559e709ab612f6857499bfd2aea372a43c6ca9e538cd2156d5` |
| `api-source-pins.json` | `036dd097e03ef536f3f0e1de53f3707c5ab5177fc2244dc71dce91400f637cdc` |
| `api.py` | `aabd860d76651e021ca5b61677c8c02b554f3ae5901f41072c9518434b1fca15` |
| `backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` |
| `base-input-pins.json` | `83395e6599724e46dee03bdcd791bf7a178355229cf001b5aae98a124f19fe08` |
| `bounded_server.py` | `ec8e615f721ee1b047b51a80537c39f1247b136503c5236ef5d975f4fc9c020d` |
| `compose.yaml` | `7587c2badc7c06b2bac59408964216d00f366b17109a6417caa38ba64399e51c` |
| `contracts.py` | `89ad5581d6ed26f4f7e909a9302d5c6d26ac2a5b7b009026228304e3c4a10619` |
| `dns_worker.py` | `df7e483eaad95749fe5cc0ae97dd0d259c6e86b7896edca3cac9d62728870596` |
| `exports.py` | `460291da7961b9463420cec14c19648f4e33ad21eef82af271d3d1d830bb9c44` |
| `fetch_runtime.py` | `8b3595556c3061da17e5a018e07871238d786601e973625cde13f88ca91a3d27` |
| `files.py` | `314e4c70f7daf02bd6d1ce8a5bb8cc60690365d4507c3f99915ae2c5cf79723a` |
| `health.py` | `f4da54dece514ea24df5a6561ce52b883a1737213634b95bb1eab94a1b4ec6db` |
| `hls_relay.py` | `5eb958dbcf1ef6d2b92fa47ba4fb737511042486601969b955f7940241fb4b36` |
| `jellyfin.py` | `f328d3c5e26ca3465717b17376e6cc3a04f858595b08514e449064c68ade950f` |
| `lifecycle.py` | `2e2c7664cf7ea9fc6d2d547f1b8248b3a6734f32a332c12fcf7f9af4e2e6a7ed` |
| `manifest.json` | `98d962f397c5bae9aee3411574687168140d17c6419635a7e3d8f7550e1b0c0f` |
| `manifest_telemetry.py` | `179a364baaf3a7fbde6c09082db0fc9df65639812a86e7139bc0c1ec32df5784` |
| `rate_budget.py` | `86b11daec92b621d2bb4d9288da78ea909976f5483c5aab4417a29961b22bd56` |
| `reference/Caddyfile.accepted` | `bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98` |
| `reference/trial_hls_relay.py` | `15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75` |
| `refresh_manifest.py` | `438fe72028cec2703111a109b8217fc01e8c3b8757d380c9b0af5cbb6f2c0a8d` |
| `register.py` | `20f0ed9ed1c44be718dbc2e1c8bb2147cde0d818152f984d2080d2cb3bc03652` |
| `registration-config.schema.json` | `7edb2204f1be1380dd9c2168c2d6021da8882c69b2abf89b401aecdfa8ed413b` |
| `relay-config.schema.json` | `2adf89698e2b9038e97a69279715d1a62dc1d7367d7ffcb2c926dc3a6e898d62` |
| `relay_main.py` | `b273dd21d1ea8a89010a7304138046d7426c61a98d8aaeb0be3188cd38e69473` |
| `telemetry.py` | `d5ab9d69bd66b364b0cdc2c0b61af225e75998cbc587bac2b61fdb16823c5ffa` |
| `tests/run-offline.sh` | `785bf57c5855a1094679be2feb717e35ede6801a068cfcc4162faa8f5cf52446` |
| `tests/test_candidate.py` | `8142e68571d5549ce62c4e6d5cb20aeb42f7cb2c85122a951100591ad4117b28` |
| `tests/test_contract.py` | `a0db206c9d62808917f8b248dd39faf14537650100422a03e86903a2a985963e` |
| `tests/test_gateway_native.py` | `6d5b298927c27315f057182507098aac4af4b7d59cf8cb0d37a4a3d25e456dee` |
| `tests/test_network.py` | `6079fe5c8a6c08b6c0bbb2eb6d21651ec84c8a410dc78b5f25c01ce884acd133` |
| `tests/test_provenance.py` | `d70a03f532ba59b1047eb962b539accc3d78cecf942c8ddc371d5ddfd1ff337c` |
| `tests/verify_units.py` | `54321e61b45dd632642ab60eb6070959e065fb7aed1c3cfc212777553f40086e` |
| `validation-results.json` | `3a0d2434177dc1c0ebfe517c95caf1b3834ac7de31cba47a675015c158c9b0dc` |
| `verify.py` | `af6657dee883b297f281e0997e254886df2d5f28ec76955293c45b7e1d72ebb2` |
| `verify_binding.py` | `cf9d079d720c952c7a2368a568d9d73595f12cd05889aac33775ef0cacc1c4f8` |

No production writes, image builds/pulls, container starts/stops/restarts, Docker-wide restart, firewall/VPN changes, Jellyfin changes, playback, reboot, new infrastructure or backup/restore exercise occurred. Stop after publication; await installation authorization.
