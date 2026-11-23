# Dispatcharr → Jellyfin integration — partial success; playback not verified

**Later verification:** the owner subsequently confirmed successful interactive picture/audio, fast startup and no buffering. Legacy Jellyfin xTeVe references were then removed after fresh checks; persistence was retained under the explicit ownership-inventory exception. See [final verification and retirement](dispatcharr-xteve-retirement.md). The dated API-client test and its limitations below remain historical evidence.

2026-11-17 UTC. Rivendell `10.10.20.30`, Andrew's selected access. Protected running release `227122dcbe9ebc76be46b8a91231350d6c93bdb4`; prior deployment report `779b8388882c0e581ab7bdbc9b1228ca11983bc1`.

**Integration PASS; bounded playback test FAIL; overall acceptance FAIL. NO-GO for xTeVe retirement.** DW English is configured and discovered in Jellyfin with its explicitly labeled placeholder guide. The one authorized live attempt stopped at the API client's capability-negotiation gate, before requesting/decoding client media. It was closed without retry. The permanent four-service stack remains healthy; working integration configuration is preserved. This result does not establish that Jellyfin's interactive web player would fail.

## Preflight and preserved state

At **15:30:22 UTC**, all four protected services were healthy with the same identities as deployment acceptance. The 67 installed source/target pins and corrected running verifier passed. Trusted guard/grant generation, actual VPN namespace, nftables policy, DNS and IPv6 restrictions remained valid. PostgreSQL/migrations, authenticated Redis, two fresh uWSGI heartbeats, and Default/DVR Celery passed independent checks.

Supported Dispatcharr API detail reads matched owned channel **3** and stream **3** exactly; the complete hidden-inclusive inventory contained only that pair, without shared references. The active opaque endpoint/UUID/export binding agreed, with no pending registration/rollback transaction. The local M3U/XMLTV pair was Jellyfin-readable and current. The observed XMLTV window was 2026-11-17 14:00 UTC through 2026-11-19 15:00 UTC, showing renewal since initial deployment. Relay media fetch count was zero before the live attempt.

Jellyfin **12.0.0** authentication verified the existing administrator against the selected server. No current playback or recordings existed. Exact Live TV and general configuration before-images, channel inventory, scheduled tasks and container inspection were preserved privately before mutation. No credentials or authentication settings were changed; no new API key was created.

Configuration identity uses SHA-256 of canonical, sorted, compact JSON:

| Identity | Value |
|---|---|
| Previous Live TV configuration | `25d8c40b72f540594838e5ad0cd70ca3752de2cf293491cda521e11814a1d14c` |
| Preserved working configuration after integration | `0ef993273eb4cbb5019926f5fa8387130e4ebc281d39651ef9d534a610b00854` |
| Original xTeVe tuner/provider rows | `9a21439251f8906f290f9a66c1ce2973afd40cc7eab37b5f8a0543d2b5cb8046` |

Scoped recovery is available from the private exact before-image. Before any separately authorized undo, compare current Live TV configuration with the latest verified after-image, including the mapping/priority transactions; refuse concurrent differences. A supported configuration POST can then restore the captured before-image and refresh the guide, preserving original rows. Do not blindly invoke the initial helper rollback: its original after-image predates the explicit mapping and provider placement described below. No database reset or filesystem replacement is needed or authorized.

## Tuner, guide and discovery

The reviewed `jellyfin.py` helper added one tuner and one provider while preserving existing entries. Stable paths are inside Jellyfin's existing `/config` mount:

| Component | Identity/configuration |
|---|---|
| New M3U tuner | `84512b75-27af-509d-9377-a29982f9722b` |
| Playlist | `/config/iptv/permanent-dw/current/dispatcharr.m3u` |
| New XMLTV provider | `fa590b78-e345-5343-b34d-9c7b4c5f10db` |
| Guide | `/config/iptv/permanent-dw/current/guide.xml` |
| Jellyfin channel | `67d9ed9926f9e1ef90002ff7dbfd790f`, **DW English**, number **9001** |
| XMLTV channel ID | `dw-english-permanent` |
| Explicit tuner-channel mapping | `m3u_72bdf3377216078a211cff2d20374229c8ace81a7c8cf374c785569d08a13c9e` → `dw-english-permanent` |

