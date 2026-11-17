# Dispatcharr scoped orphaned-record cleanup — PASS

2026-11-17 UTC (2026-11-17 US/Eastern). Rivendell `10.10.20.30`, Andrew's selected `andrew-media` access. The owner separately confirmed deletion authorization and exclusive administration after reviewing the procedure. Scope was limited to hidden DW English channel **2** and managed stream **2**, using reviewed commit `227122dcbe9ebc76be46b8a91231350d6c93bdb4`.

**Result: both owned records deleted and authoritative detail absence verified. Original protected three-service stack remains healthy and unchanged.** Default Group 2, streamcopy profile 1, the approved ACL, Jellyfin and unrelated services were preserved. No deployment, container lifecycle operation, systemd change or playback occurred.

## Fresh preflight

At **05:29:06 UTC**, before deletion:

- Original VPN/AIO/gateway were healthy. Original running/guard contracts and all 17 protected hashes passed; the expected pinned API source matched. Administrative credentials authenticated as level 10.
- Both authenticated detail GETs matched the private ownership ledger and retained deployment receipt exactly. Channel 2 was hidden and referenced only stream 2. The complete `visibility_filter=all` inventory contained only channel 2; no other hidden or visible channel referenced stream 2.
- No recordings, Redis `live:channel:*` keys or FFmpeg/FFprobe processes were present. The relay was absent; no current consumer was observed. This is an idle-state snapshot under the confirmed exclusive window, not a guarantee against future requests.
- State contained only the existing lock and `owned.json`; no pending registration journal, commit marker or unresolved DELETE intent existed.
- Default Group 2, locked streamcopy/MPEG-TS profile 1 and exact ACL digest `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e` passed. Full group/profile/settings inventory was hashed privately for comparison.
- Fresh snapshots captured all container identities, image/configuration/mount hashes, start times, health, Docker/network identities and Jellyfin Live TV configuration hash.

## Reviewed execution and deletion verification

The exact reviewed `files.py`, `api.py`, `health.py` and `register.py` bytes were loaded in memory in the existing AIO as UID/GID **1000:1000**. No candidate files or images were installed. The existing private state lock was held, administrative/ownership/reference checks repeated, and **only** `rollback_owned` was invoked. There was no mutation retry wrapper.

| UTC | Result |
|---|---|
| 05:30:10 | Single scoped cleanup invocation began after fresh unchanged-state checks |
| By 05:30:13 | Reviewed rollback returned; durable receipt complete; channel/stream inventories empty and detail absence checks passed |
| 05:31:24 | Independent read-only reconciliation passed: channel 2 detail **404**, stream 2 detail **404**, all-channel/stream counts **0** |
| 05:32:02 | Final protected-stack/security/unrelated-service checks passed |

The reviewed transport requires **HTTP 204** for DELETE; the reviewed rollback requires subsequent detail **404**. Channel deletion and its absence verification precede the repeated hidden-inclusive reference scan and stream deletion. Completion is written only after final authoritative absence checks. The complete durable receipt and successful function return establish this path; a raw per-request event transcript was not persisted after the post-check described below.

`/data/permanent-streaming/rollback-owned.json` is retained **1000:1000 0600**, with `state=complete` and both deletion stages `absent`. The ownership ledger is retired. No pending journal or DELETE intent remains. Receipt SHA-256: `53203a5bbaedfa402a545917eddc8ccbe97397a2814d79014fdd3c9072361325`. Its private ownership contents and stale endpoint are not published.

### Post-check deviation and read-only reconciliation

After the reviewed rollback returned, the outer diagnostic wrapper exited 1 at a comparison of the entire group/profile/settings inventory. **No DELETE was repeated.** The completed receipt and fresh detail reads established known successful outcomes.

The inventory difference was exactly Default Group 2's **derived `channel_count`: 1 → 0** after removal of its owned channel. Reconstructing the prior inventory by changing only that field back to 1 reproduced the exact preflight SHA-256 digest. This proves the remaining group fields, complete profile inventory and all settings were unchanged. The group was not deleted or edited. No candidate correction, receipt clearing, forced reconciliation or additional API mutation was used to resolve the diagnostic assertion.

## Final acceptance

- Both detail endpoints return 404; complete hidden-inclusive channel inventory and stream inventory are empty. No unrelated channel or stream existed in preflight or was removed. Default Group **2** and streamcopy profile **1** remain available.
- Exact approved ACL digest remains `cede3b0a514ef30c4d77fbcd09c0e079d9369afc7dcd82dfe9771acaaec60a3e`; unrelated groups/profiles/settings match the preflight inventory apart from the expected derived count.
- Original three containers remain healthy, with the same IDs, immutable images, configuration/mount hashes, start times and restart counts. The relay remains absent. All genuinely unrelated containers and Docker/network identities are unchanged.
- Original 17 protected hashes, exact nftables guard, VPN-only tun0 routing, OUTPUT/DNS restrictions, loopback resolver and disabled IPv6 pass. Guard and stack units remain active/exited, Result=success, without reload or restart.
- Application HTTP and gateway health return **200**. PostgreSQL retains **184** migrations, fingerprint `b00f51e91c5b882cd84d3b2579d074ca`; channels 0, original M3U account 1, EPG sources 0. Redis responds; no media process is active.
- Jellyfin remains healthy at peer `172.20.0.2`; Live TV configuration SHA-256 remains `28d72351abb46aac33dff87e30ff4bf58ae44122d63b6e3197b26a843540a71b`. No Jellyfin setting or playback was touched.

Private preflight, command/error, reconciliation and final verification receipts remain under `/docker/dispatcharr-iptv/private/scoped-cleanup-227122d-20261117/` (root-private directory/files). The private application rollback receipt remains in the AIO's persistent state. No credentials, tokens, broadcaster URLs, endpoint values or recovery data are published.

Reviewed execution hashes:

| Module | SHA-256 |
|---|---|
| `files.py` | `314e4c70f7daf02bd6d1ce8a5bb8cc60690365d4507c3f99915ae2c5cf79723a` |
| `api.py` | `74b824154c19b1fc612330ddf462b80bdc7ada830da502b737bb944ac4e32b6c` |
| `health.py` | `f4da54dece514ea24df5a6561ce52b883a1737213634b95bb1eab94a1b4ec6db` |
| `register.py` | `a92d5cbba346238d8c2807587be02201d4fa93e50a416bc5975ba4fe7eb16055` |

**Cleanup PASS.** No further cleanup or deployment was attempted. The completed rollback receipt intentionally blocks automatic registration recreation. Reconciliation of that latch, inactive exports and staged candidate files belongs to a separately authorized future deployment. Leave the original protected three-service stack running.
