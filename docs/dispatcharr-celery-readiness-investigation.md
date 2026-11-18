# Original Dispatcharr Celery readiness investigation

**The failed subcheck is confirmed; the precise underlying failure remains unresolved.** Celery exit69 can mean no replies, a broker connection error, or another remote-command exception. Both default and DVR workers reached `ready` during the inspection window. That excludes treating this result as proof that the workers never started. A startup/control-subscription race is plausible, but not established.

**GO for a separately reviewed diagnostic-only readiness correction. NO-GO for a speculative timeout/broker change or an unreviewed restoration start.** No service was started or modified during this investigation. All four IPTV containers remain stopped and protected; native hardening remains suspended.

## Scope and evidence

Incident: `f4298da612300a9024ac8302c8db1252d8d69fc6`, [restoration results](dispatcharr-original-stack-recovery-completion.md). Original AIO image: `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`. Selected access remained Andrew / `andrew-media`, pinned NEST SSH profile `media`, verified Rivendell / `murth` UID1000 with authorized read-only root inspection.

[Sanitized evidence](../configs/dispatcharr-iptv/celery-readiness-investigation-results.json) includes:

- Bounded Docker logs for22:30:35–22:31:50 UTC: **135 lines /17182 bytes**, with only fixed event classifications and allowed roles returned.
- Existing application-log tail: **12521 bytes**, within a262144-byte cap. Local17:31 EST timestamps correlate with22:31 UTC. No raw log lines or connection URLs were returned.
- Existing systemd journal entries for the same window, including fixed backend diagnostic records and journal timestamps.
- Private invocation intent/result metadata and the exact retained sanitized backend result.
- Static original-AIO Celery/Kombu source, worker launch configuration and entrypoint environment propagation. No Celery, Django, Redis or PostgreSQL command was executed inside a container.

Direct `docker cp` requests for stopped-container files returned “file absent.” The existing original image's committed snapshot/root-chain metadata was inspected. A print-only snapshot mount-metadata query was refused for the committed snapshot; **no mount or new snapshot was created**. A bounded metadata lookup of four known paths across374 existing layer directories located the local AIO library copies. The two virtualenv/library copies inspected were byte-identical; app entrypoint copies also matched. Selected static files were read directly, without image export, recursive filesystem scanning, package installation or application execution. This is recovered static-layer evidence, not a live version invocation or an observation of which CLI exception branch ran.

## Timeline

All Docker/journal times below are **2026-11-18 UTC**. Application logs independently show the corresponding EST times.

| Time | Evidence |
| --- | --- |
| 22:30:40.352 | Journal: the single authorized managed start begins. |
| 22:31:05.167 | Docker log: PostgreSQL ready to accept connections. |
| 22:31:09.461 | One connection-refused message. Retained classification does not identify its component; do not label it a Celery broker failure. |
| 22:31:14.928 | Two uWSGI workers spawned. |
| 22:31:15.227–15.327 | First role-bearing worker startup messages; these do not prove consumer readiness. |
| 22:31:29.345 | Durable backend invocation intent file mtime. This precedes launching the backend, not necessarily the Celery command. |
| 22:31:30.580 /30.727 | Worker logs report Redis broker connections; application log times17:31:30.578 /30.726 EST corroborate them. |
| Approximately22:31:30.76 | **Estimated** Celery inspection process launch from backend elapsed records and receipt mtime. Exact publication time was not retained. |
| 22:31:31.667 | Default worker logs `ready`; application log17:31:31.666 EST. |
| 22:31:31.814 | DVR worker logs `ready`; application log17:31:31.813 EST. |
| 22:31:39.704 | Result receipt mtime: backend failed, child inspection returned69. |
| 22:31:39.714 | Journal receives validated records and the generic lifecycle failure. |
| 22:31:43.836 | Journal: managed unit failed after scoped cleanup. |

The backend receipt is invocation `3bb14e388660a22ed7f62a9aacb795ea`. Its producer clock records Celery-stage entry at0.710226s and failure at9.654352s, a **8.944126-second** stage duration. Before it, source pins, PostgreSQL/migrations, Redis and two fresh uWSGI witnesses passed. The inspection subprocess returned69, not a40-second `subprocess.TimeoutExpired` failure.

**Important timing limit:** lifecycle code forwards all records only after capture/receipt completion. Their journal timestamps are not individual stage-start times. The approximate launch time subtracts producer elapsed time from result-file mtime; IPC/drain/write delays were not measured. No exact broker publication/subscription/reply timestamps exist. Worker `ready` messages occurred before inspection failure, so it is inaccurate to say “both workers were unavailable throughout the eight seconds.”

## Exit69: installed source interpretation

