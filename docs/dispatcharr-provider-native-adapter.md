# Dispatcharr native Xtream and XMLTV adapter

2026-11-17. `APMurtha/homelab-operations`, branch
`docs/udm-pro-max-migration-prep`. Starting implementation: `7f6822a`.

**PASS for offline implementation and synthetic API acceptance. GO for code
review; NO-GO for a real-provider test under the current network/logging contract.**
The adapter executes the native registration/import/EPG workflow against mocks;
it is no longer just a draft planner. Live native execution remains deliberately
disabled. No production, provider or broadcaster was contacted; no real credential
was installed. The working DW English stack and Jellyfin were not touched or
independently re-measured during this offline task.

## Architecture and operator behavior

`tools/dispatcharr_provider/native.py` contains the release-specific API scope,
bounded inventory/detail reads, registration and refresh algorithms, ownership
ledger and durable mutation protocol. `native_cli.py` integrates explicit native
mode without changing the original private-draft commands. `synthetic.py` models
the relevant API responses, inactive-account side effects, asynchronous completion
and private simulated server state. It has no network client.

The existing credential prompts, `getpass`, redaction, validation, metadata
selection and draft journals remain intact. `add` without `--native` still prepares
and optionally saves a **local draft**. Native mode uses separate private ledgers.
`--native --simulate-native --fixture ...` presents stable provider group/stream
IDs, requires a bounded selection, shows side effects and defaults to dry-run.
`--apply` requires `SIMULATE ADD <key-prefix>` before any simulated writes.
The summary explicitly identifies a simulation, native IDs, missing guide matches
and blocked media activation. It never calls a draft a registered provider.

| Command | Operational behavior |
|---|---|
| Original `add`, `refresh`, `remove`, `reconcile` | Existing local draft behavior unchanged; default dry-run |
| Original `inspect --remote` | Existing supported read-only loopback API inspection; not exercised live here |
| `add --native --simulate-native` | Complete synthetic native registration/import after explicit confirmation |
| `refresh KEY --native --simulate-native` | Refresh only an owned synthetic selection; verify IDs/mappings, no new channels |
| `list/inspect --native` | Local native ownership summaries only; no live checks implied |
| `reconcile --native --simulate-native --key KEY` | Read-only reconciliation of one known-ID intent; no automatic resume |
| `remove KEY --native` | Disabled: cascade/shared-resource safety is not proven |
| Native execution without `--simulate-native` | Refused before input, authentication, state creation or network activity |

