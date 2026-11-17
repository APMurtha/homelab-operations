# Native Xtream and XMLTV security hardening

2026-11-17. Repository `APMurtha/homelab-operations`, branch
`docs/udm-pro-max-migration-prep`. Starting native adapter `04e8295`.
Production release remains `227122dcbe9ebc76be46b8a91231350d6c93bdb4`.

**PASS for offline implementation and regression acceptance. GO for source/security
review and a separately authorized image-build/integration-test stage. NO-GO for
installation or a real-provider metadata test now.** The patched server has not
been built or installed; live CLI mutations and native deletion remain disabled.
No production filesystem, container, unit, firewall, VPN, DNS, Jellyfin or provider
was accessed or changed. No real credential was entered or installed.

## Architecture and exact source basis

The candidate is under `configs/dispatcharr-iptv/native-provider-hardening/`.
It modifies eight exact source inputs, adds five runtime modules and an image-local
source-hash manifest, and updates the existing native adapter's preflight and EPG
sequence. No proxy, daemon, listener, Docker network or privileged relay is added.
The current broadcaster-specific DW English relay remains unchanged.

Source is pinned to Dispatcharr
[`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`](https://github.com/Dispatcharr/Dispatcharr/tree/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e).
The base image contract remains the previously verified readiness-patched AIO
`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
That image does **not** contain this hardening. There is no new image ID/digest yet.
The existing readiness fix must be preserved in any future build.

`source-pins.json` contains exact input SHA-256 values; `output-hashes.json`
contains all 13 resulting Python-file hashes. `server.patch` is the reviewed
unified patch, including the new runtime files and `provider_contract_hashes.json`.
`prepare.py` checks every input before writing a new offline output directory.
Tests apply the actual patch to a temporary source copy and verify every output.
The bundle-local .gitattributes treats mandatory unified-diff context whitespace
as artifact data; Python/source whitespace checks remain enabled.
A source/image mismatch must stop a future build; these pins must not be
regenerated to accept unexplained differences.

Additional side-effect source reviewed is pinned in `audit-source-pins.json`.
The deployed architecture was reviewed from repository contracts/reports; this
work makes no claim of fresh live health or file inspection on Rivendell.

## Actual outbound request inventory

| Entry/path | Execution and native side effects | Candidate enforcement |
|---|---|---|
| XC account creation | API process commits account, then the original create method synchronously calls refresh_m3u_groups, including authentication/category GETs even when inactive; default profile and account-group relations are created | Default create makes no XC request. Only explicit metadata_discovery=true enters an approved discover job. Creation may still commit before a subsequent discovery failure; ownership journal rules remain essential |
| XC authentication/categories | core.xtream_codes.Client authenticates with player_api.php credentials and requests get_live_categories | Central xc_get uses the checked AirVPN metadata transport; no requests.Session retry/redirect path remains |
| Full XC stream refresh | Manual API enqueues refresh_single_m3u_account; worker may rediscover groups, authenticate, get_live_streams, persist enabled-category stream metadata, perform account-scoped stale cleanup and call auto-channel sync | Manual API passes operator_requested=true; worker requires approval, active account, matching resource identity and current namespace grant. Existing explicit group selection/disabled auto-sync controls remain mandatory |
| Automatic profile refresh/account-info | Category discovery previously queued refresh_account_profiles; profile transformations can change server URLs/credentials; profile-info API queues a separate task | Automatic profile enqueue is removed. Both native profile-refresh task bodies return a fixed disabled result; they do not load credentials or contact a provider |
| Periodic XC refresh | M3U signals create/update Beat rows based on is_active | XC schedules are disabled regardless of is_active; existing queued/default task calls lack explicit operator authority and fail before lock/network work |
| Remote XMLTV create/import | Active source creation previously queued refresh; manual import queues refresh_epg_data; source tasks call requests.get and support compressed archives | Remote auto-create refresh and schedules are disabled. Explicit source-ID import enters an approved EPG job, uses the same checked transport, accepts bounded plain XML and atomically publishes a validated cache |
| Missing cached XMLTV | Channel/programme parse functions can call fetch_xmltv when a cache is missing | The first branch of fetch_xmltv intercepts every remote URL. Without an approved EPG job context the fetch refuses; there is no fallback to legacy requests.get |
| Channel mapping/programme parsing | Channel post-save queues parse_programs_for_tvg_id; that worker can download missing source data | Remote per-channel automatic parse returns without fetching. Native adapter explicitly imports EPG again after owned channel mappings exist, through the journaled manual API |
| Programme index work | Source import queues local programme index building; cache deferral can requeue tasks | Index work reads the validated local cache; any remote fetch still needs current job scope. Deferred remote refreshes do not inherit operator authority and refuse, rather than silently retry |
| EPG artwork/series evaluation | Parsed icon URLs can become channel/logo metadata; source completion queues evaluate_series_rules | Remote import strips icon/image/url XML elements, clears XC artwork/unknown URL fields, skips automatic EPG logo application and does not enqueue DVR-rule evaluation |
| Remote non-XC playlist downloader | Separate requests.get path in M3U tasks could bypass the XC client | Refused in this candidate. Local/custom DW streams are not remote playlists and do not enter this downloader |
| VOD/series metadata | Other XC methods also use the same client | Unsupported actions refuse at the central transport; only authentication and live-category/live-stream metadata are approved |
| Future native media/DVR/artwork | Native records can contain private credential-bearing TS URLs; existing recording/artwork paths use other clients/FFmpeg | Not activated or authorized by this work. Existing shared VPN namespace/kernel enforcement remains required. The broadcaster relay and Jellyfin exports are not extended |

The trace follows the pinned
[M3U API](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/api_views.py),
[M3U tasks](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/tasks.py),
[XC client](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/core/xtream_codes.py),
[EPG tasks](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/epg/tasks.py),
[channel signals](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/signals.py),
[channel utilities](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/utils.py)
and [channel tasks](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/tasks.py).
This is the Xtream/XMLTV onboarding path, not a claim that every unrelated
Dispatcharr HTTP feature has been rewritten. Schedules Direct and unrelated local
source/background functionality retain their existing implementations.

## AirVPN-only network and trust model

All provider metadata/EPG operations must run in the **existing Gluetun AirVPN
network namespace**, shared by the AIO's API and Celery processes. The accepted
host nftables guard and VPN firewall/routing remain essential; no rule, endpoint
allowlist or WireGuard configuration changes are included here. Application
checks supplement that kernel boundary and cannot replace it.

A future root-owned 0700 policy directory at `/run/dispatcharr-provider` supplies
one root-owned, single-link, regular 0600 JSON file per provider key. No symlink or
writable/untrusted ancestor is accepted. The policy is at most 64 KiB and has an
exact schema. It binds AirVPN ownership, current host boot and actual namespace,
a distinct host namespace, the reviewed guard policy digest, provider identity,
exact XMLTV URL digest, permitted operations and expiry within 24 hours. The
example is invalid/expired and contains placeholders only. No policy was installed.

Account identity is the canonical server/username digest already used by the CLI;
EPG identity additionally matches the exact private URL digest. Approvals enumerate
exact HTTPS host/path pairs and public IPv4 sets. Each request validates current
approval, namespace, loopback-only resolver configuration and disabled IPv6;
DNS answers must be global IPv4 addresses within the approved set. A read-only
root-owned ip executable must report tun0 for the chosen address. No host WAN,
private/link-local/loopback provider destination, proxy, alternate resolver,
second hostname resolution or redirect fallback is used.

DNS makes one bounded A-record UDP exchange with the existing Gluetun loopback
resolver, with a five-second timeout and 16 KiB/record/pointer bounds. It does not
fork or spawn a worker, so it works with Celery prefork/daemonic execution. There
is no search-suffix or external-resolver fallback. CNAME responses may supply
approved A answers; a response without usable approved A records refuses. IPv6
transport is not supported. The checked IP is used directly for TCP while TLS
retains the original hostname/SNI and normal certificate trust validation.

The server reuses an exact copy of the accepted public guard/grant reader against
read-only `/guard-status`. It verifies the stable directory anchor, file ownership,
modes, link counts, no-follow lookups, current boot, expected policy digest,
matching generation and the process's actual namespace. A generation is pinned
for each job. Approval/status is checked before requests, during socket waits and
reads, and before returning data. Replacement, withdrawal, expiry or inconsistent
state refuses on the next check.

AirVPN ownership is an assertion grounded in the accepted Gluetun/WireGuard
configuration and trusted grant lifecycle, not an inference from tun0's name
alone. The public marker does **not** continuously attest the kernel firewall,
VPN provider or owner container. Existing asynchronous cleanup and check-to-use
windows remain. Revocation cannot retract sent bytes, cancel committed database
writes or guarantee instantaneous termination of a request/parse. A future
installation must verify the actual owner/configuration and full kernel contract.

## HTTP, XML and credential controls

The server uses a stdlib, pinned-IP HTTPS client with nonblocking TLS/socket I/O.
It has no automatic retry, proxy inheritance or redirect following. Bounds are:
five seconds for DNS, five seconds for connection/idle socket stages, a 30-second
absolute request deadline including authorization/headers/body, 64 KiB initial
wire/header allowance, 16 MiB response/body bounds, two in-flight requests per
process and at most 32 requests per approved job. Limits are not a cluster-wide
rate quota or a promise of exactly-once distributed task delivery. Existing
worker/container resource constraints remain unchanged.

Only HTTP 200 is accepted. Declared oversized data, truncation, compression,
redirects, malformed framing, DNS changes and certificate/hostname failures
refuse. Chunked identity responses are supported. The approved mode is HTTPS/443;
HTTP, other ports and incompatible provider formats require review rather than
relaxing TLS or destination checks. The old broadcaster allowlist is untouched.

Xtream credentials remain in TLS-protected in-memory protocol query parameters,
as required by the native API; they never enter process arguments or progress
output. Private media URL metadata now percent-encodes credential path segments
and validates IDs/extensions. Constructing such a URL grants no playback authority.
Unknown direct-source/artwork URL fields are discarded from live-stream metadata.

Credential-bearing modules use fixed-message logger wrappers, suppress raw
tracebacks/provider responses and unstructured progress/system-event bodies, and
store fixed safe error/status messages. A diagnostic helper that printed stream
fields is disabled. This deliberately reduces detailed native-provider logging;
status/IDs and the CLI's durable receipts remain available. The contract endpoint
requires DEBUG=false. Future deployment must also verify existing request/task
logging does not log POST bodies or private administrative responses. Admin
account detail responses still contain credentials under the existing supported
API; the private client must continue to avoid printing them.

Remote XMLTV must be plain UTF-8, at most 16 MiB, well formed with tv root, no
DTD/entities, unique channel IDs, at most 100,000 elements, depth 64, bounded
attributes and text. External entities are never resolved. All native lxml
streaming/programme parsers explicitly disable entity/DTD loading, network access,
recovery and huge-tree mode. Compressed remote archives are intentionally refused,
so there is no decompression bomb/extraction path. Providers requiring compressed,
DTD-bearing or larger guides are unsupported pending a separate bounded-format
review; no real-provider compatibility was assumed.

Guide text/IDs are preserved; external icon/image/url elements are removed, not
replaced with invented listings. Cache publication is atomic with a fsynced 0600
file, and stale extracted-file pointers are cleared. At most one crash-retained
native partial exists per source; a preexisting partial is neither overwritten nor
deleted and requires reconciliation. Cache filesystem and database publication
are not a single transaction; an interrupted result must be inspected.

## Scheduling, activation and native adapter

XC account creation is network-silent by default. The adapter explicitly sends
metadata_discovery=true; only the root-approved discover job may synchronously
contact that provider. It may still leave a committed account if subsequent
discovery fails. No uncertain POST is retried.

Manual M3U refresh and EPG-import APIs enqueue operator_requested=true. Their
worker defaults are false, and remote jobs require the matching active resource,
approval and grant. XC and remote XMLTV Beat schedules remain disabled even while
is_active=true; existing default/periodic calls refuse. Automatic profile enqueue
is removed and profile task bodies make no network requests. Remote per-channel
programme jobs are no-ops. Existing Celery time/soft limits are unchanged; the two
manual network tasks explicitly use early acknowledgement, no worker-loss reject
and no autoretry. Broker/task outcomes are still reconciled rather than assumed
exactly once. Lock/defer paths do not silently reauthorize remote work.

Temporary account/source activation permits an explicitly requested metadata job;
it does not enable a periodic schedule. Deactivation prevents new approved refresh
jobs, but is not instantaneous revocation of an already running job. Withdraw the
root approval to stop further network checks; retain the known race limitations.
No unrelated worker, DVR setting or Jellyfin configuration is disabled/changed.
Remote imports themselves do not enqueue DVR-rule evaluation or artwork work.
Existing independent DVR rules/consumers must still be inventoried before any real
onboarding to ensure they cannot target new metadata channels.

The new admin contract is implemented, not guessed:

`GET /api/core/provider-security/?provider_key=<SHA256>&epg_url_sha256=<SHA256>`

It verifies root approval, guide binding, current namespace/guard and actual source
hashes without contacting the provider. The CLI checks the exact reviewed 13-file
hash map and feature set, provider/guide hashes, expiry and generation assertion
before native registration/refresh; the assertion is retained privately. This is
a trusted authenticated server assertion, not independent remote attestation.
Image/source/namespace verification is still required at deployment.

After owned channels are mapped, the adapter issues a second explicit journaled
EPG import to parse their programmes, replacing the now-disabled automatic remote
per-channel job. The workflow still returns account/source inactive, keeps channels
hidden with no channel-profile exposure, preserves exact native IDs and mappings,
and refuses shared/conflicting resources. Journals and no-blind-retry behavior
remain. Native removal is disabled.

The contract's media_activation=false describes this onboarding mode's lack of
media authorization; it is not a new global playback firewall inside Dispatcharr.
No provider is exported to Jellyfin or routed through the DW English HLS relay.
Future media must retain AirVPN-only routing and receive its own format/destination
review and explicit activation authorization.

## Offline tests and compatibility

**497 tests pass: the full existing 405-test baseline plus 92 new regressions.**
No failures, errors or skips. Machine-readable counts/log hashes are in the bundle's
`validation-results.json`.

| Suite | Tests |
|---|---:|
| Existing provider/native-adapter baseline | 127 |
| New CLI hardened-server/guide/source-contract checks | 12 |
| New server policy/client/XML/scheduler/patch/application fixtures | 66 |
| New real TLS/DNS/guard tests in an unrouted user/network namespace | 14 |
| Existing permanent/security/lifecycle/guard/admission groups | 39 + 26 + 17 + 7 + 3 + 12 + 28 + 50 + 13 + 15 |
| Existing historical persistence / prior guard / lifecycle design | 26 + 14 + 28 |

Tests execute the prepared XC client with synthetic auth/metadata, actual prepared
account-create/task entries against mocked dependencies, source-pin rejection and
actual patch application/hash verification. They cover inactive/explicit creation,
periodic/profile/worker restrictions, activation/deactivation, guide identity,
credential-safe exceptions/logs, artwork/DVR suppression, DNS rebinding/private
answers, host-route refusal, stale namespace/policy, malformed/deep/oversized XML,
atomic private caches and crash-retained partials. Existing native registration,
ownership/recovery, DW English and protected infrastructure regressions pass.

The network suite uses real TLS sockets and certificates to test certificate and
hostname validation, redirect refusal, chunked/truncated/oversized responses,
header/idle deadlines and mid-fetch revocation. It uses real UID-0-in-user-namespace
guard files, actual namespace IDs and a synthetic loopback DNS wire exchange.
The namespace has no external default route. Only the loopback TLS fixture stubs
its public-destination authorization; actual destination rejection is tested
separately. No test contacted a provider, broadcaster or AirVPN endpoint.
Existing Caddy tests made 91 isolated synthetic requests using the unchanged pinned
binary. No real firewall, VPN, DNS, service or container operation occurred.

This is not a full Django/Celery integration test in the accepted image: that
requires a separately authorized build/test stage. The source preparation/stdlib
fixtures ran on Python 3.14. Review the committed patch/output identities and
verify compatibility on the actual image runtime before deployment. Production
readiness fixes, image pins, relay code, request budget, gateway routing, trusted
guard files, boot admission, source hashes and units were not modified.

## Build, installation and rollback prerequisites

1. Review this exact patch, source/output hashes and security limitations. Verify
   the eight input files against the retained patched image/source context; preserve
   the existing readiness fix. Stop on drift. No image identity may be invented.
2. Separately authorize a local image build and isolated application integration
   tests. Apply the reviewed overlay to the verified immutable base; no new package
   or service is needed. Record the resulting immutable image ID/digest and compile
   the patched sources under that image's Python/Django/lxml/Celery environment.
3. Prepare a coordinated protected-contract transition: new AIO image/source pins,
   verifiers/manifests and two AIO read-only inputs (/guard-status and root-private
   provider policies). Keep original private guard, relay mounts, Gluetun ownership,
   nftables, DNS/IPv6, systemd ordering, timeouts and resource admission unchanged.
   This task intentionally provides no Docker/systemd/firewall changes or installer.
4. Separately authorize deployment after healthy/idle preflight and scoped recovery
   review. Verify AirVPN configuration/owner, kernel/namespace contract, DEBUG=false,
   logging, absent/unapproved jobs/schedules, no active sessions or DVR consumers,
   permissions and exact server contract before any provider request.
5. Approve one provider's exact HTTPS endpoints/public addresses, real boot/namespace,
   guide digest and short-lived operations privately. The root policy is never put
   in Git or installed by the CLI. No placeholder is an authorization.
6. Review/authorize a live client transport change; the present unconditional live
   gate cannot be unlocked by credentials, --apply or a policy file. Then authorize
   one bounded metadata-only test with durable intent/readback evidence. Media,
   Jellyfin and native deletion remain separate decisions.

No production rollback is needed for this offline task. For a future deployment,
withdraw provider approvals first, preserve receipts and inspect in-flight jobs
and API outcomes. Before restoring the old image, verify every new provider/source
is inactive, its schedules disabled, and pending provider/profile/programme jobs
are reconciled safely. The old client lacks these controls; an old image alone is
not a safe rollback with active native provider work. Do not purge unrelated
queues, reset databases/Redis or delete uncertain owned records.

When those preconditions are established, use the separately approved matched
stack rollback to restore the prior image, exact image/source/mount verifier set
and accepted configuration through systemd, retaining the kernel guard and VPN
owner. Preserve database/cache/ownership evidence and unrelated services. If any
write or queue outcome is uncertain, stop for review instead of forcing rollback.
Verify DW channel/stream 3, channel 9001, existing guide, relay, gateway and unrelated
identities without starting a new stream unless separately authorized.

**GO for review and the next explicitly authorized build/integration-test stage;
NO-GO for installation, real metadata onboarding or playback now.**

## Exact changed-file inventory

Hashes below are SHA-256 of complete repository files relative to `04e8295`.
`output-hashes.json` separately enumerates every patched image Python file. This
report excludes its own hash to avoid a self-reference; Git identifies it.

| Repository file | SHA-256 |
|---|---|
| `configs/dispatcharr-iptv/native-provider-hardening/.gitattributes` | `fd30c321e26a7d06929b1301aa48c915454ce96117061fa28b33ae94afd7c79d` |
| `configs/dispatcharr-iptv/native-provider-hardening/README.md` | `bf0738470adfdef0c46db8b9359e6c6fa56504831a337faa1e19526171f123d5` |
| `configs/dispatcharr-iptv/native-provider-hardening/audit-source-pins.json` | `6d94e57571068b98350060d6564aa7c77854addd7e1d8452457ffc3b2f486c19` |
| `configs/dispatcharr-iptv/native-provider-hardening/output-hashes.json` | `7df269d2091eea5ed78e16d291d3c790ce49f64930ee2fdcc66569340ae9c474` |
| `configs/dispatcharr-iptv/native-provider-hardening/policy.example.json` | `185def27ceefabb25736658cd7cedd1ce1fcde04c262e20a93d23d7069c051de` |
| `configs/dispatcharr-iptv/native-provider-hardening/prepare.py` | `30133a926192cfd45eb47530c471ea2cec22b0e85b9b1e31f063968f994d7c88` |
| `configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_dns.py` | `28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a` |
| `configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_readiness.py` | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` |
| `configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_security.py` | `8f0195161771e25dc47b39a41b5cf81230d618529c5c9cce2f00ecc2fbfd845f` |
| `configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_security_view.py` | `b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b` |
| `configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_transport.py` | `f2540f50bad331dede6fc457a35db23e91bd121db3a1a977ff1617f2274e15a0` |
| `configs/dispatcharr-iptv/native-provider-hardening/server.patch` | `890b8966bd1bcae18669244c31279250733bc02ca8b3ceb5d5f2b7cb9496b83d` |
| `configs/dispatcharr-iptv/native-provider-hardening/source-pins.json` | `3ee7bc90687973be77ef7bff9254411941f930d2536eebde057659e7ee48c5f5` |
| `configs/dispatcharr-iptv/native-provider-hardening/tests/network_fixture.py` | `8f2df292f126502c273d7a0cf912e1f3c25a4ee07e01221f871cdbc7e2abfc24` |
| `configs/dispatcharr-iptv/native-provider-hardening/tests/run-isolated.sh` | `bb29b9f286870e8cd974c6d88d57f071adf17fdea70fc81d10f3569a1b9e5eaa` |
| `configs/dispatcharr-iptv/native-provider-hardening/tests/test_hardening.py` | `f213dd4cc852c6b1b806b398a99415f014c2576df0edc9fcecf79d661832e2df` |
| `configs/dispatcharr-iptv/native-provider-hardening/validation-results.json` | `1fc7745d6b088fb3ff4ebee743bdaccd3a2d578bb078ca57b75229a4f677cec7` |
| `docs/dispatcharr-provider-cli.md` | `3e4ff657c5eec66c22d27e16691b7de1ce8ca43682ddb5fc5eeb6e790d1c52ed` |
| `docs/dispatcharr-provider-native-adapter.md` | `e8da7b84fdedb3b90bc8f050393a362a252953c9c0a1f4a10c32f39812cb0e63` |
| `tools/dispatcharr_provider/api-contract.json` | `11f82f430ad7b6116d60c02b2c08f101b48bb0747104e14e98b3a9476d4aad2c` |
| `tools/dispatcharr_provider/native.py` | `601184eb63b236775ad5221bf14c064e092e26839567a726bcb72d21cc435755` |
| `tools/dispatcharr_provider/server-contract.json` | `981faf83ca20dca1a5025c25af4b21b0a5a80a924d9158f376a9026fb7203424` |
| `tools/dispatcharr_provider/synthetic.py` | `9cd6900eecc09ab8038ecc3c76244f1245f52b6fd85032659d237beb3433c93d` |
| `tools/tests/test_dispatcharr_hardening_contract.py` | `2edb4e813c229a567889ae49421f5130fb47a4b1377475c583a79859fae40134` |
