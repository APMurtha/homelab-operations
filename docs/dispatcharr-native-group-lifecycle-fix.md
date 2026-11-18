# Native group discovery lifecycle fix

**GO for review of a separately authorized corrected image build.** All **704
distinct offline tests pass** (existing 689 plus 15 new lifecycle regressions).
No build, Docker operation, application-runtime attempt or production access occurred.
Image binding and deployment remain **NO-GO** pending a new build and full isolated
Django/PostgreSQL/Redis/Celery/API/Xtream/XMLTV acceptance.

Investigation baseline: `887989307f562878df594e17025f15e46e345d4c`.
The retained image `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`
**does not contain this correction**. No new image ID exists; release-contract.json
keeps aio_image=null. Its original 18 hashes are archived separately in
hardened-image-integration/retained-image-contract.json. The unchanged admission
runner still verifies that retained image against its original hashes.

## Root cause and exact correction

The adapter deliberately creates an inactive XC account and requests explicit
metadata discovery. The view invoked discovery within the authorized discover
job, but the group task queried only active accounts and returned early. The view
ignored that result. The adapter then correctly refused the missing selected group.

The corrected generated task computes whether an inactive-account exception is
permitted **before acquiring its lock**. The exception requires the current
ContextVar job to be discover, established with operator_requested=true, with the
same positive integer account ID and XC resource type. The existing check()
revalidates the root-published authorization lease, allowed operation, current
guard generation, namespace grant and readiness witness. After the exact account
lookup, its current provider key/type and ID are checked again. An identity mismatch
releases the task lock and fails closed.

Only that scoped case omits is_active=True from the lookup. Ordinary group calls,
background operations and refresh contexts retain the active-only predicate.
An inactive ordinary refresh is refused; even an active ambient XC call cannot
retrieve metadata without the existing authorized request context. No account is
activated. Existing DNS, TLS, destination, redirects, deadlines, retries, VPN and
firewall controls are unchanged. This grants no real provider authorization.

The task still executes its real category projection and process_groups logic:
category_id becomes relationship custom_properties.xc_id; ChannelGroup objects
receive native IDs through the normal persistence path. The exact category-to-PK
mapping remains mandatory, and native_selected_group_missing remains unchanged.
No relationship is seeded to make a test pass. Association persistence now has
finally-based renewer/lock cleanup so a partial database failure cannot strand the
managed task lock.

## Discovery results and partial failure

The view validates discovery's return shape before treating account creation with
discovery as successful. A failure returns sanitized structured JSON containing:

- detail: native_discovery_failed_no_retry;
- account_created: true and the newly created native account_id;
- discovery.state: failed and a fixed classification code.

Authorization refusal is HTTP 403 / authorization_refused. Uncaught timeout and
invalid-response exceptions receive fixed timeout/invalid-response classifications
with HTTP 502. Legacy task paths that already converted exceptions into an opaque
failure tuple receive HTTP 502 / discovery_incomplete; the original unsafe error
text is never parsed or exposed. For example, a timeout caught inside the legacy
task is conservatively incomplete rather than falsely claiming its type survived.
Failed/busy/invalid tuple results cannot produce successful discovery responses.

For the new inactive account, the view records status=error and a fixed safe
last_message using an exact-ID, is_active=false update. It never changes is_active,
never targets another account and never deletes data. Previously committed global
groups or partial associations may remain following a later persistence failure;
they must be reconciled by ownership/conflict-checked inspection. No automatic
cleanup, retry, account activation or duplicate POST is introduced. A failure while
persisting the failure status itself remains an uncertain server error requiring
inspection, not permission to repeat creation.

The adapter algorithm and durable journal are unchanged. Any non-success creation
response leaves its write-ahead intent unresolved, blocking another write; its
existing duplicate-provider and ownership checks remain. The API response supplies
a known recovery ID to an API caller, but the present CLI API wrapper deliberately
reduces non-success responses to a safe refusal and does not automatically adopt
that ID. CLI recovery therefore remains read-only/manual reconciliation of the
intent and exact ownership tags. It cannot blindly retry or automatically resume.
The client server-contract hashes advance so the old server cannot be mistaken
for the corrected implementation. Native removal remains disabled.

## Simulator fidelity

The synthetic simulator explicitly models approved discovery, denied/expired
approval, and discovery failure after persistence. Its default approval is a
synthetic fixture witness, not an authorization for live operations. Tests can set
discovery_authorized=false, expire its short fixture lease, or select an allowlisted
safe failure code. Failed discovery returns the same 403/502 structured outcome,
retains the inactive account with error status and creates no successful category
associations. Approved discovery persists category associations without activating
the account. Ordinary refresh of an inactive account remains refused.

