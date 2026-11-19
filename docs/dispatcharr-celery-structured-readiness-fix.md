# Original Dispatcharr — structured Celery readiness candidate

**PASS offline: 221 unit tests and16 isolated permission checks. GO for review of one separately authorized managed restoration attempt, contingent on fresh preflight.** No installation, production contact, Docker/systemd operation, Celery/Django execution or broker connection occurred. Native hardening remains suspended.

This implements only Option A from [the approved review](dispatcharr-celery-readiness-necessity-review.md), `ec6963b4659e987946fd8db8a0fc9b148f2f83ce`. Both required roles remain mandatory. It is not a recovery-only omission policy, and no actual failure cause is inferred from the discarded267-byte response.

## Verified current baseline and rollback

Before editing, the three supplied hashes were verified against local candidate bytes representing the currently installed original diagnostic lifecycle:

| File | Current installed / exact rollback SHA-256 | Proposed SHA-256 |
| --- | --- | --- |
| `backend.py` | `5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b` | `466b06a23af779d0093d2325d6dce3257a354e4d8899658fb849713e2b1a3065` |
| `lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` | **Unchanged; same hash** |
| `manifest.json` | `52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b` | `8c8ea65df72c6ce18238faeb7262c6946b821ad711bdbf9b06174c10b2dc2a5f` |

Exact copies are retained under `configs/dispatcharr-iptv/original-backend-diagnostics/structured-baseline/`, source1f73b94/deployment evidencef7df20f. `structured-baseline-hashes.json` and hard-coded verifier constants fix this baseline. Historical f4298da `installed-baseline/` copies and227122d `original/` copies remain byte-identical and verified. No rollback expectation was regenerated to accept unrelated drift.

Only `backend.py` and `manifest.json` are proposed install targets. The manifest changes only its backend entry relative to the current installed baseline. All65 unchanged targets, including lifecycle, close the67-target inventory. `candidate.patch` compares against `structured-baseline/`; this is a review patch, not an installer.

## Verified supported CLI syntax

```text
celery -A dispatcharr inspect ping --timeout=8 --json
```

The retained, previously pinned Celery5.6.3 `celery/bin/control.py` source has SHA-256 **`c1267b714e2100b4c7f9817833a985f6f4cf704da08485ddaaa33279f54efbdd`**. Its `inspect` implementation receives the JSON-mode flag, sets the callback toNone rather than the human reply formatter, serializes the returned reply mapping, then returns before the human node-count footer. The operation remains the same supported `ping` inspection.

The flag spelling/placement is also corroborated by retained successful original-image `inspect active/reserved/scheduled … --json` invocations from the earlier background preflight, together with their completed sanitized receipt. This was a read of retained source/evidence, **not** a new `celery --help`, worker invocation or application test. [CLI contract evidence](../configs/dispatcharr-iptv/original-backend-diagnostics/celery-json-cli-contract.json) records this provenance and the exact proposed argv. No package/version/image upgrade is involved.

## Structured response contract

The bounded capture result must be complete, the command must exit0 and stderr must be empty. Stdout must parse as **one complete JSON object**, with only standard surrounding whitespace; no extraction from log text, prefix/footer stripping, trailing document, ANSI cleanup or human-format fallback is permitted.

For a pass, the object must contain exactly two unique worker identities: one `default@…` and one `dvr@…`. Hostnames are opaque bounded ASCII hostname tokens, not values retained in diagnostics. The role prefixes are exact/case-sensitive. This checks the returned identity/role contract, not an independent attestation of worker PIDs or hostname authenticity.

Each reply must be exactly the object **`{"ok":"pong"}`**. Extra fields, errors, wrong types/case/content, missing roles, extra workers and duplicated roles fail. A JSON object with one valid role produces the existing fixed missing-role failure; an empty mapping produces the existing missing-roles failure. They never pass on command return0 alone.

