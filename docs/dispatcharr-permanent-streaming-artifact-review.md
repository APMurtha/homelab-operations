# Dispatcharr permanent streaming artifact review

2026-11-17 UTC. Andrew's Rivendell (10.10.20.30), VM 130 on Orthanc. Read-only artifact review; no deployment authorization exercised.

**GO to reuse the verified patched image and retained source. NO-GO to deploy the trial unchanged as permanent service.** The remaining work is a bounded lifecycle/security-contract adaptation, not a new streaming implementation.

## 1. Evidence and current baseline

The successful baseline is [Phase 5H](dispatcharr-jellyfin-session-analysis-phase5h.md), followed by [Phase 5I closure](dispatcharr-jellyfin-trial-closure-phase5i.md). Earlier [5A](dispatcharr-jellyfin-phase5a.md) and initial [5B readiness](dispatcharr-jellyfin-phase5b.md) are discovery/readiness evidence, not the final playback result.

The two successful DW English sessions delivered 720p50 H.264 and AAC stereo. Jellyfin remuxed both codecs without re-encoding. Server request-to-HLS-ready times were 19.910 and 17.523 seconds. The user reported smooth playback after brief initial buffering. Browser first-frame/autoplay/buffer events were not captured; packet delivery gaps are not proof of visible freezes. Reopening created a new producer rather than reusing the previous one.

Fresh inspection found the original protected AIO, dedicated VPN and gateway healthy. Input, guard and running-contract verification pass. PostgreSQL still has 184 migration rows with fingerprint `b00f51e91c5b882cd84d3b2579d074ca`, zero channels and zero EPG sources. Built-in FFmpeg profile 1 still uses streamcopy and MPEG-TS. Both persistence units are active/exited with successful results.

Final observation at **00:51:19 UTC** confirms every container's recorded identity, image, configuration fingerprint, start time, state, health and restart count unchanged across verification. Docker/network identities and all nine installed persistence/admission files are unchanged. Jellyfin's current Live TV XML tree matches the saved original recovery XML semantically. The successful trial integration is currently absent.

## 2. Artifact inventory and integrity

All entries below were read and hashed or inspected in this review. SHA-256 values are full length.

| Artifact | Verified SHA-256 / immutable image identity |
|---|---|
| Patched image (both retained Phase 4H r2 tags) | `14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` |
| Original/current AIO image | `96bc548978c68e684677da7895692eeeefb7f0b2edfa38311dac2b702c61d236` |
| Gateway Caddy image | `78bd35025c7ba85961dd149ae670315129954e77abe2383ac47c89106b35ade9` |
| Retained Phase 4H r2 build-context tar | `04e270aebc98a9df5f1e5911e8417f0eba46f208a88a2b50e7913ed93b6221c1` |
| Build Dockerfile | `276fd90eb1a07ff8b3816d64b978c3e320bb4a565af97841b9dc699c205d89ad` |
| Patched input/buffer.py | `17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810` |
| Patched input/manager.py | `ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf` |
| Patched output/ts/generator.py | `db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b` |
| Patched readiness.py | `fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b` |
| Readiness proposed patch | `73fed8008bec5ad62b6c243c0b91c83b8594bed702ff4307473194dba8cad74f` |
| Phase 4M public bundle tar.gz | `004ca18393155780e44cdea0f6900c7b64dbbbc6b51e2985f9f1c598dbde080a` |
| Phase 4M original hls_relay.py | `d2508eab9b9a9b034dbbba36a6406e6ba8f2f6e80f1597f973d4d580be4fc226` |
| Successful until-stop trial hls_relay.py | `15c7ab3d87cbeb6e23419ce08536d6882d2721a3c9339b6bb24673387de6fb75` |
| fetch_runtime.py | `8b3595556c3061da17e5a018e07871238d786601e973625cde13f88ca91a3d27` |
| dns_worker.py | `df7e483eaad95749fe5cc0ae97dd0d259c6e86b7896edca3cac9d62728870596` |
| telemetry.py | `1f45690638d4065762a2a569f8c7bcd68fb683ca355f091f9b57ff7976ee25da` |
| manifest_telemetry.py | `179a364baaf3a7fbde6c09082db0fc9df65639812a86e7139bc0c1ec32df5784` |
| observers.py | `ee63e0f623574b070db13f98e889e3f22034ce5def8d3222da7af037029fb2e6` |
| Successful trial Caddyfile | `92014e7c19d257fe2420b41c42f7ff88e6d2f911db79f02885f8dcb2532c334e` |
| Current accepted Caddyfile | `bf5e40d2ccba8799f4b38f15336399fea7068f676150c2f7b18a1e07dc081a98` |
| Trial start.sh (historical, not a permanent launcher) | `5d9c605cda4f5474ddb60d5cb2aaf86f7fbfb74a00675877a83afa058d30d525` |
| Trial nginx-default | `ab976a25bc01e2530051d7b76251f0ab99490bc5bced54d880c979934c34f315` |
| Trial uwsgi.ini | `6d32fa1b73ce7ddfd9516b9e3aa0fc4f97b945e8726fcbca538157ce982ffe28` |
| Installed resource-admission helper | `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917` |
| Installed admission drop-in | `72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb` |

