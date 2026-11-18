# Original Dispatcharr backend readiness diagnostics patch

**PASS offline. GO for separate review/authorization to install this diagnostic-only delta and perform one managed restoration attempt. No installation, production access, Docker operation or recovery attempt occurred.** Hardening deployment remains suspended. Last observed production state is the stopped original stack recorded in `7c3f1fe`; it was not re-inspected in this offline task.

## Baseline and exact delta

Diagnosis: `7c3f1fedee413245046cf6fb8271329a3ac34166`, [original-stack diagnosis](dispatcharr-original-stack-recovery-diagnosis.md). Before editing, all three owner-approved original hashes were verified against bytes from `227122dcbe9ebc76be46b8a91231350d6c93bdb4`. Those exact rollback copies are retained under `configs/dispatcharr-iptv/original-backend-diagnostics/original/`. They are not copied from the newer native-hardening lifecycle in this branch.

Candidate: `configs/dispatcharr-iptv/original-backend-diagnostics/`. It replaces only the two diagnostic-instrumented sources and their original permanent manifest:

| File | Original SHA-256 | Candidate SHA-256 |
| --- | --- | --- |
| `backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` |
| `lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` | `171530848e5623b3ab3a578798c83d3991b1299798202f544fc70fd92a26bc8f` |
| `manifest.json` | `9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c` | `1eb1a2b68e564b56cc105b31eb6281b610cf0e1f3684fea9246fd02eaabcc8f5` |

Targets are `/docker/dispatcharr-iptv/permanent-streaming/{backend.py,lifecycle.py,manifest.json}`, all root:root 0644. The candidate manifest changes only its backend/lifecycle entries; all other entries remain equal to the original manifest. `candidate-inventory.json` also fixes the 64 unchanged installed-target hashes and retains the exact three rollback copies. The installed-file count remains 67. Every HERE-relative manifest input is represented by these 67 targets; no additional executable/module/source mount is required.

`verify_candidate.py` hard-codes the three authorized baseline hashes and source commit, verifies the originals/candidate inventory, detects unrelated tracked-input drift, and checks exact target/permission/manifest closure. It refuses mutated expected baseline pins. `candidate.patch` is a review diff, not an automatic installer. Neither the installed production manifest nor the branch's existing permanent/native source files were changed.

## Preserved readiness behavior

The original `check()` body remains in its original order, with diagnostic contexts and metric-emission statements around it:

1. Verify the same 14 application source hashes from the existing pin file.
2. Use the same read-only PostgreSQL query and require `184:b00f51e91c5b882cd84d3b2579d074ca`. Preserve psql options, 15-second process deadline, 10-second statement timeout and 3-second lock timeout.
3. Use the same configured Redis authentication, 3-second connection/read bounds and PING.
4. Preserve the exact current-PID/`uwsgi`/age0–<30s/positive-TTL logic and requirement for exactly two fresh witnesses. Malformed witness handling and excess-count predicate are unchanged.
5. Preserve the exact default/DVR `inspect ping --timeout=8`, 40-second subprocess deadline, return-code test, reply regex, two-node count and role-set test.

No retry, sleep, extra health grace period, timeout increase or relaxed predicate was added. An AST projection test removes only diagnostic contexts/statements and obtains the exact original check-function AST. The original main generic exit message is unchanged; original exception/failure behavior remains nonzero. Unexpected failures remain fail-closed.

The original lifecycle's `trusted`, generic `execute`, `prepare`, `start`, `stop` and `rollback_integration` function ASTs are unchanged. Only the existing environment-loaded backend invocation is dispatched to the bounded diagnostic capture helper, retaining the same command, UID/GID1000 and 90-second outer bound. Registration and binding invocations retain their original execution path; gateway-last and scoped cleanup are unchanged. No native provider-policy hook or `--native` path was introduced.

## Record schema and safe classifications

Backend records are newline-framed on stderr, prefixed `DISPATCHARR_BACKEND_DIAG `. JSON keys are restricted to:

```json
{"stage":"celery","event":"fail","elapsed_s":9.25,"classification":"celery_dvr_missing","count":1,"returncode":0,"default_present":true,"dvr_present":false}
```

This example is synthetic. Required fields are `stage`, `event`, `elapsed_s`, `classification`. Stage identifiers are fixed: `api_sources`, `postgres`, `redis`, `uwsgi`, `celery`. Events are `start`, `pass`, `fail`. Start/pass classifications are `checking`/`ready`. Optional fields are stage-specific: `count` for source/witness/Celery stages, `returncode` for PostgreSQL/Celery, and the two role booleans for Celery. No PID, address, credential, environment value, provider URL, raw command response or exception message is a record field.

Known failures map to fixed codes:

| Stage | Specific codes |
| --- | --- |
| API sources | `source_hash_mismatch` |
| PostgreSQL | `postgres_command_failed`, `migration_mismatch` |
| Redis | `redis_ping_failed`, `redis_authentication_failed`, `redis_connection_failed`, `redis_timeout` |
| uWSGI | `worker_count_exceeded`, `fresh_workers_missing`; Redis read failures retain their safe Redis class |
| Celery | `celery_command_failed`, `celery_roles_missing`, `celery_default_missing`, `celery_dvr_missing`, `celery_reply_count` |

Common safe codes are `file_missing`, `file_permission`, `invalid_manifest`, `dependency_unavailable`, `subprocess_timeout`, `unexpected_exception`. Classification compares known internal errors without serializing their arguments; unexpected exception text is never printed. Counts describe the configured source inventory, fresh witnesses or parsed reply count; no individual keys, file paths or node hostnames are emitted.

Every stage emits start, then exactly one pass or fail. Pass is emitted only after its unchanged predicates succeed. A failure record is emitted from the same exception that still propagates to the original generic exit. Signals/crashes before a failure record remain incomplete evidence, not success.

## Bounded validation and invocation isolation

The host imports only the schema definitions from the exact candidate backend path; importing that module does not run its checks. The child still executes the original environment-loaded backend command once. Each capture uses fresh pipes and a fresh local invocation identifier; no historical result file is read, merged or reused to authorize progress.

The strict parser requires stage order and start/terminal pairing, monotonic finite elapsed values, exact fields/types, allowed classifications and consistent failure metrics. It rejects duplicate JSON fields, nonfinite numbers, unknown fields/stages/codes, wrong role types, impossible pass counts/return codes, duplicate sequences, output after a terminal record and truncated records. Backend elapsed values are bounded by the existing 90-second invocation budget. A successful child exit alone is insufficient: all five complete stage pairs and successful evidence retention are required.

Bounds:

- At most 768 bytes per framed line.
- At most 4096 bytes of combined child stdout/stderr input; bounded 4096-byte reads prevent unbounded buffering.
- At most ten validated records; no raw output is retained.
- At most 16384 bytes per receipt.
- Original 90-second client deadline; timeout/output/protocol refusal kills the client as needed and propagates nonzero into existing managed cleanup. No protected container is manually restarted or retried.

Unsolicited stdout, raw traceback/error text or malformed stderr is rejected, not forwarded. The original fixed generic backend error line is recognized privately but is not substituted for a valid stage sequence. Host results distinguish `before_first_diagnostic` from `inside_readiness`. A failed launch, missing initial record, interrupted sequence, inconsistent process exit, capture error or evidence-write error is an explicit gap/refusal. A failed stage's exact validated stage/classification remains retained when available.

Only validated bounded records and fixed gap messages may reach the unit journal. Raw subprocess stdout/stderr and exception text never do.

## Private, durable receipts

The existing root-managed lifecycle will use only:

`/docker/dispatcharr-iptv/private/backend-diagnostics`

