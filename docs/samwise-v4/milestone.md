# Bridge V4 milestone 1

## Evidence inventory, 22 November 2026

The inspection covers the Git tree at ca0a7d7dab101a20b5a0a4d91e18585fe1acda92 on samwise/bridge-v3. Main at 529c3cf lacks the Dispatcharr tree. The evidence checkout contains 58 docs/dispatcharr* files. The following records distinguish historical observations from candidate configurations and synthetic tests.

| Inspected repository evidence | What it establishes |
|---|---|
| docs/dispatcharr-permanent-streaming-artifact-review.md | Summarizes Phase 5B stale Redis singleton and two later Phase 5H successful H.264/AAC remux sessions. The referenced private phase5h-analysis and phase5i-closure copies, original session logs and linked Phase 5G report were not inspected. |
| configs/dispatcharr-iptv/permanent-streaming/tests/fixtures/relay-stopped-18bdf54.json and tests/test_candidate.py in that directory | Sanitized stopped-relay mount projection and offline tests of generation identity, budgets and allowed HLS content. Neither measures broadcaster health. |
| docs/dispatcharr-jellyfin-integration.md and docs/dispatcharr-xteve-retirement.md | Channel 9001 and local placeholder XMLTV were discovered. An API-client capability negotiation stopped an attempt before decode. Retirement report records prior owner playback confirmation. |
| docs/dispatcharr-celery-readiness-necessity-review.md and configs/dispatcharr-iptv/celery-readiness-necessity-review-results.json | Dependency analysis and pin inventory. Original live_proxy handler and four-file readiness patch bodies were incompletely retained. |
| docs/dispatcharr-original-stack-recovery-completion.md | PostgreSQL, Redis and two uWSGI witnesses passed in one invocation. Celery returned 69. Registration and gateway start were never reached. |
| docs/dispatcharr-structured-celery-restoration-results.md and configs/dispatcharr-iptv/structured-celery-restoration-results.json | November 19 managed retry returned 0 from the Celery command but failed structured reply validation. All four protected containers ended stopped, Jellyfin healthy, rebind unreached. Raw reply and precise rejection reason unavailable. |
| configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_structured_celery.py | Synthetic reply grammar cases available for offline comparison. No production reply to replay. |

Historically, Jellyfin read local M3U/XMLTV exports for DW English. A TS request went through Caddy to the Dispatcharr AIO live proxy. AIO selected the owned channel/stream and streamcopy profile using PostgreSQL and Redis. FFmpeg consumed HLS from a fresh opaque relay endpoint. The relay fetched approved broadcaster segments through the guarded VPN namespace. Admission, backend readiness, registration and export rebinding preceded gateway startup. Current availability and topology drift are unknown.

| Hypothesis | Reproducible offline discrimination | Remaining evidence gap |
|---|---|---|
| Backend readiness prevents downstream operation | Compare managed_start and terminal_status in the structured receipt with the November 19 timeline. Check the structured reply validator against its synthetic tests. | Invalid output did not prove either worker was absent. Broker comparison unknown. |
| A stale Redis client/producer generation blocks input | Compare the Phase 5B account with the two later uWSGI witnesses and the session generation in a same-attempt trace. | No synchronized failing worker/Redis trace. A successful ping cannot establish producer health. |
| Empty relay broadcaster inventory prevents segment fetch | Distinguish a zero-fetch health check from a rejected configured route or an actual zero broadcaster count using same-generation registration and relay receipts. | No same-attempt inventory/count, binding and segment receipt supplied. |
| Jellyfin cannot ingest/remux H.264/AAC | Compare recorded API negotiation stop with two successful Phase 5H sessions. Correlate client negotiation, first TS bytes and FFmpeg input from the same session before attributing a codec failure. | No failing session's correlated client, relay and FFmpeg logs. |

No separately authorized staging evidence copy was identified for inspection. Historical private paths are references only. Present host state, provider reachability and media playback require separate evidence. After independent review, staging and separately approved live GitHub acceptance, a Rivendell investigation would need explicit owner authorization for the person/system, read-only account, exact service/status and sanitized receipt fields, time window and retention. Playback, provider traffic, secrets, state resets and service changes require distinct decisions.

## Execution and trust boundaries

V3 worker_v3.py binds an owner ready-event and comment to the issue digest, rejects edits, claims once in private SQLite and publishes a validated parity helper as a draft. development.py and runner.py isolate a fixed program in a pinned rootless Podman image. V4 gets a separate entry point, checkout and ledger. The operator invokes it for one issue. V4 recognizes only this single-line body (substitute the full current main SHA):

    samwise-task-v4: dispatcharr-evidence-v1 <40 lowercase hex>

The input manifest is compiled into the worker: the artifact review, Jellyfin integration, structured restoration report and structured restoration JSON named above. The only output is a new root file samwise-dispatcharr-evidence.md. The inventory lists byte lengths, SHA-256 fingerprints and whether the machine receipt matches the historical reviewed failure. Changed evidence requires human interpretation. No issue-controlled paths, instructions, scripts or model prompts enter the runner.

The GitHub controller binds repository ID 1126036330, issue number, owner ID 57697374, immutable body digest, latest label transition and latest comment. The owner applies the dedicated samwise:v4-ready label and posts an unedited approval binding its event node ID and digest. Closure, edits, a new label event/comment or withdrawn approval cancels the claim on recheck. Concurrent or interrupted claims cannot rerun. A publication interrupted after an external write needs manual reconciliation against the recorded issue/base and draft branch; never erase the receipt to retry.

The controller reads fixed ordinary blobs from Git objects, with a size cap and an exact current GitHub main tip. It checks the output path is absent. The isolated runner receives only blob bytes, computes fingerprints, and returns bounded JSON. The host verifies every value before rendering fixed Markdown. Rootless Podman uses the reviewed V3 image ID, private namespaces, network none, read-only root, no host mounts, dropped capabilities, UID 65532, bounded scratch, 4 CPUs, 3584 MiB memory, no additional swap and 128 PIDs. Only the controller may use a repository-scoped GitHub identity. No SSH setup, production credentials or runtime socket belongs in this account. Publication uses a fixed issue-derived branch, the approved parent and the existing draft-only publisher. Remote authorization and publication are separate operations; revocation after the final check can race with publication.

## Staging and acceptance gates

1. Independently review this diff against samwise/bridge-v3. Install reviewed code in a separate staging checkout/account with private state, no SSH agent, production tokens, mounts or V2/V3 database access. Do not install a service for this milestone.
2. On separately authorized staging 10.10.20.201, pre-provision the exact local rootless image identified in development.py, Podman, cgroup v2 delegation and enough RAM/disk. Under a credential-free account run the offline tests and the local staging probe documented below. Capture image identity, cgroup limits, network/mount inspection, output hashes, exit and container removal, including timeout/failure cleanup. V3 staging evidence does not qualify V4.
3. A later live acceptance needs independent approval, a main tip containing the four inputs and an absent output, a dedicated controller checkout with the same objects, restricted GitHub credentials and a fresh issue. Use an independent V4 state directory/service identity on Bag-End if subsequently deployed. Issue 20 is specification text. This implementation PR targets the evidence-bearing v3 branch; no deployment or integration into main is implied.