Duplicate-key detection applies at every JSON object level **before** dict construction can discard earlier values. Repeated full identities and duplicate nested `ok` keys are rejected. Different identities with the same expected role are rejected as well. Any warning on stderr—including a possible upstream duplicate-node warning—also fails closed. As with any CLI result, information already silently discarded upstream cannot be reconstructed; this parser validates the complete serialized response and refuses extra warnings rather than asserting unobserved uniqueness.

Malformed/truncated JSON, nonfinite constants, wrong top-level types, invalid identities, unexpected/error payloads, multiple documents, mixed logs, oversize or incomplete output produce `celery_unclassified_failure`. For invalid response structure/payload, **no positive role witnesses are retained**; false presence flags then mean no trusted positive proof, not a proven worker outage. Valid one-role responses retain that role's positive proof. Nonzero exit always fails, even with both positive objects.

The previously reviewed fixed CLI error classifications remain for narrowly recognized empty-stdout error cases. Raw JSON, hostnames, credentials, broker URLs, environment values and exception text are never emitted or written to receipts.

## Preserved limits, diagnostics and security

- One inspection subprocess; only `--json` is appended to the reviewed argv. Cwd remains `/app`.
- Reply timeout **8s**, subprocess deadline **40s**, outer backend invocation **90s**. No retries, sleeps, extra probes or startup grace periods were added.
- The existing bounded capture helper is unchanged:16KiB per pipe, saturated observed-byte counters, strict UTF-8 and scoped child termination on overflow/deadline. It does not signal workers or containers.
- PostgreSQL/migration verification, configured Redis/authentication handling, source hashes and exactly two fresh uWSGI witnesses are unchanged. AST comparisons verify every non-Celery stage against the current baseline.
- Lifecycle bytes, managed ordering, guard/VPN/firewall/namespace checks, registration/export rebind, gateway-last and scoped cleanup are unchanged. No native-hardening code or unit is introduced.
- Diagnostic fields/schema are unchanged. `reply_output_valid` now means the reviewed structured mapping contract, and count/presence describe explicit positive pongs from a valid response. Command monotonic start/end/elapsed, actual return code, bounded byte counts, completeness and fixed classifications remain.
- Broker comparison helper is unchanged and still reports **unknown** in the existing runtime path unless authoritative effective-setting snapshots exist. False equality flags with `known=false` are not a mismatch claim. No setting inference, Django import or broker query was added.
- Root-private `/root/dispatcharr-backend-diagnostics`, strict ancestor checks, no-follow/exclusive writes,0600 receipts, same-invocation validation and historical-receipt preservation are unchanged. Record768-byte, host-capture4096-byte and receipt16384-byte bounds remain fixed.

The parser no longer depends on a human reply regex. This removes that representation dependency; it does **not** establish that the prior missing default proof was a parser-only defect or guarantee that a future default reply will be positive.

## Offline regression results

| Suite | Result |
| --- | --- |
| Diagnostic/structured/lifecycle/integrity suite | **138 PASS** |
| Existing admission | **28 PASS** |
| Existing minimal persistence | **12 PASS** |
| Existing owned-record rollback | **26 PASS** |
| Existing security contracts | **17 PASS** |
| Total unit tests | **221 PASS** |
| Existing disposable UID0/UID1000 receipt-permission fixture | **16 checks PASS** |
| Current/historical baseline hashes and full67-target closure | **PASS** |

Fixtures cover both positive roles and JSON ordering/whitespace, missing default/DVR, empty mapping, duplicate identities/roles/nested keys, unexpected workers, error/negative/extra-field payloads, malformed/truncated/multiple/nonfinite JSON, oversize output, return0 with invalid response, nonzero exit with valid pongs, unexpected stderr/warnings, credential/hostname redaction and explicit refusal of legacy human output.

Existing tests retain real **synthetic local Python child-pipe** bounds/deadline tests, timing/counter validation, private receipt integrity, failure cleanup, broker comparison and old baseline preservation. No actual Celery/Django/broker process ran. Capture mocks were updated to model bounded completeness, not optimistically report complete oversize output. No fixture uses or reconstructs the discarded267-byte response.