TunerCount=1, stream sharing=true, looping=false, hardware transcoding=false, import-favorites=false. The new provider enables only the new tuner; EnableAllTuners=false. Existing tuner/provider entries and mappings were retained exactly. There are now two tuners and two providers, with exactly one discovered channel. No library, user, DVR, playback-default or general Jellyfin setting was modified.

**Guide conflict and scoped resolution:** initial discovery found the channel but no programme. The existing xTeVe guide has EnableAllTuners=true and references an unreachable port 34400. Logs showed its connection refusal aborting programme lookup before the new provider could return programmes. An explicit mapping alone did not resolve that ordering issue. The supported API was used to add only the new mapping, then place the **new tuner-scoped provider first**, leaving every original xTeVe row/mapping value unchanged. The old provider's relative order among old entries was preserved.

This ordering behavior is consistent with the upstream [ListingsManager programme lookup](https://github.com/jellyfin/jellyfin/blob/master/src/Jellyfin.LiveTv/Listings/ListingsManager.cs), which checks enabled providers in configuration order and returns the first available programme set. The actual server logs and fresh guide reads are the live evidence here; the upstream source is explanatory, not a pinned-source attestation of the installed assembly.

At **15:39:10 UTC**, refresh completed and the channel associated with **“DW English live stream — placeholder, not a programme schedule.”** This is renewable availability information, not broadcaster EPG listings. The existing RefreshGuide interval remains **24 hours** and its latest execution completed; the relay's existing local XMLTV writer renews hourly with a 49-hour window. No timer or schedule was added/changed.

The original helper's desired mapping was empty. The additional supported-API transactions and latest after-image are retained separately; blind reapplication of that helper now correctly conflicts with the explicit mapping. A future helper update/review should incorporate the observed mapping and priority requirements. No protected candidate source was changed during this task.

## One bounded live attempt

Browser access was unavailable. The test therefore used a dedicated authenticated Jellyfin API client, rather than claiming an observed interactive UI session. The plan was one PlaybackInfo/source-open request, Jellyfin's normal static streaming endpoint, bounded video/audio decoding, and explicit stop/close. Maximum wall budget was 90 seconds; target decoded media duration was 20 seconds. No broadcaster URL or relay endpoint was requested directly by the client.

**Only one attempt ran, 15:41:27–15:41:33 UTC (5.562 seconds).** The request advertised a transport-stream/H.264/HEVC/MPEG-2 and AAC/MP2/MP3/AC-3/E-AC-3 capable client, with direct play/stream and streamcopy enabled. Transcoding was disabled **for this request only**, without changing saved playback defaults.

Jellyfin returned a source/live-stream identity and no API ErrorCode, but reported **SupportsDirectPlay=false, SupportsDirectStream=false, SupportsTranscoding=false**, with RequiresOpening still true. The client refused those preliminary capability flags. It did **not** issue a subsequent client media GET or launch its A/V decoder. The reported source stream indexes were -1; these are not treated as verified decoded-media metadata.

| Measurement | Result |
|---|---|
| Time to first picture | Unavailable: no decoded/rendered client video |
| Video metadata reported by Jellyfin | H.264 High, 1280×720, 50 fps, nominal 8 Mbps; preliminary |
| Audio metadata reported by Jellyfin | AAC-LC, stereo, 48 kHz, nominal 128,215 bps; preliminary |
| Direct play/remux/transcoding | No client playback method established; no transcoding verified/performed by the test |
| Buffering/interruptions | Not measurable without delivered client playback |
| Client decoded frames/audio samples | Not verified |
| Relay effect | **2 requests: 1 manifest, 1 segment, 2,630,249 bytes** |
| Relay fatal/rejection state | Fatal=null; no rejection counter recorded |
| Stop/close | Supported stop and close calls completed without error; no retry |

This isolates the failure boundary to **the bounded test client's handling of the returned live-source capabilities/open state**. It is not evidence of an upstream codec fault or a broken VPN. Further diagnosis should use an available normal Jellyfin client or complete the supported live-open flow under **fresh authorization for another test**. No such follow-up, codec conversion, timeout adjustment, source substitution or security relaxation was attempted.

## Path, security and post-test acceptance

Opening the Jellyfin source caused the two relay fetches. The playlist contains only the approved Caddy gateway TS URL. During the attempt, the Dispatcharr FFmpeg process was observed consuming the loopback enforcement relay with **`-c copy`**. The relay's observed public peer routes resolve through **tun0** in the shared VPN namespace. These configuration/process/telemetry observations support the intended Jellyfin → gateway → Dispatcharr → relay → VPN path for source opening; they do not establish successful rendered playback.

At **15:44:35 UTC**, the test stream was closed, Jellyfin had zero active playback sessions, and no Dispatcharr FFmpeg/FFprobe process remained. The 67 pins, four-service running/security verifier, worker readiness, trusted grant, firewall/VPN/DNS/IPv6 checks passed. Relay counts remained the two bounded requests, with no fatal state. No additional playback or fetch test followed.

All container IDs, configuration/mount hashes, start times and restart counts remain unchanged. Docker process and network identities and unrelated media services are unchanged. General Jellyfin configuration and unrelated Live TV top-level fields/rows match their before-images. The permanent integration and current placeholder are preserved; the legacy xTeVe entries are untouched. No deployment, restart, unit/guard change, image operation, VM operation or new infrastructure occurred.

## xTeVe retirement inventory — untouched

| Reference/dependency | Observed state |
|---|---|
| Legacy Jellyfin tuner | M3U ID `e6c7eb23c33b4be996444b5564611bb2`, source at `10.10.20.30:34400`; preserved |
| Legacy XMLTV provider | ID `aaf9c49c3e204ba3a64f23dc19226709`, same host/port, EnableAllTuners=true; preserved |
| Legacy channel mapping | `m3u_a7b38ddb7c80f3d2f2e378c282f3b79e0a679898bc5fa863dd0760a60e647840` → `1007`; preserved |
| Port 34400 | No listening socket observed; source/guide refresh attempts receive connection refusal |
| Docker containers/Compose | No xTeVe-named/image container, including stopped containers; no xTeVe reference in current Compose label paths or scanned top-level Docker configurations |
| Named Docker volumes | No xTeVe-named volume; no unassociated volume was inferred to belong to it or removed |
| Persistence | `/docker/xteve`, owner 1000:1000; `config`, `demo`, `tmp` subdirectories retained |
| Config files | `/docker/xteve/config/demo.m3u`, 125 bytes; `/docker/xteve/config/demo.xml`, 328 bytes; no other files in the observed tree |
| Units/cron/scripts | No xTeVe-named unit file or matching reference in scanned systemd/cron/selected Docker scripts; root and murth have no installed crontab |

Persistence hashes: demo.m3u `b0ffe31bed0ebd70604aebd4b839f0246a4cfe0c2c6cb3c289193ed875dfa1b9`; demo.xml `7de3c1eb0b4be95ef29e83f70564b6c16e2fda73099c80941ac059ab831700f8`. Contents/source URLs are not published.

Inventory bounds: current Docker container/volume metadata, Compose paths declared by running containers, top-level `/docker` and selected scripts/maintenance locations, `/etc/systemd/system`, cron directories, named unit files, and the confirmed `/docker/xteve` persistence tree. This is not a claim that unknown external automation or unidentified orphan volumes do not exist. Nothing was stopped, removed, edited or renamed for retirement.

## Evidence and decision

Root-private before/after images, transaction/mapping/priority receipts, running API schema, discovery, playback response/monitor/stop diagnostics, xTeVe inventory and final verification are retained under `/docker/dispatcharr-iptv/private/jellyfin-integration-227122d-20261117/` (0700 directory, 0600 files). Credentials, tokens, broadcaster URLs, relay endpoints and raw private responses are excluded from publication.

**Overall FAIL / partial integration success. NO-GO for xTeVe retirement.** Tuner, explicit mapping, placeholder discovery and protected-backend/security acceptance pass. Video and audio playback acceptance remains unmet. Preserve the working configuration and four-service stack; request separate authorization for another bounded client test before considering xTeVe cleanup.
