# Dispatcharr provider metadata onboarding CLI

Run with Python 3.11+ on Linux; standard library only:

```sh
python3 tools/dispatcharr-provider.py --help
```

This release retains interactive metadata discovery, selective import planning, private provider drafts and read-only Dispatcharr inspection. It also implements a pinned native account/channel/XMLTV adapter with an explicit **offline simulation** workflow. Live native mutations and native removal remain disabled. Without `--native`, `--apply` saves a confirmed local draft. With `--native --simulate-native`, it executes confirmed synthetic API operations. Neither mode activates playable destinations or changes production.

The current broadcaster-specific HLS relay is not a general Xtream gateway. New providers need a separately reviewed metadata route and format-specific streaming/security contract. Saving credentials or a draft supplies neither authorization. No tool command changes firewall, VPN, Docker, systemd, relay, Jellyfin, or DW English resources.

## Offline walkthrough

The fixtures contain placeholders and synthetic stations only:

```sh
python3 tools/dispatcharr-provider.py \
  --state-dir /tmp/provider-review-private \
  add --fixture tools/examples/provider-catalogue.example.json \
  --dispatcharr-snapshot tools/examples/dispatcharr-snapshot.example.json
```

Enter a synthetic provider name, an HTTPS `.invalid` base URL, a synthetic username/password, blank XMLTV URL, and a positive connection allowance. Select group `1`, channel `101`, or browse/select exact IDs. There are pages of 50 rows; `all` is permitted only within the 200-item selection ceiling. IDs are provider IDs, **not** Dispatcharr foreign keys.

Passwords and optional credential-bearing XMLTV URLs use `getpass`; insecure terminal fallback refuses. No password, username, token or URL is accepted as a CLI option. Username is interactively entered; it is omitted/redacted from output. No secret file is saved during dry-run. A missing state directory is not created by a dry-run add/list/inspect.

The summary shows selected groups/channels, metadata format hints, exact EPG-ID matches, missing EPG IDs, existing resources affected (none), request recipes, unresolved native foreign keys and all security prerequisites. A format hint is **not** a verified media format. No manifest or segment is fetched.

Add `--apply` only to save a private draft after reviewing the summary. You must type `ADD <first-12-key-characters>` exactly. Use an existing appropriately restricted operator secret location outside Git, such as a dedicated owner-private state subdirectory; do not use an active stack/configuration directory. No real credentials should be used for fixture demonstrations.

```sh
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE list
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE inspect
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE \
  refresh EXACT_PROVIDER_KEY --fixture tools/examples/provider-catalogue.example.json
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE remove EXACT_PROVIDER_KEY
```

`refresh` compares metadata with the owned selection. Removed channels, altered selected metadata or changed EPG mappings refuse rather than overwrite. Default is dry-run; `--apply` requires `REFRESH <key-prefix>`. It does not call native provider refresh APIs.

`remove` displays the exact owned draft and its effect. `--apply` requires `REMOVE <key-prefix>` and moves that draft into a private recovery file. It never deletes a remote provider/channel/stream/group/EPG source. A draft claiming native resources or another owner refuses. Remote records are never silently adopted.

## Approved metadata discovery — separate future network approval

Without `--fixture`, `add`/`refresh` require `--metadata-approval /EXISTING/ROOT/PRIVATE/APPROVAL.json`. The included `metadata-approval.example.json` is intentionally invalid/expired and is not an authorization or installer. This development task did not create or install a grant or real credential file.

A separately approved network review must identify the correct Rivendell execution context, host boot, actual VPN and host namespace device/inode pairs, policy digest, exact endpoint paths and public IPv4 addresses. The root-owned single-link regular approval must be 0600, expire within 24 hours, match current boot/namespace, specify tun0 and differ from its recorded host namespace. Do not fabricate these values to satisfy a check. The CLI cannot establish the approved path for you.