It validates the root-owned, non-writable, non-symlink ancestor chain and existing root:root 0700 private parent, then creates or validates a root:root 0700 receipt directory. It does not chmod an insecure existing directory into acceptance. New files are root:root 0600, regular and single-link, opened no-follow/exclusive. Names are restricted to a fresh 32-hex invocation identifier and `.intent.json`/`.result.json`; traversal and overwrite are rejected. A held directory FD and current-path inode comparison detect directory replacement.

A new receipt-directory entry is fsynced through its existing private parent. The intent is flushed/fsynced before launching the single backend process. The final sanitized result is flushed/fsynced before accepting it. All historical files remain untouched. File/directory collision, symlink, hardlink, wrong owner/mode, replaced anchor, size or persistence failure causes a fixed evidence-gap message and nonzero failure, retaining whatever private intent/evidence exists. No raw diagnostics are put in a temporary public file.

These are diagnostic receipts, **not an authorization or independent health latch**. An intent without a successfully retained result, or a file whose write/fsync failed, is not proof of backend acceptance. Service acceptance additionally requires the current managed invocation to return successfully and complete its original downstream gates. No old receipt can make a new attempt healthy.

## Offline evidence

**69 new unit tests, 236 existing offline regressions and 13 isolated filesystem checks passed; zero failures/errors/skips.** No Docker, production systemd, real Django/Celery runtime, provider or external request was used.

New tests cover all five success/failure stages; source/migration mismatch; Redis authentication/connection/timeout; missing/stale/expired/future/malformed heartbeats; excess workers; missing default/DVR/duplicate Celery replies; command failure/deadlines; unexpected errors; generic original exits; launch/no-initial-record failure; same-invocation retention; partial, duplicated, malformed, nonfinite or invalid-UTF8 output; per-line/combined limits; schema/field/type/metric inconsistencies; dummy credential/environment redaction; incomplete evidence; directory/result persistence failures; unchanged critical lifecycle ASTs; exact original hashes and complete manifest closure.

The permission fixture uses a disposable user/network namespace and chroot with synthetic data, not production paths. It demonstrates actual root-owned 0700/0600 receipt metadata, UID1000 traversal/read denial, collision preservation, symlink/hardlink refusal, current-path replacement refusal, bad directory mode/ownership refusal and path-traversal rejection. The isolated network has no external access. No packages or services were installed.

Existing checks: 210 permanent-streaming security/lifecycle/unit/guard/boot-admission/isolated gateway/network checks, plus 26 original persistence checks. The existing pinned Caddy fixture was reused; no image was built/pulled. Source inputs elsewhere in the tracked Dispatcharr tree remain byte-identical.

Reproduction from repository root:

```sh
python3 -B configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py
python3 -B -m unittest discover -s configs/dispatcharr-iptv/original-backend-diagnostics/tests -v
sh configs/dispatcharr-iptv/original-backend-diagnostics/tests/run-permissions.sh
```

The permission runner requires existing namespace/subuid support. Results and log hashes are in `offline-results.json`; complete source/artifact hashes are in `artifact-hashes.json`.

## Installation, rollback and one-attempt requirements

**Not executed by this task.** Separate authorization must cover installing this exact diagnostic candidate and one managed original-stack restoration attempt. Before installation, verify fresh host/account/exclusive-administration and stopped/protected state, current recovery/Denethor copy, full root-owned/non-writable receipt-path ancestry, all 67 original target hashes including the three exact old inputs, ownership/registration certainty, unchanged image 14c, unit ordering and resource capacity. Any unexpected drift stops installation; do not regenerate pins or loosen permissions.

Install only the three mapped candidate files as root:root 0644 from `candidate-inventory.json`, and verify their SHA-256 plus all 64 unchanged hashes. Retain the exact three original rollback files. The diagnostic receipt directory is created/validated under the existing private parent by the lifecycle helper; an invalid/unwritable path fails closed. No Compose, unit/drop-in, image, namespace/mount, guard, firewall, VPN, DNS, registration, provider-security or Jellyfin change is included. No daemon reload, container recreation or database restore is required by this source-only delta.

