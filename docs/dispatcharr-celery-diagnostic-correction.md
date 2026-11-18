# Original-stack Celery diagnostic correction

**PASS offline: 190 unit tests plus16 isolated filesystem checks. GO for review of one separately authorized diagnostic restoration attempt, subject to fresh preflight.** Nothing was installed or executed on Rivendell. No Docker/systemd operation, application execution, broker connection, provider request or production change occurred. This candidate does not fix or assume the cause of the previous Celery failure.

## Exact baseline and change scope

Source evidence is [the investigation](dispatcharr-celery-readiness-investigation.md), commit `387f2197aec34de82bd01ed8e016baa94b430f4c`. The implementation starts from the diagnostic-instrumented original lifecycle installed at `f4298da612300a9024ac8302c8db1252d8d69fc6`, not the native-hardening lifecycle. Before editing, all three supplied SHA-256 values were verified and exact copies retained under `configs/dispatcharr-iptv/original-backend-diagnostics/installed-baseline/`:

| File | Installed baseline / rollback SHA-256 | Proposed SHA-256 |
| --- | --- | --- |
| `backend.py` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` | `5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b` |
| `lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` | **Unchanged, same hash** |
| `manifest.json` | `07faa8cce4c643c0a580787b2514c955ddbc4cd0cbff77b61209de9dd97815a4` | `52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b` |

Only **backend.py and manifest.json** are future installation targets. The manifest changes only its backend entry relative to the installed diagnostic baseline. The inventory represents65 unchanged and2 replacement targets, with exact 67-target closure. All older227122d source originals also remain untouched under `original/`.

`installed-baseline-hashes.json` and hard-coded verifier constants prevent replacing rollback expectations with regenerated values. The verifier checks exact baseline copies, unchanged lifecycle bytes, exact candidate/rollback source paths, manifest scope, historical baseline integrity and all unrelated frozen input hashes. `candidate.patch` now reviews the delta from the **installed diagnostic baseline**, rather than repeating the original instrumentation patch. No active production manifest, image pin, Compose file, guard source or unit was edited.

## Failure classification

Only the reviewed Celery5.6.3 control/CLI error paths are recognized. Source hashes are retained in [machine-readable evidence](../configs/dispatcharr-iptv/original-backend-diagnostics/celery-correction-results.json); the implementation uses those previously inspected source contracts without contacting Rivendell again.

| Classification | Required evidence |
| --- | --- |
| `celery_no_replies` | Return69, empty stdout, exact newline-terminated Click no-node-reply error. |
| `celery_broker_connection_failed` | Return69, empty stdout, exact reviewed broker-operational-error prefix plus a nonempty single-line reason. The reason is never exported. |
| `celery_remote_command_failed` | Return69, empty stdout, exact reviewed remote-inspection-error prefix plus a nonempty single-line reason. The reason is never exported. |
| `celery_usage_or_import_failed` | Return2, empty stdout, exact reviewed missing-Dispatcharr-module error, including its leading newline; optional exact Click usage/help envelope. Other import tracebacks/usage variants remain unknown. |
| `celery_unclassified_failure` | Bare/ambiguous69, unexpected code/text, mixed signatures, unknown output, terminal controls, malformed UTF-8, missing newline, truncation marker or incomplete/oversized capture. |

The coarse `celery_command_failed` code is replaced by these classifications; historical receipts are not reinterpreted. The existing role-specific codes remain for a well-formed return0 reply set missing default/DVR or containing an incorrect reply count. Existing common failures such as subprocess timeout or launch/file errors also remain distinct. No classification changes a failing readiness predicate into success.

Matching is deliberately narrow. ANSI/control sequences and unrecognized preambles are not stripped into acceptance. Multiple error lines, recognized error prefixes embedded in another reason, explicit truncation markers and incomplete records remain unknown. Only fixed codes, booleans, bounded counts and numbers reach diagnostics; raw replies, hostnames, CLI arguments, exception text, URLs and credentials do not.

## Capture and precise timing

The same **single** Celery argv, cwd `/app` and40-second subprocess bound are retained. A bounded pipe reader replaces the unbounded internal `subprocess.run` buffers for this command only. It launches one inspection process, reads both pipes without deadlock, caps each retained byte buffer at16384 and saturates each observed-byte counter at16385. On overflow or the existing deadline, it terminates only its own inspection subprocess; it never signals workers or containers. Output is strict UTF-8. Unknown/truncated capture cannot authorize readiness.

This is bounded evidence capture, not a startup retry or new health grace period. The probe still specifies `--timeout=8`; the outer backend invocation remains90 seconds. There are no added sleeps or retries. Process termination is followed only by bounded child reaping, not another command invocation.

The Celery terminal record now retains:

- `command_start_s`, `command_end_s`: six-decimal absolute `time.monotonic()` values around the one capture call.
- `command_elapsed_s`: their measured duration, with strict finite/order/consistency validation. These measure the local command/capture boundary, **not Redis publication time or remote worker processing time**.
- Actual process `returncode` when available, `stdout_bytes` / `stderr_bytes`, and `output_complete`. Counters describe observed bytes, saturated on overflow, not unobserved output after termination.
- Original parsed count and default/DVR-presence booleans, plus `reply_output_valid` for the reviewed human reply formatter/footer. A successful return code with unknown logs/error text or malformed formatting is conservatively refused as incomplete diagnostic evidence.
- Fixed broker-comparison booleans described below.

Launch failure/timeout can retain only metrics actually available; no return code or output count is invented. Existing diagnostic stage ordering and same-invocation start/pass/fail pairing remain strict. The768-byte record limit,4096-byte host capture,16384-byte private receipt limit, root-private receipt path and all ownership/no-follow/exclusive-write protections remain unchanged. Schema validation rejects unknown fields, invalid booleans, nonfinite/inconsistent clocks, impossible role counts and contradictory success/failure evidence. Historical receipts are never read to authorize a new invocation and are not rewritten into the new schema.

## Broker comparison: exact limits

The reviewed entrypoint writes a selected login environment, uWSGI launches the workers, and the inspection inherits a Docker-exec environment overlaid with that profile. Missing variables are not proof of different effective broker configuration. Loading Django solely to resolve settings can introduce application side effects; `/proc` environments alone are not authoritative post-initialization Celery configuration.

The pure `compare_brokers()` helper therefore accepts only **already-resolved, authoritative effective snapshots** for all three contexts: `inspection`, `default`, `dvr`. It performs no imports of application code, filesystem/process scans, environment inference, DNS, URL requests or broker I/O. It compares privately:

- Endpoint: normalized literal host and port. DNS aliases are not resolved or assumed equivalent.
- Transport: Redis/rediss and reviewed TLS identity/verification fields. Incomplete TLS information or disabled verification makes the comparison unknown.
- Authentication: exact supplied effective username/password strings, including explicit empty strings for an attested no-auth configuration. No password/hash/URL is serialized.
- Namespace: Redis database, control exchange, global key prefix, fanout-prefix and fanout-pattern settings.

It returns only `broker_comparison_known`, `broker_endpoint_equal`, `broker_transport_equal`, `broker_auth_equal`, `broker_namespace_equal`. Equality means both worker snapshots agree with inspection. A known false equality flag proves only a difference in those supplied settings, **not the cause of a runtime failure**. Missing, malformed, unsupported, ambiguous or partial snapshots produce `known=false` and all equality flags false; this means **unknown**, not a proven mismatch.

**Runtime limitation:** the unchanged original lifecycle provides no authoritative effective-worker snapshots. The current backend therefore calls the helper without snapshots and explicitly records unknown. No runtime snapshot acquisition/import mechanism was invented. Synthetic tests prove comparison behavior; they do not attest production equality. This candidate can identify a broker-error versus no-reply CLI branch, but cannot by itself prove or exclude an invocation-environment mismatch. Any later effective-setting observation needs separate reviewed authorization and must remain private/boolean-only.

## Preserved readiness and security

Application-source pin verification, PostgreSQL query/fingerprint, configured Redis readiness, exactly two fresh Redis-backed uWSGI witnesses, and the exact default/DVR reply predicate remain unchanged. AST-projection tests recover the original readiness check after removing diagnostic scaffolding and projecting the bounded capture call onto the identical original invocation. Tests additionally assert exact argv/cwd/deadlines and that a failed child exit cannot pass even with plausible replies.

Malformed/oversized/unknown successful-command output is an additional **fail-closed diagnostic refusal**, never a relaxation of readiness. The strict formatter check retains known role-specific failures. Guard/VPN checks, lifecycle prepare/start/stop/rollback ordering, scoped failure cleanup, gateway-last and registration behavior are unchanged; lifecycle bytes match production exactly. Native hardening, policies, providers, Jellyfin and unrelated services are untouched.

## Offline validation

| Suite | Result |
| --- | --- |
| Diagnostic schema/backend/lifecycle/integrity tests, including38 new focused cases | **107 PASS** |
| Existing boot-admission tests | **28 PASS** |
| Existing minimal-persistence tests | **12 PASS** |
| Existing owned-record rollback tests | **26 PASS** |
| Existing permanent security-contract tests | **17 PASS** |
| Total unit tests | **190 PASS** |
| Existing disposable UID0/UID1000 namespace/chroot permission fixture | **16 checks PASS** |
| Candidate/rollback integrity and67-target manifest closure | **PASS** |

Synthetic coverage includes valid/default/DVR replies, all five new classifications, ambiguous69, stderr credential/URL redaction, unknown successful output, malformed/truncated/oversized output, actual bounded local Python child pipes and deadline interruption, byte-count saturation, precise/invalid timing, match/mismatch/unknown comparisons, TLS identity handling, role/schema contradictions, same-invocation receipt retention, baseline-copy hashes and refusal to substitute the older227122d rollback inventory. The existing69 diagnostic tests remain, updated only for the extended schema and capture seam. No Celery, Django or broker process was run; local child fixtures execute only synthetic Python output/sleep behavior.

## Changed-file inventory

Hashes below cover implementation, tests, rollback copies, inventory and review artifacts. The report/results file are evidence artifacts and do not enter the production manifest.

| Repository file | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/original-backend-diagnostics/README.md` | `39c7784e3ca5d4952c82239bfae3531ab5ebfff41b19b1c80415d730ecffbd0b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate-inventory.json` | `17692690075a71edc0da8abf87c7319ef427d4ddf436480fe4d77b0b290f3b0c` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate.patch` | `f13bee83f9d3a66ca7368d7ab44a07c6f7c3a105c3f577c8fe31093284470bdf` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/backend.py` | `5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/manifest.json` | `52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/installed-baseline-hashes.json` | `f2db6ece950f673a6981aa4c985800b7cac33b36c4ce82d96b94f5f0fed649f3` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/installed-baseline/backend.py` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/installed-baseline/lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/installed-baseline/manifest.json` | `07faa8cce4c643c0a580787b2514c955ddbc4cd0cbff77b61209de9dd97815a4` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_celery_correction.py` | `250f8b8c3bc30b8ab4927190f44f240359c3ee584dc3934fd242848d29e75875` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_diagnostics.py` | `6cc86c8b42bb056ec54ee089b389e841f2b4117cd87e9792ab7bc47465a2f297` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py` | `3818323248b2401e602e01a640ed62ddbffcb0ca0c7af013669864d705a3ddf8` |

## Future installation and rollback requirements

**Do not execute this plan under the current authorization.** Before a separately authorized attempt:

1. Verify the exact reviewed commit, both source baselines, candidate inventory and all67 current installed target hashes. Expect the three installed diagnostic hashes in the first table, with lifecycle unchanged. Stop on drift.
2. Freshly verify the original stopped/identifiable four-service stack, original immutable image, recovery/independent checkpoint, private receipt permissions, ownership transactions, resource admission and exclusive administration. Preserve existing kernel protection, withdrawn guard/grant assertions and revoked provider authorization.
3. Preserve exact current rollback bytes privately. Install only proposed `backend.py` and `manifest.json` as root:root0644, using the matched inventory. Verify all65 unchanged files, both replacements and manifest closure. Do not install native sources, Compose/unit changes or a new image. The unchanged lifecycle dynamically imports the schema from that same backend file; no new runtime module/mount is needed.
4. Preserve all historical root-private receipts. Only under explicit authorization issue one existing managed start and retain the new invocation's diagnostics. Unknown comparison/classification is not permission to bypass readiness or retry. Allow unchanged scoped failure cleanup.
5. After failure or installation refusal, stop. If separately authorized and the stack is stopped/protected with known transaction state, restore only those two files from `installed-baseline/`, verify all67 matched installed-baseline targets, and leave stopped unless another start is explicitly authorized. Do not use the older227122d backend/manifest as this patch's rollback. Lifecycle has no rollback delta. No database restore/reset is part of this procedure.

## Decision and production status

**GO for review of one separately authorized diagnostic restoration attempt**, contingent on fresh preflight and acceptance of the explicit unknown broker-comparison boundary. This is not GO for claiming recovery, changing timeouts/broker configuration, starting now or resuming hardening. No live health assertion is made: Rivendell was not contacted in this offline task; its last observed protected/stopped state remains the prior incident evidence.

The next diagnostic result can distinguish the narrowly recognized CLI failure branches while preserving safe unknowns. It does not guarantee a functional fix or an effective-environment comparison. Installation, any runtime observation and a managed restoration start all await separate authorization.
