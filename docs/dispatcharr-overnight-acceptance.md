# Dispatcharr overnight acceptance

Starting evidence: `3f1b2c08d684e08c356cb82930b9a04d655a66f8`.
Retained image: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.
Scope: at most three additional isolated attempts; image-binding review only, never deployment.

## Demonstrated fixture correction

The preceding attempt stopped on a background `refresh_plugin_repos` hostname
lookup. The pinned upstream `apps/plugins/apps.py` at
`2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e` queues a startup refresh with a ten-second
countdown and wires a periodic refresh. Its supported
`DISPATCHARR_SKIP_PLUGIN_AUTODISCOVERY=1` opt-out returns before both operations.
The task fetches manifests for enabled plugin repositories. The previous audit
record does not disclose the hostname or prove a completed external connection.

The synthetic test environment now sets this opt-out before Django initialization,
including inherited uWSGI fixture processes. It additionally requires no plugin
refresh periodic schedule and verifies the plugin task is still registered.
This excludes plugin maintenance from this acceptance scope; it does not establish
that production plugin maintenance is safe or authorize its network requests.
The Redis-backed non-eager Celery worker, native tasks, default/DVR queue probes,
provider/API/XMLTV assertions, network-none isolation and socket denial are unchanged.

Only the test payload pin is advanced in the detached transport. Runner bytes,
120-second stabilization, one final capacity decision, 240-second application
watchdog, 1,200-second transport deadline and protected installed mappings remain
unchanged. Source files and hashes are in `overnight-offline-results.json`.

## Offline evidence

All 677 distinct regressions pass: existing 674 plus three plugin fixture tests.
The tests execute the exact pinned upstream AppConfig using synthetic Django
modules, reproduce startup wiring without the opt-out and verify its suppression
with the opt-out. The vendored fixture matches upstream Git blob
`2257ebe8ee9d8b607121cffbb0196e9203ec3476`.
Existing UID1000, namespaces, guard/relay, registration, admission, transport,
credential, DNS/TLS and socket-denial regressions pass.

## Runtime campaign

Attempt 1 is justified by this demonstrated, narrowly corrected fixture scheduling
side effect. It requires fresh source/host/image/production checks, independent
payload verification and proven cleanup from the preceding attempt. No attempt
has yet been launched in this report revision. Every previous receipt is preserved.

Until actual runtime evidence is recorded, application acceptance and image
binding remain **NO-GO**.