The simulator projects selected category metadata; it is not a complete Django ORM
or a substitute for native runtime acceptance. The source-backed tests execute the
full generated task, full process_groups body, generated creation view and pinned
serializer create body over an in-memory ORM facade, with synthetic category
responses and policy/guard witnesses. Success is produced by that actual hardened
logic, not a mocked success return. No Django/Celery application is started.
The previous investigation's historical prefix tests retain their old source
provenance against the archived image contract rather than incorrectly asserting
that old excerpts match the corrected candidate.

## Regression evidence

All 15 new cases pass: inactive creation; explicit inactive discovery; actual
category projection/association persistence; inactive ordinary refresh; missing /
expired approval; revoked guard; wrong account; changed provider identity; task
failure response; partial association failure and lock cleanup; simulator outcomes;
interrupted CLI intent and duplicate prevention with DW fixture preservation;
ambient-operation denial; safe classifications; and retained/candidate image
contract separation. Some cases group related assertions.

The full offline suite passes: tools 147, native hardening 106, permanent streaming
210, persistence 26, guard interface 14, trusted guard design 28, isolated network
fixtures 14, UID1000 permission fixtures 40, runtime harness/admission/transport 116,
and three additional socket fixtures. The audit runner repeats 35 existing tests:
**704 distinct tests / 739 executions**, zero failures. Existing DW preservation,
strict identity, ownership, source pins, TLS/DNS, resource and socket restrictions
remain covered. These are offline synthetic results, not real AirVPN or application
runtime acceptance.

## Source and release integrity

Only these three of fourteen hardened application outputs changed:

| Application output | Previous SHA-256 | Corrected SHA-256 |
| --- | --- | --- |
| `apps/m3u/api_views.py` | `61c9289fa4c6bc9ecc275d39386c6ff0081a551535ce95d44353fe92c51e4e3f` | `6c48c35abc821efbb428a74c832e7c8c018eef472d6f987505169cd83d902936` |
| `apps/m3u/tasks.py` | `4294d180806627da4029af9b955a3c40f5ac13869da23adc25b4bec7293085ac` | `75a6eb9276ec96b0e5de2ae2b1274a63ffe47ef89cc8d6c1620a89e049467fb1` |
| `core/provider_security.py` | `b63d7c4af215d7b135110667c1b37166ddc9b19c3456a4c6703618042d30af16` | `8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004` |

The other eleven outputs, all four inherited readiness files, all eight upstream
input pins, the accepted immutable base image, image packaging modes, VPN/relay/
gateway pins and lifecycle/unit source remain unchanged. The derived in-image
provider_contract_hashes.json follows the same fourteen-output inventory.

prepare.py deterministically generates the corrected overlay. server.patch applies
to the original pinned sources and reproduces all output hashes in regressions.
output-hashes.json, release-contract.json and the CLI server-contract.json advance
together. Candidate verification input pins, minimal verifier EXTRA_PINS, related
artifact/manifests and transition installed-target hashes advance only for changed
source dependencies. No installed target was added, no ownership/mode was relaxed,
and all original rollback-source/hash records remain intact. These are offline
candidate files; no installed verifier, policy or service changed.

Exact old/new SHA-256 values for every changed implementation/test/contract file,
source output comparison, changed target mappings and suite log hashes are in
native-provider-hardening/group-lifecycle-fix-results.json. Historical build receipts
and acceptance reports remain unchanged. The retained runner and transport code
still name the old image and old eighteen source hashes; do not run them expecting
this new candidate. Image/runner binding needs separate review after a corrected
build; no digest was invented here.

## Next authorized boundary

A separate build authorization must verify the unchanged local base and eight
inputs, all fourteen corrected outputs and four readiness files, then build using
the existing corrected COPY-only packaging. Record a new immutable ID and verify
source bytes and UID1000 access. Do not reuse or retag the retained failed image.

Separate isolated runtime acceptance must then verify real Django serialization,
PostgreSQL migrations, Redis-backed non-eager Celery execution, inactive explicit
discovery, group ID readback, partial failure/receipt recovery, selected-channel
import, XMLTV/EPG mapping and DW English/backend compatibility. Retain sanitized
discovery outcome and stable-ID presence evidence. Preserve the approved detached
transport, image verification, admission/stabilization, network-none limits, socket
audit, cleanup and production fingerprints. No runtime authorization is implied.

Rollback remains a source/image candidate rollback under the separately reviewed
managed transition. There is no production rollback to perform now. A future
installation must stop on pending provider jobs or uncertain API mutations and
must reconcile owned records before restoring an earlier image. Never delete
partial resources or clear intent receipts simply to permit another attempt.

**GO for separately authorized build review only; stop after offline publication.**