The patch file's digest is recorded here from the retained repository source; the deployed overlay bytes independently match the Phase 4H manifest. No rebuilt image is substituted.

### Source and build locations

- Repository: `configs/dispatcharr-iptv/image-phase4h/` and `readiness-v2/`.
- Rivendell build tree: `/docker/dispatcharr-iptv/private/build-phase4h/r2/build/`. Dockerfile, .dockerignore and all four overlay files match the reviewed manifest.
- Retained local r2 context: `.ai-local/dispatcharr-phase4h/build-context-r2.tar`; archive hash matches. The rejected r1/old Phase 4G build recipes are not deployment inputs.
- Retained local relay bundle: `.ai-local/dispatcharr-phase4m/phase4m-test-artifact.tar.gz`; archive hash matches.
- Rivendell public fixture bundle: `private/offline-phase4m/fixtures/` beneath the Dispatcharr project. All 64 available manifest-listed files match.
- Successful trial relay/gateway/runtime source: `private/live-phase5b-open/config/`. The five relay dependency hashes match Phase 4M exactly.
- Trial control source: `private/live-phase5b-open/control/`. All seven retained control files match the repository input manifest; cleanup/finish/safety hashes also match the recorded closure preflight.
- Evidence: `private/live-phase5b-open/phase5h-analysis/` and `phase5i-closure/`.

Both `local/dispatcharr-readiness:phase4h-r2-a` and `phase4h-r2-b` resolve to the verified patched image. Docker also retains the local RepoDigest `local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. This establishes local availability, not a remotely pullable registry publication.

There was **no separate relay image** in the successful trial: Python relay code was mounted read-only and exec-started inside the patched disposable AIO. Reuse that exact image/runtime; no relay image build is needed.

### What the readiness patch fixes

Release metadata/source reference is `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`; the immutable base is Dispatcharr 0.33.0 at the original image identity above. Historical OCI revision metadata differs as documented in [Phase 4H](dispatcharr-image-build-phase4h.md); do not replace the base using a guessed commit/tag.

The four-file patch implements canonical input-buffer readiness: producer generations, actual contiguous MPEG-TS byte budgets, Redis-server-time freshness, atomic binary Redis snapshots, fencing of stale writers/readers and re-admission after source switches/eviction. It preserves established timeout, buffering-speed, authentication and failover defaults. It does not itself repair the separate stale Redis singleton problem seen in Phase 5B; [5G recovery](dispatcharr-worker-recovery-phase5g.md) and fresh backend/per-worker acceptance remain relevant.

Fresh image inspection confirms Linux/amd64, identical image Config, and an identical prefix containing every original base layer. Together with the unchanged immutable image identity and retained build/source hashes, this supports dependency compatibility. The historical completed-image test matrix was not rerun: that would require starting containers, prohibited here. Patched in-image files were not freshly extracted from a new container.

## 3. Relay enforcement and exact trial differences

The successful relay is byte-for-byte reproducible from the reviewed Phase 4M source with exactly three documented edits:

1. Replace the finite session expiry with infinity for the owner-directed until-stop trial.
2. Construct but do not start the session timer; host watchdog/explicit stop owned trial lifecycle.
3. Emit JSON null rather than converting infinite remaining lifetime to an integer.

Reconstruction produces the retained `15c7ab…` hash. No destination/fetch enforcement changes are hidden in that difference.

Retained restrictions include one exact approved HTTPS manifest and hostname; only same-directory .ts segments; no credentials/alternate ports/query/fragment/percent-escape/traversal destinations; rejection of redirects and unsupported HLS tags, including external key/map/master-playlist mechanisms; public-address DNS validation on each fetch; IPv4 connection to the validated address with hostname-verified TLS; opaque HMAC loopback resource URLs; guard-readiness checks; four concurrent fetch slots; 1 MiB manifest and 8 MiB segment limits; and independent 12-second total manifest/segment fetch budgets with DNS-worker cancellation/reaping.

**Permanent-use gap: the relay still enforces a cumulative process-wide 1,200-fetch-attempt budget.** The next attempt fails closed with `request_budget`. Removing session expiry did not remove this cap. The retained no-expiry relay therefore cannot be presented as indefinitely available. Before rollout, explicitly review a minimal long-running request-budget policy and its bounded resource/telemetry behavior. Do not silently remove this limit, reset it through restart loops, or weaken destination/TLS/deadline checks. Any authorized source adjustment needs a new digest and focused offline regression; that is a deliberate difference from the successful trial.

No broadcaster, manifest, segment, DNS destination or playback request was made in this review. Current source reachability and future broadcaster URL stability remain untested.

## 4. Routing and Jellyfin settings

The tested chain is:

```text
Jellyfin
  -> Rivendell LAN :9191 /proxy/ts/stream/<channel UUID>
  -> existing VPN-owner published :9192 Caddy listener
  -> Dispatcharr loopback TS proxy
  -> built-in FFmpeg streamcopy profile
  -> opaque loopback HLS relay :19193
  -> approved broadcaster HTTPS through the dedicated VPN