A future authorized start must use exactly the existing managed entrypoint once:

```sh
# SEPARATE AUTHORIZATION REQUIRED — NOT RUN HERE
sudo systemctl start dispatcharr-stack.service
```

Monitor that same unit and new sanitized receipt; do not relaunch. The original guard/admission/VPN/grant/backend/owned-rebind/export/gateway order and scoped failure cleanup remain. Normal owned DW endpoint rebind/export renewal belongs to that future managed-start authorization; no provider policy, media retrieval or playback is implied. Success requires the complete original application/security acceptance, not merely diagnostic completion. Failure or evidence gap stops the attempt and preserves receipts; no automatic retry/reset/restore.

Removing this instrumentation later requires an authorized source rollback with conflict checks: current three files must match this candidate, then restore the three exact original bytes/root ownership/modes and verify the original manifest. Preserve all diagnostic receipts. Do not force overwrite newer changes or perform a runtime restart simply to remove logging. No database or unrelated state rollback is part of this patch.

## Exact artifact inventory

Paths below are relative to `configs/dispatcharr-iptv/original-backend-diagnostics/`. The hash inventory and this report exclude their own bytes to avoid circular hashes.

| Artifact | SHA-256 |
| --- | --- |
| `README.md` | `93211cad22030f88327d9abd17907c21d533677d10c3208e44ca5b9cfb65d7b0` |
| `candidate/backend.py` | `c3b52ec9ca05909375c531389376653c6f9e77051fa4ca4922a6d145235710f8` |
| `candidate/lifecycle.py` | `171530848e5623b3ab3a578798c83d3991b1299798202f544fc70fd92a26bc8f` |
| `candidate/manifest.json` | `1eb1a2b68e564b56cc105b31eb6281b610cf0e1f3684fea9246fd02eaabcc8f5` |
| `candidate-inventory.json` | `4cf27e5ad65bd1b81be72bbbe99c1b46209adf4add600646cdcfd65b026e302e` |
| `candidate.patch` | `a3fa38e37fc465c0f6f4d65a4864baac9c93c55bcdc8b4d6f9ed5b338be22d57` |
| `offline-results.json` | `0398b1d0470a1dd91f0336a7f11a7cd34dc37b9abee211b92136431ac17f5861` |
| `original/backend.py` | `651c7f5952667ac0bda3e21e1e1edb73963aea16b38c9ceca8501182ae774dbf` |
| `original/lifecycle.py` | `9dbe2ec2cfb41b847cffc5cff487e558c16f56d5d992474670989c387d286779` |
| `original/manifest.json` | `9014af51977ae95a33ea5a380480196da8352af6043bde6126c9b39a4c8f781c` |
| `original-hashes.json` | `5e3558daa34afd58633673c22ac53127107d02ea85f1ab75969fc28fef9adca2` |
| `tests/permission_fixture.py` | `7e12cd7324097c0a35522b331f6f28c204f62e229d02d14d54b6abb68f6f4811` |
| `tests/run-permissions.sh` | `89aa5a9c6e69d198f10fbd5925f26a070820dd0ab8443ad3a14b1a9317fe5d2a` |
| `tests/test_diagnostics.py` | `6b18e41e8dc4850d385fd9adfb9e4740838c5616c57fedf748ddc55825c1a4ba` |
| `verify_candidate.py` | `1764bc1adf3307e86607f77db059a2181acede33296533eebaae7bdbdfe6279a` |

## Decision and limits

**GO for separately authorized diagnostic-candidate installation and one controlled original-stack restoration attempt**, conditional on fresh prerequisite verification. This is not a GO for native hardening, provider activation, playback or a blind uninstrumented retry.

The patch makes the next failure observable; it does not establish the previous cause or fix an assumed Celery race. Synthetic tests and real isolated filesystem semantics do not prove actual production startup or storage durability. No production receipt directory or diagnostic patch was installed, and no containers/services were operated. Stop after publication and await separate authorization.
