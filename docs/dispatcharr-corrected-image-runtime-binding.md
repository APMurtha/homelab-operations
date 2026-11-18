# Corrected image binding for isolated application acceptance

**GO for one separately authorized isolated application acceptance attempt, after
fresh preflight. No runtime attempt was launched.** All **728 distinct offline
regressions pass**, zero failures. Production remains unbound: aio_image=null.
No Docker/SSH operation, image operation, provider request or production write
occurred during this offline binding review.

| Binding identity | Value |
| --- | --- |
| Corrected immutable test image | `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439` |
| Build evidence | `e0da9ff06ab827f6eaf79397d15dd8ce6399fe10` |
| Application-source correction | `8764cfdaff97b8d94102f03d9b367f1e1de6c317` |
| Build-results SHA-256 | `2ed95e293499735a516a0ef8eb996411b485e7b4917c7f77cad83757273e9d5c` |
| Unchanged production release-contract SHA-256 | `891b115e0ad7b6e154aab9f1967fca6009e60e8ae6ba6996b14a980ef9573af1` |
| Canonical eighteen-source contract SHA-256 | `3a920af181c06796131bded5c283fa2ed9c76578d3dc59bf847b5bb78ae4a546` |

## Exact binding changes

corrected-runtime-binding.json is the review inventory for the immutable image and
all eighteen expected hashes. Its values were checked against the published built
image verification and approved release contract; no hashes were learned from
unexpected runtime output or regenerated to accept drift.

runtime_admission.py now requires this corrected image, uses its exact eighteen
hashes, rejects another image before inspection, and prevents a receipt for an old
image/contract from authorizing stabilization. Only three expected source values
changed; eleven hardened outputs and four inherited readiness hashes match the
historical retained-image contract unchanged:

| Corrected application file | Approved SHA-256 |
| --- | --- |
| `apps/m3u/api_views.py` | `6c48c35abc821efbb428a74c832e7c8c018eef472d6f987505169cd83d902936` |
| `apps/m3u/tasks.py` | `75a6eb9276ec96b0e5de2ae2b1274a63ffe47ef89cc8d6c1620a89e049467fb1` |
| `core/provider_security.py` | `8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004` |

run_runtime.py's accepted image and exact admission-helper pin advance together.
Its image inspector pin is unchanged. runtime_transport.py dispatches the same
corrected image and pins the new runner and test fixture bytes. Host-helper loading,
exclusive attempt identities, detached execution, monitoring and cleanup behavior
remain unchanged. Old image acceptance is removed from the current controller;
old jobs and their receipts must still use their originally staged transport copies.

| Test file/inventory | SHA-256 |
| --- | --- |
| `corrected-runtime-binding.json` | `d260c99e86b43b378f0001c6d5fa432b8c100d021005e6817b0e74888558a7e7` |
| `runtime_admission.py` | `7e029a8fb42ec2b813a0d58fd1a0e399e2b6a9a116741b570e275a9d674bee44` |
| `run_runtime.py` | `8ae09016286ca99f82d42b3ea915235a12b5e754701499287495bca02039afbd` |
| `runtime_transport.py` | `70697278636f729289dfae6250dd20f13797cf236d0d34e71ecd00e60de36872` |
| `runtime_test.py` | `3641f48248a43a3182ff10f2f7121d2a0a4c11110f51427216dc5941e5381bfd` |
| `runtime_diagnostics.py` | `de5ed39ff92da1002e2f90507511d9dd3cfc878b8e5de55126fb30d467bae432` |

The complete previous/new file inventory, all eighteen hashes and regression log
hashes are in corrected-runtime-binding-results.json. The pin chain is checked by
regressions: transport -> exact runner -> exact admission/inspector, plus exact
runtime fixture and unchanged diagnostic module. Production aio_image remains
null; no Compose image pin or source/image contract for deployment was changed.

## Necessary runtime-fixture adjustments

The supported API exchange now retains bounded, sanitized evidence after account
creation. For the positive synthetic provider it performs a fresh supported detail
GET immediately after POST, before the adapter can activate the account. The fixture
requires is_active=false, valid native group PKs, unique category IDs, disabled groups
and disabled automatic synchronization. It records only IDs/flags; credentials,
URLs and raw response bodies are excluded.

After the actual adapter workflow, test_06 requires exactly one category `"1"`
association from that creation readback. It reads the actual isolated database's
ChannelGroupM3UAccount and confirms its persisted xc_id and native group PK match
the imported stream. These are reads/assertions, not fabricated associations or a
mocked discovery-success response. Existing selected-channel, programme, EPG and
ownership checks remain, including the unmodified native_selected_group_missing
assertion in the unchanged adapter.

The real Celery denial test now also queues an explicitly requested refresh for
the inactive fixture account, alongside its existing ambient denial and disabled
profile-refresh checks. All results must be real Redis-backed non-eager task results
and must produce no provider HTTP fixture traffic.