```

Caddy does **not** point directly at the HLS relay. The relay serves HLS to Dispatcharr; Caddy delivers the resulting MPEG-TS to Jellyfin.

The retained trial gateway points to loopback **19191**, the disposable AIO port. The accepted AIO listens on **9191**. Sanitized comparison confirms that, ignoring comments/whitespace, the trial Caddyfile differs from the current file only in backend port and stripping `X-Real-IP` in both proxy blocks. It also matches the retained Phase 5A gateway hash.

Preserve HTTP/1 framing, immediate flushing, 5-second connect and 120-second response-header allowances, successful MPEG-TS filtering, response-header/trailer filtering, redirect rejection, blocked alternate media/direct routes and locally reconstructed forwarding identity. For the smallest production adaptation, keep the accepted AIO on 9191 and add the tested two `header_up -X-Real-IP` directives. Do not copy the trial 19191 upstream unchanged or install its alternate nginx/uWSGI/start scripts. This production-port adaptation requires a new reviewed gateway hash and fixture acceptance.

Validated Jellyfin settings were:

- M3U tuner using local `/config/iptv/phase5b/dispatcharr.m3u`; one channel, number 9001, DW English (Phase5B Test).
- TunerCount 1; AllowStreamSharing true; EnableStreamLooping false; AllowHWTranscoding false; ImportFavoritesOnly false.
- XMLTV provider using local `/config/iptv/phase5b/guide.xml`, EnableAllTuners false and EnabledTuners restricted to that tuner; ChannelMappings empty.
- Matching tvg-id `dw-english-phase5b`; one explicitly labeled placeholder programme, not an official broadcaster schedule.
- Only TunerHosts/ListingProviders changed. Libraries, users, playback defaults and DVR configuration were preserved. Unsupported EnableTvgId was not retained.

The trial DB, generated secrets, opaque relay state, channel/stream rows and Jellyfin exports were deliberately removed at closure. The trial API device/token was revoked. Retained JSON/configuration receipts remain; this is expected cleanup, not unexplained loss. Restore equivalent settings with newly generated stable channel identity and permanent local paths; do not replay expired tokens, ephemeral relay URLs or stale guide dates. A real renewable guide/export policy is still required; replaying the historical placeholder is not permanent guide service.

## 5. Credentials and private inputs

Existing root-private `private/app.env`, dedicated `private/wg0.conf` and `private/dw-english-phase4d-20261108/relay-private.json` remain mode 0600. The source reference is HTTPS on the expected host with no query/fragment. Its value was not exported.

Local owner-login references remain mode 0600 at `.ai-local/dispatcharr-phase5a/jellyfin-login.json` and `.ai-local/dispatcharr-phase4d/dispatcharr-api-login.json`. No login or token creation was attempted. File presence does not establish valid current credentials or authority in the accepted AIO; the old Dispatcharr trial login must not be assumed to authenticate there.

A later rollout needs the owner's valid Jellyfin management session, accepted-AIO administrative API access, existing DB/Redis/Django secrets, dedicated WireGuard keys and protected source configuration. Relay session/HMAC identifiers are generated runtime secrets, not durable values to copy from logs. No provider subscription credential is introduced by this one-channel DW plan. Keep all values outside Git, command arguments and published logs.

## 6. Exact minimal deployment changes — proposed only

Use the existing project and persistent AIO data; retain VPN owner/network/port publication, nftables policy, DNS/IPv6 protections, resource-admission helper/thresholds and unrelated media services.

| Existing location/component | Necessary change |
|---|---|
| `compose.proposed.yaml` Dispatcharr image | Pin the retained patched local image by immutable identity; keep current AIO ports, env, persistent data and VPN startup gate. No build/pull or release upgrade. |
| Relay source/runtime | Stage the verified source/dependencies in a permanent read-only bundle, incorporating only a separately reviewed request-budget adjustment if approved. Use the same retained image as Python runtime. |
| Existing Compose project | Add one managed relay service sharing `service:iptv-vpn`, with no published ports/new network, restart=no, unprivileged UID 1000, dropped capabilities, read-only source/config/resolver/guard mounts and private writable runtime state. Select explicit resource bounds during candidate review. This is lifecycle packaging of the existing relay, not a replacement implementation. |
| Relay startup/health | Feed protected JSON on stdin as before; require guard/VPN readiness. Check fresh nonfatal stats, expected loopback listener and current endpoint without fetching its manifest. Persisting an old PID/endpoint file is not health. |
| Startup endpoint registration | After relay and AIO/backend readiness, a scoped release-matched API helper must ensure the single channel/stream and bind its URL to the relay's **new** opaque endpoint each start. Preserve FFmpeg profile 1; no Redirect mode or direct broadcaster URL in Dispatcharr/Jellyfin. This helper is not yet implemented/reviewed. |
| Gateway Caddyfile | Keep backend 9191 and apply the tested two identity-header removals; retain all existing response/route filters. Never forward Jellyfin directly to relay :19193. |
| `minimal-phase6b3d/verify.py`, `contracts.py`, manifests | Replace the accepted Dispatcharr image pin; add explicit relay service/image/name, mounts, restart policy, namespace and readiness checks; update the gateway source pin and affected manifest hashes together. Preserve exact nftables semantics. |
| `dispatcharr-stack.service` | Preserve all four prestart stages including unchanged admission. Adapt managed start to AIO+relay readiness, scoped endpoint registration, then gateway readiness; include relay in scoped failure/stop cleanup and final verification. Keep unit timeouts unchanged. |
| One-time rollout transaction | Existing `--no-recreate` cannot replace the old image or apply new mounts. In a separately authorized maintenance window, stop only the protected unit, stage the affected containers **stopped** against the reviewed Compose files, then let the unit perform admission/start. Retain the exact VPN owner and shared-namespace references. Never bypass admission with a direct container start. |
| Dispatcharr settings | Restore only one DW channel/stream and exact observed local STREAMS ACLs. Trial allowed loopback, Rivendell, bridge-gateway and observed Jellyfin addresses; reobserve current peers instead of copying an old container IP. Keep M3U/EPG and XC API restricted. |
| Local exports/Jellyfin | Atomically generate sanitized local one-channel M3U/XMLTV at stable permanent paths, with explicit guide renewal; use the supported configuration API to change only tuner/provider arrays and refresh discovery. Capture current before-images first. |

The added relay service and registration stage are **not currently covered by the installed three-container contract**. The existing verifier intentionally rejects another Dispatcharr image; its hash pins intentionally reject an altered gateway. These are required security-contract updates, not reasons to disable checks.

Because the relay URL changes on process restart and the gateway must not serve a stale binding, detached `docker exec -d` is insufficient permanent lifecycle management. Do not reuse the completed trial cleanup/watchdog: it targets disposable names, restores historical Jellyfin state and can remove trial resources. Use scoped project-managed start/stop/failure ownership. No additional host daemon, network, VPN or firewall allowance is needed.

## 7. Acceptance criteria for a separately authorized deployment

1. Normal systemd admission succeeds without changed thresholds/timeouts; missing guard, wrong namespace/image/source hash or failed registration refuses exposure and stops only protected components.
2. PostgreSQL/Redis authenticate; no unexpected/pending migrations; both uWSGI workers have fresh Redis-backed heartbeats and default/DVR Celery workers respond. No retained NoneType Redis-reference failures.
3. Dedicated VPN healthy; broadcaster traffic uses tun0; normal exit, DNS/IPv6 and exact nftables contract pass. Any deliberate outage/leak test needs explicit authorization; normal-path checks alone are not universal leak proof.
4. Relay health performs zero source fetches. Destination, redirect, malicious-DNS, forbidden HLS-tag and finite-fetch behavior pass focused offline fixtures before live use. Request-budget behavior matches the approved long-running policy.
5. Gateway health 200 and native synthetic security/framing cases pass; canonical stream only, forged identity removed, no upstream URL/secret/redirect leakage.
6. Jellyfin discovers exactly DW English 9001 and its current mapped guide. Only intended tuner/provider fields differ; unrelated settings/users/libraries and no-DVR state remain intact.
7. One owner-authorized playback sample demonstrates actual H.264 720p50/AAC media, Dispatcharr streamcopy and Jellyfin codec-copy remux/direct streaming. Classify codecs from actual FFmpeg/session evidence, not a generic “Transcode” session label. No unexpected re-encoding or persistent visible buffering; compare startup observations with the 17.523/19.910-second trial baseline without increasing deadlines to force a pass.
8. User-observed playback plus bounded server telemetry covers a representative sustained interval, request-budget behavior, close/reopen and stop. No extra automated consumers, warning-driven restart loop or invented first-frame measurement.
9. Clean stop cancels/reaps relay fetch/DNS work and producers; no media children, stale channel session keys or consumers remain. A separately authorized protected-stack recovery generates a new endpoint, rebinds it, passes admission and restores health without touching Jellyfin playback defaults or unrelated containers. Host reboot is a separate acceptance action.

These are future requirements, not tests performed by this read-only review.

## 8. Rollback

Before authorized deployment, save fresh exact before-images of current Compose, gateway, verifiers/contracts/manifests, unit/drop-ins, image identities, scoped Dispatcharr records/ACLs and current Jellyfin tuner/provider configuration. Revalidate the existing recovery reference as required by that change window; this review created no backup or restore exercise.

If acceptance fails, terminate only the authorized test playback and stop the protected unit through systemd. Restore the original AIO image, original gateway file, exact prior three-service Compose and matching verifier/unit/manifests atomically; remove only the stopped newly added relay resource. Preserve VPN owner identity, guard, data and unrelated containers. Restore only the captured channel/stream/ACL and Jellyfin tuner/provider changes using supported APIs with conflict checks. Regenerate/restore exports consistently. Start through the unchanged admission gate only when that rollback action is authorized; stop after bounded failure rather than retrying or relaxing policy.

The patch changes source, not schema, and the base/dependencies match; nevertheless unexpected migrations invalidate image-only rollback. Preserve failed state and obtain authorization for any matched DB/assets recovery rather than wiping data, importing old trial DBs or overwriting current Jellyfin with its historical full backup. Existing recovery artifacts remain references; no restore was performed. Do not invoke the old completed Phase 5 cleanup against production.

## 9. Recommendation and remaining prerequisites

**Verified reusable:** exact patched image, matching build context/overlay, relay source plus documented lifetime edits, matching dependencies, trial gateway/settings evidence and current healthy protected architecture. No rebuild, replacement upstream image or streaming redesign is justified by these checks.

**NO-GO for immediate permanent deployment** until:

- A reviewed permanent request-budget policy resolves the retained 1,200-attempt process cap.
- Managed relay health/start/stop and fresh-endpoint registration are implemented and reviewed with the four-service security contract and unchanged admission gate.
- Current accepted-AIO/Jellyfin management access is verified privately; channel/ACL identities and stable export/guide renewal are specified.
- The production-port gateway adaptation and new lifecycle checks receive focused offline validation.
- The user authorizes deployment, playback and scoped rollback/recovery acceptance.

No container lifecycle, build/pull, live configuration, Jellyfin, firewall/VPN, infrastructure, playback or backup/restore action occurred. Remote inspection emitted sanitized flags/hashes rather than raw private configuration. **Stop after publication; await deployment authorization.**