Recovered local AIO package source identifies **Celery5.6.3**, with virtualenv Python3.13.17. The306-byte executable at `/dispatcharrpy/bin/celery` is a normal Python launcher calling Celery's `main()` and passing through its result; SHA-256 `a36c6599754b5de4a2af22fb7d02b84c474045e29fdb3a2bef093c8dd7383696`. No custom wrapper branch maps worker state to69.

Relevant static source paths beneath `/dispatcharrpy/lib/python3.13/site-packages/`:

- `celery/platforms.py:51`: `EX_UNAVAILABLE` is69 on this platform.
- `celery/bin/control.py:178–198`: `inspect` requests replies; empty replies raise a `CeleryCommandException` with `EX_UNAVAILABLE`.
- `celery/bin/base.py:123`: an `OperationalError` is converted to a broker-connectivity exception with **the same69**; other remote-command exceptions are also converted to69.
- `celery/exceptions.py:307`: the command exception carries the requested exit code.
- `celery/bin/celery.py`: normal application-import failure handling uses Click context failure; there is no evidence here of a substituted launcher or newly changed dependency. The actual CLI stderr was not retained, so unusual application exceptions cannot be categorically excluded.

Therefore69 alone does **not** identify a no-reply timeout. Zero regex matches also cannot distinguish a silent no-reply result from an exception that reported only to stderr. Broker-error text may contain a sensitive connection string; recovering observability must preserve fixed-code redaction rather than forwarding that text.

## Exact readiness and startup behavior

Fresh installed-source hashes match the incident candidate:

- `backend.py`: `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8`.
- `lifecycle.py`: `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac`.

The host lifecycle executes the backend as UID/GID1000 after sourcing the image-generated profile. The backend then runs exactly `celery -A dispatcharr inspect ping --timeout=8`, cwd `/app`, with captured stdout/stderr and a40-second subprocess bound. It requires return0, exactly two matches of `->\s+([^:\s]+):\s+OK\s+pong`, and role prefixes exactly `default` and `dvr`. The90-second outer backend capture bound remains unchanged.

The original uWSGI configuration starts Redis and both Celery workers as attached daemons. Default uses the `celery` queue/name `default@…`; DVR uses the `dvr` queue/name `dvr@…`. Those names match observed logs and the readiness predicate. A source-backed synthetic formatter example matches both names with the existing regex; this is only a static parser check, not recovered runtime stdout. **A parser mismatch cannot itself cause the already-returned child exit69.**

The AIO Docker health check tests local HTTP only. Neither it nor the earlier uWSGI heartbeat gate guarantees that both Celery remote-control consumers are ready. Lifecycle ordering waits for container health and immediately performs the single backend check; there is no preceding Celery-specific startup gate.

Kombu's inspected `_broadcast` implementation publishes once and then collects replies. Pidbox consumers begin listening during consumer startup. The eight-second option bounds reply collection; it is not a worker-initialization/rebroadcast loop. A request sent before subscriptions exist can be missed despite later `ready` logs. That is a viable mechanism, but the precise publication timing and error branch needed to prove it are missing. Simply increasing8 seconds is not an evidence-based fix.

## Cause assessment

| Candidate cause | Evidence / conclusion |
| --- | --- |
| Permanently missing/crashed default or DVR worker | Not supported: both reached `ready` and connected to Redis in both retained log sinks. No matching fatal/traceback/crash event was found in the bounded Docker window. This does not prove they answered control requests. |
| Startup/control subscription race | Plausible: process launch overlaps worker initialization; one-shot publication has no readiness/rebroadcast phase. **Not confirmed** because exact send time and CLI failure classification were discarded. |
| Redis generally unavailable | The backend Redis PING passed, and both workers logged broker connection. A CLI-specific connection/remote-operation error remains possible. |
| Invocation broker/environment difference | Not excluded. Docker creation environment includes an explicit loopback broker override; the login-profile variable list does not propagate that override, while workers launch through the login/uWSGI path. This is not proof that the resulting endpoints/authentication differ. Do not change either configuration without a private semantic comparison of their effective settings. No credential or URL value was exposed. |
| Command wrapper/dependency/app initialization | Source shows a standard launcher and valid `inspect ping` operation, with no observed version/image drift. Missing runtime stderr prevents complete exclusion of an unexpected CLI exception. |
| Wrong worker names / reply parser | Roles match the static launch configuration and observed ready messages. No implementation defect demonstrated; parser output cannot explain the subprocess's nonzero return code. |
|40-second subprocess deadline | Excluded for this occurrence: receipt records return69 after approximately9 seconds, not a timeout exception. |

**Confirmed root cause remains unavailable.** Confirmed facts are the failed CLI/control stage, overlapping initialization, subsequently ready workers, and a diagnostic projection that intentionally collapsed multiple69 branches into `celery_command_failed`. No functional application/readiness defect has been conclusively demonstrated.