Before resolving metadata hosts, the client requires only `127.0.0.1` as resolver and disabled IPv6. A short-lived DNS worker has a five-second deadline; all DNS answers must belong to the explicit public-IPv4 set. Every checked destination must route through tun0 using a root-owned read-only `ip route get` executable. HTTPS uses the original hostname for certificate/SNI verification while connecting to the already-checked IP. Proxy environment variables are not used; redirects, unapproved DNS changes, compressed payloads and TLS errors refuse, without retry. The namespace/path approval is a trusted administrative assertion, not proof of continuous kernel enforcement; existing guard/VPN policy still applies independently.

Only fixed Xtream metadata requests are issued:

- `player_api.php?action=get_live_categories`
- `player_api.php?action=get_live_streams`
- The explicit XMLTV metadata URL, or the provider's `xmltv.php` endpoint.

Xtream GET credentials are URL-encoded **only in the in-memory TLS request**, never process arguments or diagnostic output. Provider-returned stream/logo/redirect URLs are never followed. Optional provider XMLTV 404 is reported as unavailable; a separate explicitly supplied XMLTV URL failure, TLS/DNS failure or malformed data refuses. XMLTV supports bounded UTF-8, rejects DTD/entities and uses stable exact channel IDs; it never invents listings or matches by fuzzy names.

Limits: one metadata request at a time, no retries, 16 MiB per response/private record, 100,000 metadata rows, 200 selected groups/channels, pages of 50 display rows, 64 Dispatcharr pages, 1,000 local drafts. Socket operations have ten-second timeouts; the body read loop has a 15-second budget with bounded `read1` reads. DNS has its own five-second worker deadline. These are separate phase bounds, not a promise of 15 seconds for the whole workflow. The CLI has no daemon, queue or automatic refresh scheduler.

HTTP-only servers, nonstandard TLS ports, ambiguous paths, duplicate IDs, unsupported paginated Xtream response wrappers and oversized inventories refuse. The pinned Xtream interface returns arrays; the CLI does not silently truncate to a first provider page. API pagination follows bounded local page numbers and never trusts a server-supplied next URL as a destination.

## Read-only Dispatcharr inspection

```sh
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE \
  inspect --remote --api-credentials /EXISTING/OWNER/PRIVATE/LOGIN.json
```

This is for a separately verified existing execution context where the accepted AIO API is `http://127.0.0.1:9191`; it is not a remote login/SSH launcher. Other origins refuse. Use the selected owner's existing 0600 login file with `username`/`password`; never another person's credentials. The tool does not install or copy that file. A placeholder schema is supplied in `dispatcharr-login.example.json`.

The transport permits only authentication-token POST and release-specific inventory GETs. It cannot POST/PATCH/DELETE provider resources, change settings or invoke refresh/import endpoints. Admin account responses can contain passwords; only safe allowlisted summary fields are printed, and response credentials/URLs are collected for redaction. No raw API response or exception body is logged.

Without `--remote`, a synthetic/private `--dispatcharr-snapshot` may be supplied. If neither is supplied, the plan explicitly says remote duplicates were **not checked**. Such a draft is never presented as ready to register. Snapshot keys are `accounts`, `channels`, optional `groups`, `epg_sources`, `epgdata`; no existing record is overwritten.

## Original draft-mode native contract (live execution remains blocked)

This table describes the unchanged original draft mode; see the native extension below for the implemented synthetic API workflow. The reviewed contract is pinned to Dispatcharr commit `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e` and accepted image `14c83733…cad21`. Exact source hashes are in `tools/dispatcharr_provider/api-contract.json`; production pins/manifests were not changed.

