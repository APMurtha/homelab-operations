# Dispatcharr provider CLI — offline implementation review

2026-11-17. Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.

**PASS for offline metadata onboarding preparation and private draft management. GO for code review; NO-GO for real provider registration/import/activation.** The utility is runnable and tested, but deliberately has **no production mutation adapter**. This limitation is explicit in CLI help, summaries and [usage documentation](dispatcharr-provider-cli.md). It must not be mistaken for a completed native provider registration tool.

## Implemented behavior

Entry point: `python3 tools/dispatcharr-provider.py`. Standard library only, Linux/Python 3.11+.

- `add`: interactive provider/base URL/username, hidden password and optional XMLTV URL, known positive connection allowance, bounded group/channel browsing and exact selection. Synthetic fixtures are supported without networking. A separately approved metadata path may be used later, but none was installed/contacted in this task.
- Default dry-run displays provider fingerprint, selected metadata, exact stable EPG-ID matches, unmatched/ambiguous cases, affected existing resources, supported native request recipes and unresolved native IDs/security prerequisites. A draft never represents authorized streaming or successful import.
- `--apply`: requires an exact confirmation string and writes a private **local draft only**. No account, stream, channel, group, EPG source or mapping is created in Dispatcharr.
- `inspect`: local ownership plus optional whitelisted read-only Dispatcharr inventory, including hidden channels. Remote records remain unmanaged and cannot be adopted. No production inspection was performed during development.
- `list`, `refresh`, `remove`: manage only this tool's private local drafts. Refresh refuses removed/changed selected channels or EPG mappings; removal archives a matching owned draft without permanent deletion. Claims of native-owned resources refuse.
- Durable locked/fsynced journals, atomic publication, before/after conflict checks and explicit `reconcile` support interrupted local transactions without retrying effects. There is no remote mutation to retry. Retired drafts and journal history remain private.

Examples contain only synthetic stations, reserved `.invalid` hosts and replacement placeholders. Actual credentials are prompted privately or read from existing restricted files in a future approved context. No secret CLI options, raw upstream errors, diagnostic tracebacks or provider-returned URLs are printed. State is owner-private 0700 with 0600 regular single-link files; unsafe links, permissions, ownership and journals refuse.

## Architecture/API findings and scope decision

The deployed architecture was reviewed through committed deployment/integration/retirement reports, candidate source and pins. **No SSH, production API, Docker or Jellyfin operation was performed.** The previous report's healthy DW English state was not re-measured or modified by this offline task.

Source review used Dispatcharr commit `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`, corresponding to the accepted patched image. All 14 existing API-source hashes matched the retained local source, and eight additional official source files at that exact commit were retrieved solely for review. The new `api-contract.json` records all 22 hashes; existing protected pins/manifests were untouched.

The native API supports XC account CRUD, group relationships/settings, provider refresh, stream/channel CRUD, XMLTV sources/import and `epg_data_id`/`tvg_id` mapping. Detailed routes/fields and direct source links are in the usage guide. Important constraints prevent safe generic writes in the current release:

1. **Creating an inactive XC account still calls provider metadata refresh synchronously.** Native creation is therefore not a harmless local staging operation. The standalone metadata client's approval does not authorize Dispatcharr's internal requests, redirects, asynchronous work or logging.
2. **Inactive account streams are excluded from the ordinary stream API.** A list omission is not absence. Account deletion cascades streams and auto-created channels, potentially affecting shared/manual relationships. Full ownership/cascade proof is not available from the ordinary inventories reviewed here. No destructive native operation is implemented.
3. **The pinned native importer constructs credential-bearing `/live/<username>/<password>/<stream_id>.ts` URLs.** This does not establish actual media encoding or HLS compatibility. The current relay remains scoped to its approved broadcaster; no new URL, domain, port, profile, egress permission, relay rule or Jellyfin export was authorized.
4. **EPG mappings require actual owned source/EPGData/stream IDs after reviewed native import.** The CLI does not guess IDs or bind to an unrelated source merely because a display name or stable ID matches. Existing/ambiguous records and group-name collisions require review; DW English resources are never overwritten.

The CLI provides selective channel import **plans**, not actual stream import. Native account/EPG request recipes are deliberately non-executable and contain private-value references. A future policy-specific write adapter, with full side-effect/ownership visibility and separate deployment authorization, is required before real onboarding. This safety stop follows the task's explicit no-automatic-destination-authorization and conditional destructive-operation requirements.

## Metadata transport and credentials

The optional future metadata client accepts only an existing root-owned 0600 approval tied to current host boot, actual namespace, a distinct recorded host namespace, tun0, reviewed policy digest, exact paths, public IPv4 set and short expiry. It verifies loopback-only resolver settings, disabled IPv6 and destination routing through tun0. The tool cannot enter a namespace, install an approval, invoke a publisher or change networking.

DNS is isolated in a bounded short-lived worker. HTTPS connects to a checked IP with hostname/SNI certificate verification; DNS changes, redirects, proxy inheritance, TLS failure, compression, oversized data and time limits fail closed without retry. Only fixed Xtream live-category/live-stream metadata actions and XMLTV are requested. XMLTV DTD/entity and non-UTF8 inputs refuse. This is an administrative approval/point-in-time context check, not continuous kernel attestation or authority to broaden the existing protected firewall.

