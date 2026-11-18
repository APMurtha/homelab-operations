# Native Dispatcharr group resolution investigation

**Root cause: a native discovery lifecycle contract defect, not a mismatched
synthetic category ID. NO-GO for another runtime attempt or image binding until
the application/adapter contract is corrected under separate authorization.**
No application, adapter, runtime fixture, image or protected configuration changed.

Baseline: `a038444b4bd700e3c437fa9ec62f7624fc968ce0`.
Failed attempt: `overnight2-20261118-dd0c87d8`.
Retained image: `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.

## Verified source and trace

The local adapter and runtime fixture hashes match the actual attempt payload.
The locally retained hardened task, view, signal and Xtream-client files match the
approved `release-contract.json` outputs. The upstream M3U model/serializer and
channel association serializer match `api-contract.json` pins. No image operation
was used to inspect them. Exact source excerpts, line ranges and SHA-256 provenance
are retained in `tools/tests/fixtures/native-group-source-evidence.json`.

1. **Fixture identity:** runtime_test.py's in-memory provider handler returns
   category IDs `"1"` / `"2"`, named Fixture News / Fixture Other. Its selected
   stream is `"101"` with group `"1"`. The direct handler test and AST extraction
   of test_06's selection confirm identical IDs and types. There is no category
   name/ID mismatch to repair.
2. **Adapter account creation:** native.py:265–279 sends `is_active=False`,
   `metadata_discovery=True` and all automatic group-sync options false. The
   serializer persists the inactive account; it does not import group associations
   during creation. The hardened save signal skips automatic XC group refresh.
3. **Creation view:** apps/m3u/api_views.py creates/serializes the account first,
   then enters the explicit `job("discover", account, True)` context and calls
   `refresh_m3u_groups(account_id)` synchronously. The security context permits
   explicit discovery of an inactive account; its active-account predicate applies
   to refresh/EPG operations. Existing authorization remains required.
4. **Actual discovery gate:** apps/m3u/tasks.py:1703–1716 obtains its task lock,
   starts the renewer and queries
   `M3UAccount.objects.select_related("user_agent").get(id=account_id, is_active=True)`.
   The newly created inactive account cannot match. The task stops its renewer,
   releases its lock and returns `(not-found-or-inactive message, None)`.
   This occurs before client construction, authentication, category retrieval or
   `process_groups`. The view ignores the return value and still returns its
   successful account-creation response.
5. **Association path, if reached:** the later category loop reads each
   `category_id` into `groups[category_name]["xc_id"]`. `process_groups` resolves
   native ChannelGroup objects, then creates/updates account-specific
   ChannelGroupM3UAccount relations carrying that `xc_id` and the native group PK.
   Automatic enabling follows the account preference, false here. This path is
   unreachable for the adapter's inactive new account.
6. **Readback/parsing:** Ledger.mutate performs a fresh authenticated detail lookup
   and verifies persisted expected fields, including `is_active=False`, before
   returning the account. Thus the stale POST response is not the explanation.
   Adapter.register maps each relation's `custom_properties.xc_id` to its native
   `channel_group` PK, rejects duplicates, and requires the selected stable group
   set to be a subset. At native.py:289 it raises
   `Refused('native_selected_group_missing')` before any group-settings mutation.

The mismatch is between **inactive account creation with explicit discovery** and
an **active-only discovery task query**. The missing group is a downstream symptom;
the strict group-identity refusal is correct. Merely changing fixture IDs, seeding
relations, enabling the account prematurely or ignoring the assertion would hide
this genuine integration defect.

## Offline reproduction

Eight focused tests pass. The reproduction executes the exact approved create-view
method and the task's complete pre-category prefix with synthetic in-memory ORM,
lock/renewer and job-context stubs. It also runs the unchanged real Python
Adapter, API and durable Ledger against that source-backed synthetic path.
It does not initialize Django/Celery, contact a server, open a socket or provide a
real guard/VPN authorization. The task excerpt intentionally ends before category
processing; the active-account control proves only passage through the early query.

| Reproduction | Observed result |
| --- | --- |
| Exact fixture handler and selected literal | Category `"1"` equals selected group `"1"` |
| Inactive task lookup | Exact not-found/inactive return; lock released; no category stage |
| Active control | Passes the early query; no claim of full discovery success |
| Exact creation-view method | Returns 201 despite discovery's inactive-account return |
| metadata_discovery=false | No discovery/job invocation |
| Unchanged adapter over source-backed path | Same `native_selected_group_missing` refusal after detail readback |
| Journal/side effects | One account POST; verified account operation; phase remains registering; no downstream writes |
| Ownership and preservation | Returned synthetic native ID used, no invented association; DW fixture unchanged |

The existing `dispatcharr_provider.synthetic.Synthetic` simulator supplies groups
whenever metadata_discovery=true, even for inactive accounts. An explicit comparison
test demonstrates that optimistic assumption. It explains why older mock-only
registration tests passed while the real application path failed. This is a mock
fidelity gap **in addition to the native lifecycle defect**. The simulator and its
existing positive tests remain unchanged; replacing the real fixture with that
optimistic behavior would conceal the defect.

## Evidence limits

The retained runtime traceback ends at Adapter.register:289. The original account
detail/category response bodies, new account ID and group PKs were not retained;
this investigation does not reconstruct or claim those values. The empty relation
list and synthetic native IDs in the new evidence belong only to the controlled
reproduction. The source-backed reproduction, verified inactive write/readback
contract and exact same refusal establish the structural failure without inventing
runtime values. No successful provider HTTP retrieval or complete native/XMLTV
workflow is inferred from the earlier account-creation success.

Further application tests will still be required after a reviewed correction.
They should retain sanitized counts/stable-ID presence and discovery outcome codes
at this boundary, rather than credentials, URLs or raw account responses.

## Regression results and change inventory

**689 distinct offline tests pass**, zero failures: the existing 681 plus eight
source-backed investigation tests. The tools suite now has 147 tests; all native
hardening, permanent streaming, persistence, guard/lifecycle, UID1000, network,
transport/admission and socket-audit suites pass. The audit command repeats 35
already-counted unit tests and adds three local socket fixtures, giving 724 test
executions. These are offline/local fixtures, not application-runtime acceptance.

New files only:

- `tools/tests/test_dispatcharr_native_group_investigation.py` — eight tests.
- `tools/tests/fixtures/native-group-source-evidence.json` — exact source excerpts.
- `tools/tests/native-group-investigation-results.json` — hashes and test evidence.
- This report.

Exact new-test hashes, unchanged source hashes, excerpt provenance and suite log
hashes are in `native-group-investigation-results.json`. The protected transition
manifest, source/image pins, adapter, simulator, runtime harness, security controls
and all historical acceptance evidence remain unchanged. No test-only correction
was applied because a fixture-only correction cannot resolve this lifecycle defect.

## Recommendation

**NO-GO** for retry, image binding or deployment. A separately authorized correction
must reconcile explicitly authorized discovery of an inactive account with the
native task's active-only predicate and make discovery failure observable to its
caller. Preserve operator authorization, guard/VPN checks, blocked background
requests, inactive defaults, bounded imports, journals and exact stable-ID mapping.
Do not simply remove the active predicate globally or activate accounts to make
tests pass. The simulator's fidelity should then be aligned with the reviewed
contract, with real isolated application evidence before image-binding review.

No Docker operation, image build, host access, production change, provider request,
credential access or application-runtime attempt occurred. Stop after publication.
