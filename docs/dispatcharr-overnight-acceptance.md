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

### Attempt 1 — fixture reconciliation error; clean failure

ID: `overnight1-20261118-3d8ef59a`; payload SHA-256:
`92a1a1165748362dc81ae8dadd1508da1a23c91fbacaefdbef3f72a5357f9235`.
The plugin opt-out passed all runtime checks. PostgreSQL 17, authenticated Redis,
UID1000 Django 6.0.9, 184 migrations, 57 registered Celery tasks and two actual
Redis-backed task results completed. Four application tests passed; the fifth
raised an error in its account-tag collection lookup (runtime_test.py:330).
There was no socket refusal. Native import/XMLTV/backend final acceptance did not run.
Transport reported failed with cleanup_complete=true; all 33 production container,
network and volume fingerprints and previous receipt hashes remained unchanged.
Full sanitized admission measurements/checkpoints are in `overnight-attempt-1-results.json`.

The demonstrated test-only defect is a chained dictionary lookup on native nullable
JSON metadata. The pinned M3U model permits `custom_properties=null`; the test
incorrectly assumed dictionaries for every unrelated/default account. The retained
stack ends at that expression; raw response values and the original exception
message were not retained. Offline reproduction confirms the nullable case raises
AttributeError. A strict structured-tag selector now excludes untagged/malformed
metadata while retaining exact-match, duplicate-count, ownership-journal and
no-retry assertions. No native adapter or application behavior changes.

Four focused regressions cover the former exception, exact tag matching, malformed
metadata refusal and duplicate preservation. The harness suite now passes 116
checks; the full distinct offline baseline is 681. Source/payload pins advance
only for these reviewed test changes. Attempt 2 is justified by this demonstrated
fixture defect and requires a new identity, fresh preflight and the confirmed
cleanup above. No second launch has occurred in this report revision.

Application acceptance remains **NO-GO** pending the complete runtime matrix.
