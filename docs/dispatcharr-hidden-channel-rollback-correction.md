# Dispatcharr hidden-channel rollback and tmpfs correction

2026-11-17 UTC. Rivendell, Andrew's `andrew-media` target. Offline correction based on failure report `c61125333c856a4c9fb80006038fa0f8d2a49ae7` and candidate `824d0be03af997762160e7bb7dd1fa497a5dfd9f`. No production code was installed and no channel or stream was deleted.

## Retained state — read-only verification

At 05:17:06 UTC, authenticated supported API reads with the existing level-10 administrator established:

- Channel detail ID **2** exists, is hidden, matches every saved ownership field, and references only stream **2**. Stream detail ID **2** matches its ownership ledger and the retained deployment receipt.
- `visibility_filter=all&page=N` returns channel 2. No other channel, including hidden channels, references stream 2. The default collection's omission is a visibility filter, not deletion.
- Recordings are empty, Redis `live:channel:*` keys are absent, and no FFmpeg/FFprobe process exists. The managed relay is absent and its endpoint is inactive. No current playback/recording consumer was observed; these checks are a snapshot, not a lock against future requests.
- The private application-state directory contains only `owned.json` and its existing lock. No pending/uncertain registration journal, commit marker or owned-rollback receipt exists. The earlier failed cleanup stopped before invoking the destructive function.
- Default Group **2**, locked streamcopy/MPEG-TS profile **1**, and the approved exact ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e` remain unchanged.
- The original three-service running contract passes. Unrelated container/configuration identities, Docker process and networks remain unchanged. Jellyfin was not modified.

The running original AIO's `apps/channels/api_views.py` hash was rechecked as `0d211a4287943b47999f642fdaaec1e368ad331943901e2237c60b09474c38fa`, matching the pinned source at Dispatcharr commit `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`. Its list action defaults to active visibility, supports `visibility_filter=all`, and permits hidden detail retrieval/deletion for an authorized administrator. No API record/settings writes were performed; authentication token acquisition was the only POST.

Final read-only recheck at **2026-11-17T05:24:17Z** reconfirmed the same retained records, zero shared references/recordings/live-channel keys, no pending journal, and unchanged protected/unrelated state.

## Root causes and corrections

**Hidden ownership:** rollback and restart registration inferred presence/absence from the default channel collection. That excludes the intentionally hidden managed channel. Known owned IDs now use authenticated detail GETs. Complete channel scans use the narrowly allowlisted `visibility_filter=all` query, including pagination, for collisions and shared-reference checks. Both records must match their saved ownership fields before any deletion; a truncated or out-of-scope ledger refuses.

Only an actual HTTP **404 on a known stream/channel detail GET** means absence. Authorization errors, collection 404s, malformed responses and server/transport errors cannot establish deletion. This relies on freshly verified administrative credentials and the pinned API behavior: a permission-filtered user's 404 is not an authoritative ownership check.

Owned rollback writes a durable per-record DELETE intent before mutation. Channel deletion must return **204**, then detail GET must prove absence before stream deletion. The complete hidden-inclusive reference scan repeats before stream deletion. Final detail checks establish both absences before ownership retirement. A complete receipt is durably written first and blocks automatic registration recreation.

After interruption, an explicitly authorized invocation may reconcile a pending deletion by detail GET if the record is absent. If it remains present, the saved intent blocks another DELETE even when the previous request may have failed before taking effect. No blind retry, receipt clearing or automatic recovery is provided. Existing registration journals/commit markers and edited/shared records still refuse. Known-ID journal rollback also uses detail reads and durable DELETE intents. Existing-ownership rebind uses detail lookups so managed restarts do not mistake a hidden channel for a missing one. Legacy owned-rollback receipts without the new progress fields require explicit review; the current retained state has none.

**Docker tmpfs:** the running verifier required `/tmp` in `Mounts`, although the deployment's Docker representation retained its exact configuration only in `HostConfig.Tmpfs`. The latter remains mandatory and must exactly equal `rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700`. Either lifecycle state may omit the redundant `Mounts` entry. If represented, tmpfs type, writable status, empty source/mode/propagation remain checked. All six exact bind mounts, duplicate/extra/missing bind rejection, read-only sources, namespace, capabilities and resource limits remain enforced.

The sanitized fixture contains actual mount/tmpfs fields from the failed deployment's retained inspect. **Capture occurred after automatic cleanup, with Running=false**; a full pre-cleanup running inspect was not retained. Tests apply these captured fields to synthetic stopped and running states. This is not presented as a live running capture or a newly deployed runtime acceptance.

## Offline validation

**278 tests pass**, zero failures/errors/skips: the previous **251-test baseline**, plus **26** rollback/transport regressions and **one** captured mount regression. Existing mount tests were corrected to accept the observed optional representation while retaining all security negatives.

| Suite | Tests |
|---|---:|
| Relay policy, registration, exports, lifecycle | 39 |
| Hidden ownership, deletion ordering, interruption and API transport | 26 |
| Four-service security contract | 17 |
| Diagnostic inventory / provenance | 7 / 3 |
| Minimal persistence / boot admission | 12 / 28 |
| Trusted guard permissions, crash boundaries, units and cleanup | 50 |
| Isolated DNS/TLS/resources / native Caddy groups | 13 / 15 |
| Historical persistence / prior guard counterexamples / design models | 26 / 14 / 28 |

Tests cover hidden collection omission with detail presence, hidden sharing, changed/unowned/truncated ownership, missing/malformed detail, 401/403/404/503 handling, DELETE 204, uncertain before/after effects, no repeated pending DELETE, reappearing channel, interrupted receipt retirement, pending registration refusal and restart rebind. Mount negatives still reject altered/missing tmpfs options, unsafe optional tmpfs entries, missing/extra/duplicate binds, writable sources, wrong namespace and changed resource/privilege limits.

Network tests used isolated user/network namespaces with loopback and synthetic fixture addresses only; no external route or broadcaster request. The retained Caddy binary hash remained `a563843e11cbce39c557bd429ebb787d56f49d51d9bbb3292cd9b36b37a60cdf`; 91 synthetic gateway requests passed. Native offline unit checks passed without loading or executing services. Final provenance and the 50 trusted-guard tests were repeated after manifest metadata updates.

Reproduce with `CADDY_TEST_BINARY=/path/to/verified/caddy sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh`, plus the existing historical persistence, guard-interface-review and trusted-guard-design runners recorded in `validation-results.json`.

## Proposed cleanup — requires separate authorization

1. Obtain an exclusive administrative window and fresh cleanup authorization. Reverify the original healthy stack, administrative role, pinned API source, idle/playback/recording state, unchanged ACL/group/profile and exact private ownership receipts. Compare channel/stream details and the complete hidden-inclusive reference inventory; stop on any conflict.
2. Verify the corrected source hashes below. Execute only the reviewed API/rollback modules in the existing AIO's UID/GID 1000 context, using its private credentials and existing state lock. This can use a reviewed in-memory module bundle; it requires no image, unit, guard, container or production candidate installation. Do not run registration/startup, change permissions, expose credentials in arguments, or copy historical private endpoints into logs.
3. Invoke only `rollback_owned` for the ledger's channel 2 and stream 2. Preserve durable receipts privately. DELETE channel 2, require 204 and detail 404; repeat all-channel reference scan; only then DELETE stream 2, require 204 and detail 404. A prior pending request must have settled before explicitly authorized reconciliation. If a pending DELETE's row remains, stop for review rather than repeat it.
4. Verify both detail 404s, no shared references, absent ownership ledger, complete receipt, unchanged group 2/profile 1/ACL, and healthy unchanged original stack/Jellyfin. Preserve the receipt and diagnostics. Reconcile the completed rollback latch and inactive stale exports only as part of a separately reviewed future deployment; do not silently enable registration afterward.

No server-side CAS or atomic all-channel snapshot exists here. Exclusive administration, bounded detail reads and repeated scans reduce risk but do not eliminate check-to-use races or future consumers. They are prerequisites, not claims of transactional concurrency protection.

## Scope and decision

**GO for separately authorized, fresh conflict-checked cleanup review/execution. No cleanup was performed. NO-GO for deployment under this task.** Live DELETE behavior remains unexercised by this offline correction. Any fresh mismatch cancels the proposed cleanup.

No guard publisher, private/public readiness schema, unit, admission threshold/timeout, image identity, Compose mount, resource limit, relay request budget, gateway routing or Jellyfin behavior changed. The retired historical controller remains under its old disabled pins. Original production baseline hashes and the prior inactive-candidate reconciliation hashes are preserved. The corrected candidate remains local/Git only; previously staged production files were not updated.

The candidate manifest has 45 source entries (47 candidate files including manifest/results). The coordinated transition now has **67** target mappings, adding only the new regression module and fixture to the previous 65. Updated manifest entries correspond only to the reviewed files below. The report itself is identified by its publishing Git commit rather than a self-referential hash.

## Changed-file SHA-256 inventory

Paths are relative to the repository. Compared with `c611253` (candidate sources unchanged since `824d0be`):

| File | SHA-256 | Reason |
|---|---|---|
| `configs/dispatcharr-iptv/permanent-streaming/README.md` | `8d47edb478a1e2845f358b75f6e374076e3fdee0b0d423752e108c800d532312` | Document hidden-detail cleanup, durable intents and exact tmpfs contract |
| `configs/dispatcharr-iptv/permanent-streaming/api.py` | `74b824154c19b1fc612330ddf462b80bdc7ada830da502b737bb944ac4e32b6c` | Narrow all-visibility reads, detail 404 classification and DELETE 204 |
| `configs/dispatcharr-iptv/permanent-streaming/contracts.py` | `2faddb7e2d33a2d1a841abd36244770101c294a69df6cb527dae773eef90fe20` | Accept optional tmpfs Mounts representation; exact HostConfig remains mandatory |
| `configs/dispatcharr-iptv/permanent-streaming/manifest.json` | `9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c` | Only changed/new candidate source hashes |
| `configs/dispatcharr-iptv/permanent-streaming/register.py` | `a92d5cbba346238d8c2807587be02201d4fa93e50a416bc5975ba4fe7eb16055` | Detail ownership, hidden references and durable conflict-checked deletion |
| `configs/dispatcharr-iptv/permanent-streaming/tests/fixtures/relay-inspect-c611253.json` | `d7aa9f8ae10fed661cbea925a64295a8045720b2b22d49fa52f52ed7f492c3b1` | Sanitized actual failed-container mount projection |
| `configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh` | `978694b1160ebdd0fe3e7fba861964188b690305976052759961927419e90790` | Run new rollback regressions |
| `configs/dispatcharr-iptv/permanent-streaming/tests/test_candidate.py` | `afa66139f415e6aabc0d305c71fd4f171c0fa7e693a217dcabaa0ae432d0d66f` | Make synthetic detail absence an explicit 404 |
| `configs/dispatcharr-iptv/permanent-streaming/tests/test_contract.py` | `3f2545316b816314a6a540eab643bf37493b33ea1181cfce67a5b2840c7e6e52` | Observed stopped/running representation and unchanged negatives |
| `configs/dispatcharr-iptv/permanent-streaming/tests/test_rollback.py` | `5b320ffd27a19f2f659223af4158537b405884ec4e32b625faee56a15a31f0a6` | 26 synthetic ownership/transport/interruption tests |
| `configs/dispatcharr-iptv/permanent-streaming/validation-results.json` | `1fdffff152283fd7e141d94c9c6fdfe076dfd16768b31dc5b8485da3b5abe0c9` | 278-test results and production-read boundary |
| `configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json` | `47ae4041f2ec9e35c46cf586133001562ce0e3fdde6804fe21c54ce01f6672c8` | Affected mapped/source hashes and two new test mappings |