For denied discovery after account creation, test_05 now checks the corrected
HTTP 403 / authorization_refused envelope and returned native ID, fresh API readback
of inactive/error state, exactly one journal intent and blocked subsequent writes.
The unresolved intent/reconciliation refusal remains mandatory. No POST retry,
account deletion, forced resume or activation is added. Other fixed failure codes
and HTTP 502 are accepted only with their exact reviewed response structure.

Each account-creation HTTP status is written through the existing fsynced diagnostic
sink **before** validating its response. The event is phase_started, never a premature
completion checkpoint. Existing safe stack/test-failure records remain. Normal final
results retain the bounded creation/failure summaries. If abrupt termination prevents
those final summaries, the last durable status/checkpoint remains evidence; missing
IDs or later phases must not be inferred.

## Required runtime matrix

| Requirement | Reviewed fixture/check |
| --- | --- |
| Inactive creation and explicit discovery | test_06 creation detail readback before activation; real native view/task |
| Association persistence and stable IDs | Detail group mapping + real ORM relation + imported stream FK |
| Unauthorized / ordinary inactive refresh | test_03 actual Celery denials; test_05 denied discovery |
| Discovery failure and partial account | Structured failure, inactive/error detail, single unresolved intent |
| No blind retry or duplicate create | Journal clean/reconcile refusal, existing ownership/duplicate checks |
| Selected channels | Actual Adapter.register and one imported owned channel |
| XMLTV / programme mapping | Native source import, EPGData stable tvg-id and ProgramData |
| Django / PostgreSQL / Redis / Celery | Existing bootstrap/migrations and non-eager worker/default-DVR queue tests |
| DW English / backend | Existing unchanged DW record check and real two-worker uWSGI heartbeat test |
| Completion evidence | Existing explicit checkpoints and final-acceptance gate |

The positive network authorization remains explicitly synthetic: reviewed loopback
TLS/DNS/route fixtures, no real AirVPN grant. Tests do not claim approval of an
external provider or production stream. The plugin-maintenance opt-out remains in
the disposable fixture and meaningful native/default/DVR tasks remain registered.

## Security and historical preservation

Source-function fingerprints against e0da9ff establish unchanged runtime container
creation, isolation checks, capacity stabilization, watchdog, scoped cleanup,
production comparisons, transport launch/status/supervision and reconciliation.
The entire socket-audit/diagnostic module is byte-identical. Preserved limits:

- network=none, no ports, no production volumes/credentials/policies/databases,
  no Docker socket, read-only root and disposable tmpfs;
- 1 CPU, 1.5 GiB memory/swap, 256 PIDs, no automatic restart;
- 120-second stabilization, 180-second ceiling, load <=2, RAM >=2 GiB, disk >=1 GiB;
- 240-second application watchdog, 1,200-second detached deadline;
- exclusive attempt IDs, durable receipts, strict socket denial and scoped cleanup.

19 historical repository evidence files retain identical hashes,
including the old image's retained-image-contract.json and previous receipts/reports.
No Rivendell/private receipt was accessed or overwritten. Old pending/failed attempts
must never be reinterpreted as fresh attempts or cleared merely to proceed.

The transition manifest updates only its test-source inventory. Its installed-target
mappings and original rollback records are byte-equivalent as data; production
Compose, guard/admission unit, hardened application source/patch and release contract
hashes are unchanged. Current README guidance now points to this test-only binding;
older checkpoint notes remain labeled historical.

## Offline results

**728 distinct tests / 763 executions, zero failures.** The fifteen new tests cover
exact corrected acceptance, old image rejection before work, incorrect and mixed
hashes, old-contract receipts, build/pin agreement, duplicate identity refusal,
historical preservation, production mapping and security-function fingerprints,
strict inactive-group readbacks, sanitized failure response shape and retained
runtime lifecycle assertions.

Full suites: tools 147; native hardening 106; permanent streaming 210; persistence
26; guard 14; trusted design 28; isolated network fixtures 14; UID1000 permissions
40; harness 140; three additional socket fixtures. The audit runner repeats 35
already-counted tests. No actual application/worker or Docker environment was run;
source-backed unit fixtures are not runtime acceptance.

## Next attempt prerequisites and stop boundary

Separate authorization must permit one new exclusive attempt. Fresh host/image/
production health, capacity and session-policy preflight remains mandatory. Verify
the actual corrected image and build receipts, exact payload and all eighteen hashes
again. Use a fresh SSH-account-private work directory; do not overwrite the old
work directory's build receipt or use the root-private build workspace as runtime
state. Reconcile the reviewed build acceptance into the runner's existing verified
build-receipt schema with this image ID and preserved provenance. That preparation
has not been installed or performed on Rivendell here.

Stage only the matched current controller/helpers and synthetic fixtures; independently
verify the complete payload digest. Launch once using the existing detached transport,
then monitor only that same attempt with status. Stop on admission failure, uncertain
state/cleanup, socket refusal or application error; no automatic retry or security
relaxation. Preserve private receipts and verify all production fingerprints afterward.

**GO for one separately authorized isolated attempt only. Stop after this offline
publication; no image binding into production or deployment is authorized.**