## Smallest justified next action

Prepare a **separately authorized diagnostic-only correction to the existing original backend**, with matching private-record validation/manifest updates:

1. Classify the bounded child output into fixed codes: exact no-node-reply message, broker-operational-error prefix, other remote-command exception, usage/import failure, or unknown. Never publish raw stdout/stderr, exception text, URLs, credentials or environment values. Unknown/malformed/truncated evidence remains fail-closed.
2. Retain command-specific monotonic start/end, return code and bounded byte counts in the same invocation receipt. Retain journal/worker-ready timestamps separately; do not mistake buffered forwarding times for execution times.
3. If the invocation-environment hypothesis needs resolution, compare effective broker endpoint/auth configuration privately against the worker launch context, emitting only reviewed equality/presence booleans. Do not invoke a running broker outside a separately authorized restoration attempt.

Preserve the exact readiness predicate, role requirements, eight-second probe option, existing overall bounds, managed lifecycle and cleanup. Do not add retries or a sleep now. If a future controlled observation specifically establishes a startup no-reply race with matching broker contexts, review a bounded Celery-readiness polling correction within the existing overall budget; do not treat generic69 as permission to retry arbitrary errors.

This is the minimum additional observation needed to choose between a timing correction and a CLI/broker-context correction. No database change, recreation, Redis reset, security change or hardening deployment is justified. **No proposed patch was implemented or installed in this task. A new managed restoration start requires separate authorization.**

## Static source inventory

These are selected read-only source fingerprints, not new production pins or permission to accept drift.

| Package file | SHA-256 |
| --- | --- |
| `celery/__init__.py` | `84a164d3862145db4ac21717f808ceeeb289ae885b873978b5df234cd831d16b` |
| `celery/bin/control.py` | `c1267b714e2100b4c7f9817833a985f6f4cf704da08485ddaaa33279f54efbdd` |
| `celery/platforms.py` | `0c30860a9f32b7a7ff0eb64f4a20a359b8eed87242b0559f934cad49ff810f10` |
| `celery/bin/celery.py` | `76730385bda66607440b5dd34c688f987f6eb15103d55f2ee887e7b672c601ac` |
| `celery/worker/pidbox.py` | `2dc42c28391df19f779d0c64d1238bba507c18b11f2233e437e274a4693b75f3` |
| `celery/worker/consumer/control.py` | `d0d889f4ff801ddbf5df899792046053d85f85d27f3fb1ca6fbcfd0385ea6b64` |
| `kombu/pidbox.py` | `959ffb7345bc60255973a1a13673c9e422847f58a7b5ab2a39539ea7e9088e8b` |
| `celery/bin/base.py` | `922af38f29c48c06246dc5cf0b0e8b5bf1fe2ed58886ef6d1d182c6188db0bb7` |
| `celery/exceptions.py` | `16b971422a1d46dc7446b25f810a3964c61327c05286b264b5e487dbd4c250a3` |
| `celery/worker/consumer/consumer.py` | `4993370f72b92a96a692bee0b711e0fcc32ce022080dcbc2c3e8204989fa190f` |
| `celery/worker/worker.py` | `8afaee27658ae49caf17bacb62eb8c1df5649627ceaeb425ef5971ea0e165263` |

Entrypoint SHA-256: `af1353b20193c7e9f19a50b8e0ff5bbcfd40f45273cb6957a2495e8f2a22cc8c`; original uWSGI configuration: `2e9fe2643141b14d31ee2625c4fa312e3c45c636cda200c40f29c08306844992`. Previously extracted local entrypoint/app-Celery source copies were compared with these recovered static-layer bytes before relying on their trace. No source or manifest was regenerated.

## Preservation and decision

At23:08:21 UTC, all67 current diagnostic-baseline files and all33 container fingerprints matched the failed-cleanup state. All four IPTV containers remained stopped; Jellyfin healthy; Docker process/network/volume fingerprints unchanged. Exact kernel nftables verification passed, guard/grant assertions remained withdrawn, provider projection empty and guard transaction revoked/unblocked. Ownership state had no pending transaction. Subsequent inspection only read static source/application logs.

The original private result receipt still hashes to `5f5efba1fc7374931345410e247b7359df95ee319b1bcffe29535946b7e9fa51`. No receipt was cleared. No Docker lifecycle/exec, systemd lifecycle, application write, provider request, playback or production installation occurred. Only this report and sanitized evidence were added to the repository.

**Final: GO for reviewing the minimal diagnostic correction described above; NO-GO for asserting a confirmed startup race, applying a speculative functional fix, or attempting another restoration start without authorization.**