Passwords and optional secret XMLTV URLs use secure `getpass`; insecure terminal fallback refuses. Secrets are held in memory for dry-run; confirmed local drafts store them as plaintext under the restricted existing-file approach, not as an encrypted vault. Raw provider/Dispatcharr data and credential-bearing URLs are neither printed nor saved as diagnostics. Native admin account responses can contain passwords and are handled accordingly. No real credential was entered, installed or committed in this development task.

## Validation

**343 tests pass, zero failures/errors/skips:**

| Suite | Tests |
|---|---:|
| New mocked CLI/input/transport/planning/ownership/interruption tests | 65 |
| Existing permanent policy/registration/lifecycle/export tests | 39 |
| Existing hidden rollback / security contract | 26 / 17 |
| Existing diagnostic inventory / provenance | 7 / 3 |
| Existing minimal persistence / admission | 12 / 28 |
| Existing actual trusted guard permission/crash/unit tests | 50 |
| Existing isolated TLS/DNS/resource / native Caddy groups | 13 / 15 |
| Historical persistence / prior guard interface / design models | 26 / 14 / 28 |

New regressions cover plain/percent-encoded secret and hostile URL redaction, insecure argument/getpass handling, URL validation, TLS/SNI/IP pinning, redirects/HTTP errors, DNS rebinding/private/IPv6 destinations, namespace/DNS/tun0 checks, bounded response/deadline handling, pagination/10,000-channel inventories, selection bounds, exact EPG matches/ambiguity, duplicate providers/groups/channels/sources, interrupted add/remove, journal tampering, ownership conflicts, and DW English preservation. A behavior test rejects all provider-resource POST/PATCH/DELETE before transport. All data and credentials are synthetic.

Existing network tests used isolated user/mount/network fixtures with no external route, including 91 native Caddy fixture requests. No real firewall, provider, broadcaster or production container was exercised. Only official pinned source retrieval used external network access. The CLI smoke inspection used the synthetic DW English snapshot and created no state directory.

Reproduce new tests:

```sh
python3 -B -m unittest discover -s tools/tests -v
```

Existing suites use the unchanged permanent-streaming runner with the retained verified Caddy binary, plus historical persistence, guard-interface-review and trusted-guard-design runners. Counts and boundaries are recorded in `tools/dispatcharr_provider/validation-results.json`.

## Remaining review/deployment prerequisites

- Review/install a real metadata-only VPN path separately; the example approval is invalid and conveys no authority. No provider request was made in this task.
- Review native account-create/refresh side effects and credential logging/redirect behavior before adding a mutation adapter. Resolve a complete resource graph and conflict-checked recovery rather than relying on inactive-stream list absence.
- Determine each selected provider's actual delivery URL/container behavior under a separately authorized bounded media test. Metadata hints and native `.ts` construction are not proof. Any new enforcement/relay policy requires separate design/review; do not reuse the broadcaster HLS allowlist indiscriminately.
- Verify pinned release compatibility and selected Rivendell context before any future installation. Do not install this utility, a credential file or an approval as part of this report.

**Stop after publication.** Existing DW English, Dispatcharr, VPN/firewall, systemd and Jellyfin configuration remain untouched. No real provider has been onboarded. Production registration and activation remain explicitly blocked.

## File inventory and SHA-256

All files below are new, isolated from protected deployment source. The report itself is identified by its Git commit rather than a self-referential hash.

| File | SHA-256 |
|---|---|
| `docs/dispatcharr-provider-cli.md` | `e43f871c24248488a86213b6968f563a5f5ea7add90fa068116de2d17594e870` |
| `tools/.gitignore` | `626fc93b32ca6eae046bbfbb2bb50d42dfdbcb6cce8ba261a0b47f119d6b9d87` |
| `tools/dispatcharr-provider.py` | `b9ba1e6f2015911215196b1b2f74eeccf97736f0f867fab86befe30091fd4246` |
| `tools/dispatcharr_provider/__init__.py` | `b0985cd13d70035c2bad764542b99762b44092d1a21234ad38c1dfb72d29270b` |
| `tools/dispatcharr_provider/api-contract.json` | `2f7c8f0af5ce4372e784aba55ac9f3c34f2257535a28210fb7b2dc372998d6b1` |
| `tools/dispatcharr_provider/cli.py` | `3397ba9c2b0fe085e4ad01972baeecd0f4365139938e35fc592d8000977265a9` |
| `tools/dispatcharr_provider/core.py` | `179789668a1bd190b5b00839e1f8b679040115c103d43d026710c2ed0099ae45` |
| `tools/dispatcharr_provider/validation-results.json` | `a761cd04a2a119b757cc2e07574613e3816b30cf7cd8d58c4bb9f245d309d8cf` |
| `tools/examples/dispatcharr-login.example.json` | `f929f6ad35579e1537ddc097a814d96f4e58b3aebc4493f8a6f59f26b7edd4ee` |
| `tools/examples/dispatcharr-snapshot.example.json` | `77d40cec4e7cc5b46be3167ca4aa68633393b589e02783de161921b9115ab09a` |
| `tools/examples/metadata-approval.example.json` | `e735dd5d3dec4f395df28fc8a5510add59c054c4e8a9f8743a479b0c3d40d1e7` |
| `tools/examples/provider-catalogue.example.json` | `9376c820b0b9b9a1c41af9baf54230a9161ec9a544e52f709fc2e5a3812ce39c` |
| `tools/tests/test_dispatcharr_provider.py` | `0c78b31fd171e71ad15dc25c6006610e99107bb2f860e0be4ebfd5f9b216278c` |