| Native operation | Verified source/API | This CLI |
|---|---|---|
| Create/list Xtream account | `/api/m3u/accounts/`, account_type=`XC`, server_url, username/password, max_streams, is_active and explicit auto-enable/VOD controls | Read inventory and generate inactive request recipe only |
| Discover native groups | Account create immediately calls `refresh_m3u_groups`; group relations and native group-settings action exist | External approved metadata discovery; no native create |
| Refresh provider streams | `POST /api/m3u/refresh/<account_id>/` queues refresh and synchronization | Metadata comparison only; no native refresh task |
| Select/import channels | Native group settings and streams; `/api/channels/channels/` accepts streams, channel_group_id, tvg_id, epg_data_id | Exact selections and symbolic import/EPG plan; no guessed native IDs |
| XMLTV source CRUD | `/api/epg/sources/`, source_type=`xmltv`, url, is_active | Read inventory and inactive request recipe only |
| Refresh EPG | `POST /api/epg/import/` with id queues import | Not invoked |
| Stable EPG mapping | `/api/epg/epgdata/`; channel epg_data_id/tvg_id | Exact XMLTV IDs only; duplicate/ambiguous IDs flagged/refused; no existing mapping adoption |
| List/remove provider-owned resources | Account detail plus related streams/channels; account DELETE cascades streams and auto-created channels | All remote resources unmanaged; destructive remote operations absent |