## Changed source, inventory and evidence files

The following exact hashes cover the candidate, matched manifest/inventory, tests, CLI evidence and new rollback copies. Older evidence remains historical and is not rewritten to pretend it contains this correction.

| Repository file | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/original-backend-diagnostics/README.md` | `e9807dc54171a861ad64e2dae271a01fd57f16296eb5e76708fc2f7ec9a5aef1` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate-inventory.json` | `f154b0abdf524eac2c9ad882220945efbae6d5c97820ac9ebfe087439c8bdcaa` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate.patch` | `4983a79f3886d97e19556a12771e2bf72ed6d9d82ff85274927e2a78f87f1c2f` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/backend.py` | `466b06a23af779d0093d2325d6dce3257a354e4d8899658fb849713e2b1a3065` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/candidate/manifest.json` | `8c8ea65df72c6ce18238faeb7262c6946b821ad711bdbf9b06174c10b2dc2a5f` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/celery-json-cli-contract.json` | `c6dd6adfc29d1a5b986ba919006dc1f743192f9393190cfe84b75b51ccf3aad9` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/structured-baseline-hashes.json` | `711ef496bf8ebcb6da256c14fcee12659b6015350e9180bf8f6122805bf14096` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/structured-baseline/backend.py` | `5d37a1a53a8c4e05d3b699998cd3ae618cb4b79112c9c651ed9711d9175a5e4b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/structured-baseline/lifecycle.py` | `0df62a9448618f63e1e3c9e04f4d36a8a30d804c0f0c8418b4633e4dd07099ac` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/structured-baseline/manifest.json` | `52f8c8e14ecc33fec0b362b1ef32f7d79111ba9d127ee759bc08b939a8f1620b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_celery_correction.py` | `05ca8dff1b1c36c2ddf3873832bcda7675032b4eda607e9e1a303c7c5769d15b` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_diagnostics.py` | `171cd0f1023fe7bdc510b13c1188d8d98c12146477e8a4aa83338d742e5c40f4` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/tests/test_structured_celery.py` | `13e1f710cb28dba68b61da4bb183930cd8e544faaf0b60f9950442c865dd0486` |
| `configs/dispatcharr-iptv/original-backend-diagnostics/verify_candidate.py` | `e7e40480e78a13b6653a904ef8e30db9d2e8c4ade30ba58825b7a0a38c262b5c` |

[Machine-readable results](../configs/dispatcharr-iptv/original-backend-diagnostics/structured-readiness-results.json) include the baseline/candidate hashes, source contract and test counts. This report and that results artifact are not new production inputs.

## Installation and rollback requirements — future authorization only

1. Verify the exact reviewed commit, candidate/rollback hashes and67-target closure. Freshly establish the expected stopped/protected original four-service state, original immutable image, current recovery and independent copy, ownership/receipt consistency, resources and exclusive administration. Stop on drift.
2. Preserve current rollback bytes privately and install **only backend.py and manifest.json**, root:root0644. Verify the65 unchanged targets, especially unchanged lifecycle. Use `structured-baseline/` for this candidate's rollback, not the older f4298da/227122d snapshots. No image, Compose, unit/reload or application-data change is part of this patch.
3. Only with separate authorization issue one existing managed restoration start and monitor its exact invocation. Require both structured positive roles and all security/application/registration/export/gateway gates. Unknown or missing evidence is a refusal, never permission to retry or bypass.
4. On failure, preserve the new private receipt and allow existing scoped cleanup. Any rollback requires separately authorized, conflict-checked stopped/protected state and known ownership outcome. Restoring these two prior diagnostic files does not itself authorize another start, database restore or reset. Preserve all historical receipts.

**Final: GO for review of one separately authorized managed restoration attempt, not installation/start under this task.** Production was not contacted or modified, and no fresh production-health claim is made. Stop here; native hardening, provider activation and playback remain out of scope.
