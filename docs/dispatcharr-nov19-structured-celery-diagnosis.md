# Rivendell Dispatcharr structured Celery failure, November 19

**Finding.** The readiness gate rejected the captured stdout. Confidence is high in that immediate cause. Both workers reached their logged ready state, but the exact reason the validator rejected the response remains unknown. The original 290 bytes were deliberately discarded. The evidence supports keeping recovery at NO-GO.

## Historical evidence

All times in this table are UTC on 2026-11-19. The published restoration receipt identifies one managed start. During this review the private result's SHA-256 matched the published digest. Retained Docker output (139 lines in the selected AIO window), the rotated application log and the stack unit journal were filtered on Rivendell. Only timestamps, counts and event categories are reported.

| Time | Source | Observation |
| --- | --- | --- |
| 00:42:40 | Restoration receipt | One managed start accepted. |
| 00:43:06.385 | AIO log | PostgreSQL reported ready. Two later connection-refused lines at 00:43:10.851 and 00:43:16.144 mention uWSGI. Neither identifies a failed Celery broker connection. |
| 00:43:32.665 and 00:43:33.367 | AIO and application logs | Two worker-side Redis broker connection messages. Application timestamps corroborate both within 4 ms after conversion from EST. |
| 00:43:33.593 | Private intent file mtime | Backend invocation intent recorded. Source pins, PostgreSQL/migrations, authenticated Redis and two fresh uWSGI witnesses subsequently passed in this invocation. |
| 00:43:33.774 | AIO and application logs | DVR worker logged ready. |
| Approximately 00:43:34.139 | Receipt and journal clocks | Inspection command/capture began. |
| 00:43:34.421 | AIO and application logs | Default worker logged ready, about 0.28 seconds after capture began. |
| Approximately 00:43:43.397 | Receipt and journal clocks | Capture ended after 9.257686 seconds. Child exit 0, complete stdout 290 bytes, stderr 0 bytes. |
| 00:43:43.445 to 00:43:46.910 | Private result mtime and unit journal | Backend result persisted, then the managed unit failed. Backend exit 1 and Celery child exit 0 refer to different processes. |
| 00:45:11 | Restoration receipt | Cleanup verified all four IPTV containers stopped. Gateway startup was never reached. |

The two estimated UTC times apply the realtime-minus-monotonic offset from 26 same-boot stack journal entries in the incident window to the receipt's monotonic capture bounds. The estimates fall between the intent and result mtimes. They locate the CLI process window. Message publication, worker subscription, individual replies and delivery to the inspector were unobserved.

The November 18 attempt used the human-readable CLI and returned 69. Its zero parsed replies and failure classification belong to that earlier invocation. [Earlier recovery record](https://github.com/APMurtha/homelab-operations/blob/c7181a08d7f1ba81205b8f497629b612a2d80a4a/docs/dispatcharr-original-stack-recovery-completion.md)

## How the November 19 gate decided

The pinned Celery 5.6.3 invocation requested JSON for a broadcast inspect ping, with an eight-second reply option, a 40-second subprocess bound and a 90-second backend limit. It specified no destination. The gate requires child exit 0, complete capture, empty stderr and stdout of at most 16,384 UTF-8 bytes. The parser accepts one JSON object with up to two members, rejects duplicate keys at every depth and rejects nonfinite constants. Each identity must fully match `(default|dvr)@[A-Za-z0-9_.-]{1,253}`. Each role can occur once and its entire payload must equal `{"ok":"pong"}`. Readiness requires both roles. Surrounding JSON whitespace and key order are immaterial.

For exit 0, a valid empty or one-role mapping produces a missing-role classification. An invalid response discards all role witnesses. Here `reply_output_valid=false`, both role flags were false, trusted count was zero and the classification was `celery_unclassified_failure`. Complete capture, size and stderr all met the contract, leaving stdout content as the rejection point. All 30 structured offline tests passed during this review. [Validator](https://github.com/APMurtha/homelab-operations/blob/ee7e6c85258d707bcab35f7521157bb26f9099ac/configs/dispatcharr-iptv/original-backend-diagnostics/candidate/backend.py) · [Contract fixtures](https://github.com/APMurtha/homelab-operations/blob/ee7e6c85258d707bcab35f7521157bb26f9099ac/configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_structured_celery.py) · [Machine-readable receipt](../configs/dispatcharr-iptv/structured-celery-restoration-results.json) · [Restoration timeline](dispatcharr-structured-celery-restoration-results.md)

| Possible cause | Assessment |
| --- | --- |
| Mixed or malformed stdout, unsupported JSON shape, identity, duplicate or payload | Any of these can account for the rejection. No retained discriminator ranks them. A parser defect is unproven. |
| Missing replies or late worker startup | No valid subset was observed. The timing permits a startup overlap. Both ready markers precede capture completion, and neither proves a control reply. A late worker alone would leave a valid subset if the other response met the contract. |
| Wrong destination or broker | No explicit CLI destination. Worker connections and the Redis readiness pass weigh against a general outage. Effective CLI versus worker broker, authentication and namespace equivalence were unknown. No evidence establishes misrouting. |
| Timeout | The child exited normally inside the 40-second bound. The eight-second reply window could still have influenced which replies arrived. Duration alone cannot explain invalid stdout. |

## Current host observation

At **2026-11-23 03:06:51 UTC** (November 22, 22:06 EST), read-only Docker metadata on the verified Rivendell host showed the following. Bag-End's existing SSH key and pinned host-key entry were used because the historical NEST media server profile was absent locally.

| Container | State | Docker restart count | Last finish (UTC) |
| --- | --- | ---: | --- |
| dispatcharr | Exited | 0 | Nov 19 17:31:24 |
| rivendell-iptv-relay | Exited | 0 | Nov 19 17:31:21 |
| rivendell-iptv-vpn | Exited | 0 | Nov 19 17:31:24 |
| rivendell-iptv-gateway | Exited | 0 | Nov 18 20:25:17 |
| jellyfin | Running, healthy | 0 | Nov 19 17:23:34 |

Three IPTV finish times postdate incident cleanup, so continuous downtime since 00:45 cannot be inferred. Docker's restart count does not count every manual or managed start. Current health of stopped workers cannot be measured from these fields.

## Next action and authorization

The smallest diagnostic change is an offline, synthetic-fixture change to the validator that assigns a fixed reason to each rejection branch, for example JSON decode, top-level shape, duplicate key, identity, duplicate role or payload. Keep the existing acceptance rules, and record only the reason enum. This would distinguish causes on a future capture. It cannot recover November 19's discarded stdout.

**Separate authorization is required** to implement that code change under this documentation-only deliverable, install it on Rivendell or run another managed attempt. The evidence supplies no basis for changing timeouts, broker settings or worker destinations. This review used retained evidence and container metadata only. No service lifecycle, provider, playback or bridge operation was performed.