Sources: pinned [M3U views](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/api_views.py), [serializers](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/serializers.py), [stream import](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/m3u/tasks.py), [channel views](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/channels/api_views.py), [EPG routes](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/epg/api_urls.py) and [EPG serializer](https://github.com/Dispatcharr/Dispatcharr/blob/2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e/apps/epg/serializers.py).

This is a deliberate safety boundary, not a successful native onboarding claim:

1. Even inactive XC account creation contacts the provider. Native account refreshes can discover groups, and later synchronization can create/update channels. The CLI's metadata approval does **not** authorize those separate server-side clients or their logging/redirect behavior.
2. Ordinary stream APIs exclude inactive account streams. Account deletion cascades related streams and auto-created channels, including effects on shared/manual channel relationships. Exact ownership/absence cannot be proved by collection omission. No production removal is implemented.
3. The native XC importer constructs credential-bearing `/live/<username>/<password>/<stream_id>.ts` URLs. No inference is made that these are compatible with the current broadcaster-only HLS allowlist. Metadata format hints and native URL construction are documented without fetching media.
4. Before native registration/activation, separately review the actual metadata path used by Dispatcharr, logging/redaction, per-provider connection limits, full resource ownership/cascade visibility, native foreign-key resolution and stream-format-specific enforcement. Any required relay/firewall policy change must be separately reviewed and installed; this tool cannot authorize or perform it. No direct provider URL may be exported to Jellyfin.

## Journals, removal and recovery

Saved drafts contain the provider secret, sanitized plan and explicit owner marker `dispatcharr-provider/v1`; their remote-resource list must be empty. State directory 0700, files/lock 0600, current-owner-only regular single-link files; symlinks/FIFOs/hardlinks refuse. Secrets belong outside Git. Private draft passwords are stored as plaintext under those permissions, consistent with the existing deployment's restricted private files; they are not an encrypted vault.

Each local change holds one exclusive file lock and writes a fsynced pending operation with before/after digests before atomic publication. Receipts are retained. A crash blocks further mutation; no POST/DELETE retry exists. Inspect/reconcile only after the interrupted process has exited:

```sh
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE reconcile
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE reconcile --apply
```

The first command reports the pending operation. The second requires `RECONCILE <key-prefix>` and only reconciles a known local after-image or aborts a known before-image without replay. Unexpected state refuses. For interrupted removal, the private retired draft must also match. Retired files and old journals are not permanently deleted; retention is an explicit operator responsibility. Do not edit journals to bypass a conflict or copy a foreign manifest to adopt remote resources.

## Tests

```sh
python3 -B -m unittest discover -s tools/tests -v
```

Tests use synthetic credentials, mocked provider/Dispatcharr APIs, fake TLS transports and temporary private state. Existing protected-stack regressions are documented in the implementation report. No test needs real credentials, a production connection, media, or container operations.

## Native adapter extension (this release)

The original draft commands above are unchanged. A separate native API algorithm
now exists in `tools/dispatcharr_provider/native.py`. It performs real-contract
account/group/stream/channel/XMLTV operations against an injected **synthetic API**,
with durable native ownership and write-ahead journals. This supersedes the older
statement that no adapter exists; **no live mutation transport is enabled**.
See [native adapter review](dispatcharr-provider-native-adapter.md) for the exact
contract, side effects, recovery limits and live-test prerequisites.

Use synthetic credentials only in these demonstrations:

```sh
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE \
  add --native --simulate-native \
  --fixture tools/examples/provider-catalogue.example.json
```

Default is a dry-run. Add `--apply` to execute the entire synthetic native
registration after typing `SIMULATE ADD <key-prefix>`. This creates a simulated
native account, selected hidden channels and exact guide mappings. It is **not**
a local draft save and **not** a production import. Group and channel selections
use the displayed stable provider IDs. No fixture URL is contacted.

```sh
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE list --native
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE inspect --native
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE \
  refresh EXACT_KEY --native --simulate-native \
  --fixture tools/examples/provider-catalogue.example.json --apply
python3 tools/dispatcharr-provider.py --state-dir /PRIVATE/STATE \
  reconcile --native --simulate-native --key EXACT_KEY \
  --fixture tools/examples/provider-catalogue.example.json --apply
```

`refresh` reuses only the owned selection and refuses changed native IDs or guide
mappings; it never creates more channels. Confirm with `SIMULATE REFRESH <prefix>`.
Reconciliation uses `SIMULATE RECONCILE <prefix>` and only verifies a pending
known-ID write by GET; it never resumes an interrupted registration or requeues an
import. A lost create response, uncertain queue request, or nonterminal task needs
manual review. Preserve all receipts; do not erase state to retry.

Native `list`/`inspect` read local ledgers only, clearly marked simulations. Use the
original `inspect --remote` command **without `--native`** for supported read-only
Dispatcharr inventory in a separately approved execution context. Native mode
rejects remote inventory flags rather than implying a live check occurred.

`remove KEY --native` always refuses. The existing `remove KEY` command still
archives only a private local draft. Neither deletes a remote record.

Native files live beneath the private state directory's `native/` subdirectory:
`native-KEY.json` holds the ownership ledger and operation receipts;
`synthetic-KEY.json` holds the simulated server state. Files are 0600, the directory
is 0700, and one exclusive lock covers both. These files contain synthetic private
inputs and must never be committed. The legacy draft store remains separate.

Omitting `--simulate-native` refuses native execution before credentials, state
creation or network access. `--apply`, a metadata approval or an administrative
login cannot unlock it. Native creation itself fetches provider data even when
inactive; its server-side redirect/retry/logging behavior needs separate approval
and controls. No new provider is routed through the DW English relay or exported
to Jellyfin. No media URL or format has been tested by this development work.

## AirVPN server-hardening candidate

The offline native adapter now requires `dispatcharr-native-airvpn-v1` before
registration or refresh. It verifies exact patched source hashes, required
features, provider key, exact guide URL digest, unexpired approval and a current
guard-generation assertion. Missing/mismatched evidence stops before native
writes. The verified contract is retained in the private ledger.

Account creation explicitly requests `metadata_discovery=true`. After creating
owned channel/guide mappings, the adapter submits one more journaled EPG import:
the hardened server suppresses automatic remote per-channel programme jobs.
The workflow still ends with inactive account/source and hidden channels.

This does **not** unlock live execution. The server patch has not been built or
installed; production cannot satisfy this contract. The synthetic server supplies
a simulated assertion only. Policies cannot be created by a CLI flag, `--apply`,
existing admin credentials or the old metadata-path approval.

See [native provider hardening](dispatcharr-native-provider-hardening.md) for
network controls, explicit background-work rules, supported input limits and the
separate build/deployment prerequisites. Native removal and new provider media
activation remain disabled; the existing DW English relay and Jellyfin settings
are unchanged.