The CLI has no switch, approval-file field or administrative credential that
unlocks native HTTP writes. The separate API algorithm accepts an injected test
transport; its write scope additionally requires an explicitly synthetic transport.
Changing code to add live transport requires review and separate authorization.
Usage examples and confirmation strings are in
[the CLI guide](dispatcharr-provider-cli.md#native-adapter-extension-this-release).

## Pinned source and exact API contracts

The accepted image remains
`sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
Source is pinned to Dispatcharr
[`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`](https://github.com/Dispatcharr/Dispatcharr/tree/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e).
`tools/dispatcharr_provider/api-contract.json` records exact source SHA-256 pins
and the adapter contract. Existing production source/image pins were unchanged.
Additional official files inspected were `apps/m3u/models.py`, `apps/epg/tasks.py`,
`apps/channels/managers.py` and `core/scheduling.py` at that same commit.

| Operation | Native contract used |
|---|---|
| Account create | `POST /api/m3u/accounts/`, HTTP 201; `account_type=XC`, private server/username/password, known max_streams, `is_active=false`, refresh_interval 24, empty cron, explicit VOD and all new-group auto-enable flags false, ownership custom_properties |
| Account details/status | `GET /api/m3u/accounts/{id}/`; returned ID must equal requested ID; admin representation may contain password and is never printed |
| Group discovery | Account detail `channel_groups`: native channel_group ID, enabled, auto_channel_sync, ranges and custom_properties.xc_id; resolve stable provider category IDs within this account, never by label alone |
| Group selection | `PATCH /api/m3u/accounts/{id}/group-settings/`, HTTP 200; group_settings covers every discovered association; only selected categories enabled; auto_channel_sync false; ranges null; preserve relation custom_properties; fresh detail verifies the complete set |
| Provider refresh | `POST /api/m3u/refresh/{id}/`, HTTP 202; active account required by task; poll account detail for success and changed nonempty updated_at; never use global refresh |
| Native stream inventory | `GET /api/channels/streams/?page=N`; filter exact m3u_account; resolve integer stream_id, group ID, exact tvg_id and non-stale state; missing/duplicate match refuses |
| Stream profile | `GET /api/core/streamprofiles/?page=N`; require exactly one locked, active FFmpeg streamcopy/MPEG-TS profile matching the explicitly supplied reviewed ID; no name-only ID inference |
| EPG source | `POST /api/epg/sources/`, HTTP 201; source_type xmltv, private explicit or provider XMLTV URL, inactive, refresh_interval 24, empty cron, priority 0 and ownership tag |
| Scoped activation/deactivation | `PATCH /api/m3u/accounts/{id}/` or `/api/epg/sources/{id}/`, HTTP 200; only is_active is changed by this algorithm, private before-image retained |
| EPG import | `POST /api/epg/import/`, HTTP 202; explicit positive id and force=false required; active source required; poll source detail for success with changed updated_at |
| EPG data resolution | `GET /api/epg/epgdata/?page=N`; exact owned epg_source ID plus case-sensitive tvg_id resolves actual EPGData.id; no guessed ID or display-name match |
| Channel create | `POST /api/channels/channels/`, HTTP 201; actual streams IDs, native channel_group_id, exact tvg_id/epg_data_id, reviewed stream_profile_id, hidden_from_output true and channel_profile_ids=[]; detail readback verifies returned ID, UUID and accepted fields |
| Channel inventory/detail | Collection explicitly includes visibility_filter=all; known hidden IDs verified through detail GETs |

These contracts come from the pinned
[M3U API](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/api_views.py),
[M3U serializer](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/serializers.py),
[M3U tasks](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/tasks.py),
[channel API](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/api_views.py),
[channel serializer](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/serializers.py)
and [EPG API](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/epg/api_views.py).
No endpoint name or native foreign key was inferred from another release.

## Side effects and the live execution blocker

XC account creation commits the account and then synchronously calls
refresh_m3u_groups, even when inactive. XCClient authentication and category GETs
occur in that call. It creates/discovers global groups and account relationships,
queues profile/account-info refresh, and signals create a default profile and
periodic task. Inactive is **not** a network isolation boundary. A failed HTTP
response does not prove that account creation was rolled back.

A stream refresh requires an active account and can rediscover all categories,
queue profile refresh, retrieve the live-stream catalogue, persist metadata for
enabled categories, mark/clean stale account streams and run auto-channel sync.
All auto-enable/VOD flags and all group auto-sync settings are explicitly disabled
and verified before refresh; only the selected **channels** are created, at most
200. Native stream metadata can still include every stream in selected categories,
not just selected IDs. Client-side limits cannot cap the server's metadata work or
provider response size. A live review must bound the actual provider catalogue and
background task resource effects before permitting account creation.

Active EPG source creation would queue an automatic import. The adapter creates it
inactive, then activates and explicitly imports it once. Active account/source
windows also enable periodic tasks; refresh_interval=24 is not a guarantee that a
Beat tick cannot queue extra work. On success both return inactive. On failure an
active window may remain open; no blind corrective PATCH is attempted. A live
transport must not be enabled without controlled server-side scheduling/network
boundaries and an approved failure/recovery procedure.

Manual channel creation can attach its group to the shared locked Custom account
and queue parse_programs_for_tvg_id, as shown by the pinned
[channel signals](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/signals.py).
The ledger records before/after effects on existing accounts without adopting
those accounts. Queued programme parsing, schedule rows, cached programme state
and other internal side effects cannot all be enumerated or independently verified
through the selected public API. Therefore this implementation does not claim
complete cascade ownership or proven server quiescence. It verifies channel/EPG
foreign keys, not actual programme availability or an independent profile-membership
query. These are explicit live acceptance prerequisites.

The pinned [XCClient](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/core/xtream_codes.py)
uses requests.Session GET with default redirect behavior, 60-second timeouts and
an adapter configured with max_retries=3. Debug/error paths include URLs, request
params and exception tracebacks; authentication/group tasks can log usernames.
Default TLS verification is not disabled, but there is no equivalent of the
CLI metadata client's destination/IP/path/redirect enforcement. A native request
executes in the API/Celery server, not the CLI's separately approved metadata
namespace. The old metadata approval therefore cannot authorize native I/O.

No relay allowlist, VPN/firewall rule, logging configuration or application source
was changed to address these blockers in this task. An owner-approved server-side
network and secret-safe logging contract must precede live enablement. Inactive,
hidden and empty channel-profile settings reduce exposure; they do not prove that
an authenticated native detail/playback URL cannot be used.

## Selection, EPG and refresh rules

Selection uses provider stream/category IDs. Native IDs are resolved only after
native discovery, scoped to the created account. Account name/server+username,
channel name/tvg-id and EPG source name/URL duplicates refuse without adoption.
Selected duplicate names/guide IDs, missing native streams, multiple matches,
wrong groups, changed EPG IDs and stale metadata refuse. No existing channel or
mapping is overwritten. DW English ID 3/channel 9001 is protected, and the entire
preexisting hidden-inclusive channel inventory must remain unchanged.

Provider EPG defaults to the private xmltv.php URL with encoded credentials; an
optional validated separate XMLTV URL replaces it. Matching uses exact stable
identifiers **within the newly owned source**, so an entry from another source is
never silently borrowed. Missing entries remain explicitly null/unmatched;
duplicate IDs within the source refuse. No guide entries are invented. Refresh
can update provider metadata, but changing selected native stream IDs or mapped
EPGData IDs stops rather than rebinding existing channels automatically.

There is no media fetch, playable-stream activation, export generation or Jellyfin
operation. The native importer constructs /live/<username>/<password>/<id>.ts,
regardless of a provider container_extension hint. TS/HLS compatibility is not
established without media inspection; this task deliberately did none. The current
DW English HLS relay must not transport these URLs. A separate format-specific
security review is needed before playback or Jellyfin exposure.

## Ownership, journaling and recovery

One owner-only lock covers native state. Native ledgers and synthetic server
files are atomic/fsynced 0600 files under a validated 0700 directory. Symlink,
hardlink, wrong-owner and unsafe-mode checks reuse the existing private-state
implementation. Credentials and URLs remain private plaintext, as in the existing
restricted-file approach; this is not an encrypted vault. Raw exceptions and
server error bodies never become progress/error output.

The durable ledger records the provider identity/key, selection, account and
default profile identities, ownership custom_properties, all discovered stream IDs,
account-group associations, observed new global group IDs, EPG source/data IDs,
channel IDs/UUIDs, resolved stream/EPG bindings, baseline channels/accounts and
indirect signal effects. Global groups and the shared Custom account are not
claimed as exclusively owned. Derived resources are scoped to their owned parent;
that scope alone is not deletion authority.

Each POST/PATCH has a durable intent **before** transport, containing a unique
operation ID, exact private request, expected readback, original modified values
or pre-create ID set. Returned IDs and acknowledgement are durably recorded before
verification. A completed operation is marked verified only after authoritative
detail verification, complete group readback, or fresh asynchronous success.
Queue acknowledgement alone does not complete a refresh/import.

Any pending intent blocks further writes. Lost responses, authentication failures,
server errors, interrupted journals and timeouts do not trigger mutation retries.
Polling is bounded to 30 observations by default (maximum configurable 60 in the
adapter), one second between reads; success requires a changed timestamp as well
as status. A task may continue after polling ends; receipts remain pending and no
requeue occurs. This is not a transaction across Dispatcharr and Celery.

Known-ID creates/PATCHes can be reconciled by exact GET readback. Unknown create
IDs, group-setting outcomes or asynchronous intents require operator review;
reconciliation never retries a mutation or resumes an interrupted workflow.
Read/write gaps lack server-side compare-and-swap; the adapter does not claim
atomic conflict exclusion or complete automatic crash recovery. Preserve ledgers,
receipts and before-images, establish exclusive administration, inspect queued
work and reconcile actual outcomes before any separately reviewed recovery.

Native deletion is disabled. The account destroy handler can stop proxies,
delete auto-created channels and cascade streams into shared channel relations;
inactive streams are omitted from the stream queryset. Channel/group/EPG signals
and shared references make an account-ID-only delete unsafe. Refresh refuses
foreign channels sharing owned streams/EPG entries, including hidden channels.
No broad cleanup, adoption or automatic rollback was added. Local draft archival
remains available and does not touch these native resources.

## Offline verification

**405 tests passed: the complete 343-test baseline plus 62 new native tests.**
No failures, errors or skips. Machine-readable results and local log SHA-256
fingerprints are in `tools/dispatcharr_provider/validation-results.json`.

| Suite | Tests |
|---|---:|
| Existing provider CLI/input/transport/planning/journal tests | 65 |
| New native adapter/API/CLI/simulation tests | 62 |
| Permanent security/registration/lifecycle/export groups | 39 + 26 + 17 + 7 + 3 |
| Minimal persistence/admission/trusted guard groups | 12 + 28 + 50 |
| Isolated TLS/DNS/resources and native Caddy groups | 13 + 15 |
| Historical persistence / prior guard / design | 26 + 14 + 28 |

New cases cover inactive XC creation discovery, asynchronous imports/freshness,
actual native ID resolution, bounded selections, broader category metadata,
source-scoped exact EPG mappings, missing/duplicate/foreign guides, profile checks,
hidden/shared resources, DW preservation, signal effects, duplicate/conflict
refusal, readback drift, credential-safe errors, authentication failure, durable
intents, uncertain committed POSTs, known-ID reconciliation, task deadlines,
interrupted registration, refresh conflicts and cascade deletion refusal. Original
TLS, redirect, DNS, secret-entry and large-inventory tests remain passing. Existing
protected tests include isolated UID/GID, crash and namespace fixtures plus 91
native Caddy fixture requests, without external routes.

Reproduce:

```sh
python3 -B -m unittest discover -s tools/tests -v
CADDY_TEST_BINARY=/PATH/TO/PINNED/CADDY sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh
python3 -B -m unittest discover -s configs/dispatcharr-iptv/persistence-phase6b3/tests
sh configs/dispatcharr-iptv/guard-interface-review/run-offline.sh
sh configs/dispatcharr-iptv/trusted-guard-design/run-offline.sh
```

The Caddy binary pin remains a563843e…60cdf. Namespace fixture suites need the
existing isolated user/mount/network test capability. Only official pinned source
retrieval used external access. Mock success is not live server compatibility,
provider authorization, media acceptance or proof of a secure deployment path.

## Review and live-test prerequisites

1. Review this adapter, its source contracts, journals and synthetic acceptance.
2. Approve exact server-side metadata destinations, DNS/TLS/redirect enforcement,
   background profile/EPG tasks, size/rate limits and secret-safe logging. Existing
   broadcaster-only controls must remain unchanged; if those cannot support safe
   metadata access, stop before registration rather than expand them implicitly.
3. Establish exclusive administration and verify the pinned release/admin API,
   account catalogue size, current inventory, profile identity, hidden visibility
   and ownership/conflict baseline through separately authorized reads.
4. Resolve temporary scheduler activation, programme-task completion and shared
   Custom-group effects; specify observable recovery and no-retry reconciliation.
   Exact deletion/cascade proof is still required before enabling removal.
5. Review a scoped live transport change, then separately authorize one provider
   metadata test using existing private credentials. No real credential is needed
   to review or exercise the current synthetic implementation.
6. Review actual provider transport/format and separate media policy before any
   streaming activation. Jellyfin and the DW English HLS relay remain out of scope.

**NO-GO for a live provider test now.** The blocker is the native server's actual
network/logging/scheduling side effects, not a missing registration algorithm.
No additional infrastructure project or production workaround was undertaken.

## Changed-file inventory

The following inventory is relative to `7f6822a`. SHA-256 covers the complete file.
The report itself is excluded to avoid a self-referential hash; Git identifies it.
Original production configs, systemd/guard/relay manifests, image pins and the
original 65-test module are unchanged. The existing synthetic metadata and login
examples remain compatible; no secret or runtime state was committed.

| File | Change | SHA-256 |
|---|---|---|
| `docs/dispatcharr-provider-cli-implementation.md` | Updated | `b8556944c40b0e9b1282ca4ca5672e78357ac12ee2bb8d52cdefa871352adb83` |
| `docs/dispatcharr-provider-cli.md` | Updated | `ae487f5499042aaaf7d102a4559fb682758bf7f76a64772e698007605bd1e2e3` |
| `tools/dispatcharr_provider/api-contract.json` | Updated | `9fa46d0a472cb9c1c316f52ff12f17f9ac05aca42502ae2d0046a868cb623a9b` |
| `tools/dispatcharr_provider/cli.py` | Updated | `b2682033fc32d1a0cfb0a003f4450c393052bd89e226215196208625254bbb62` |
| `tools/dispatcharr_provider/validation-results.json` | Updated | `f598cdd992df9e6ccf6700f85a6e0995a010f2bf83e7af3bed4c53d1194e8450` |
| `tools/dispatcharr_provider/native.py` | Added | `a76a8712fba0b400a01935561285179e63994ed25fbc5560a55b5e19deef222e` |
| `tools/dispatcharr_provider/native_cli.py` | Added | `099fc706a47d5e72df5c931977a1788f55eccbb08213810c603a60c89d690221` |
| `tools/dispatcharr_provider/synthetic.py` | Added | `606efd09a0d612d4bc30e972f1edbe36d0e23fda6508c350aadb53c3664dc125` |
| `tools/tests/test_dispatcharr_native.py` | Added | `a0c18393dfe18a7e58574a06d1269e5b9100b90c40f7f046ed24e470f45055c9` |
