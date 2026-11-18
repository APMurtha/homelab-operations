# Dispatcharr runtime socket-audit diagnostics

Evidence baseline: `6bf39a6f2a169ce2b0d63861fe30d5fb37f2bef8` on
`docs/udm-pro-max-migration-prep`.
Retained image reference:
`sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.

**Offline diagnostics PASS: 608 distinct tests pass. GO for one further isolated
diagnostic run only after separate authorization. Application acceptance and image
binding remain NO-GO.** No Docker operation, image build, application runtime
integration, production access, provider request or playback occurred in this task.
The image reference comes from the existing report; it was not inspected anew.

## Confirmed diagnostic blind spot

The old `runtime_test.py` hook watched Python `socket.connect` and
`socket.getaddrinfo` events. It extracted a host and permitted only text values
starting with `/`, or exactly `127.0.0.1`, `::1`, or `localhost`. Every other
representation wrote one generic stderr marker and called `os._exit(86)`.
It recorded no family, classification, call stack or phase. The child's ordinary
stdout/stderr went to a private application logfile. The final result was written
only at the end, on disposable tmpfs; abrupt termination could remove all phase
completion evidence before the host runner read it. The host then reported a
missing result instead of the underlying refusal.

Possible legitimate local operations include pathname or abstract Unix IPC,
PostgreSQL/Redis connections, local HTTP test clients, byte-form addresses,
expanded or IPv4-mapped IPv6 loopback, and kernel-local netlink activity. Only
some representations were permitted. This explains potential misclassification;
it does **not** identify the previous operation. An actual forbidden request is
still possible. The prior runtime acceptance JSON and report are unchanged;
no migrations, Celery task results or native workflow are retroactively accepted.

## Harness changes

- `runtime_diagnostics.py`: shared standard-library classifier, sanitized record
  encoder, checkpoint snapshots and host recovery. Classification never resolves
  DNS. It emits family, connect/getaddrinfo operation, Unix/loopback/private/public/
  unknown class, address representation and an optional fixed fixture-service
  label. No address, hostname, path, raw port or destination hash is serialized.
- `runtime_test.py`: delegates denial to the diagnostic writer; adds explicit
  completion checkpoints and sanitized unittest failures; passes an inherited
  evidence descriptor to the UID1000 application process. Removes raw traceback
  messages and the application's raw logfile-tail fallback from exported results.
- `run_runtime.py`: requires the new helper in the reviewed fixture payload;
  creates a fresh private attempt directory instead of overwriting prior evidence;
  recovers sanitized records even without final JSON; treats a refusal or nonzero
  exit as failure. The exact owned-container cleanup and production comparisons
  remain in place for a future authorized run.
- `test_runtime_diagnostics.py`, `audit_local_fixture.py`,
  `run-audit-offline.sh`: offline synthetic-event, crash, sanitization and real
  namespace-confined socket regressions.
- README and this report explain the evidence boundary. The transition manifest
  changes only test-harness `source_files`: updates the runner hash and adds five
  diagnostic/runtime fixture hashes. All **80 installed-target mappings**, all
  other manifest sections, application patches/source pins, image contracts,
  build recipe, Compose, guard, relay and systemd sources remain unchanged.

### Refusal contract and sanitization

No destination is newly allowed. Well-formed pathname-text AF_UNIX and the three
existing literal loopback/localhost strings retain their permission. Byte-form
addresses, abstract Unix sockets, other 127/8 addresses and expanded/mapped IPv6
loopback receive accurate local classifications but remain denied. A malformed
pathname used as a TCP hostname is now rejected rather than inheriting the old
string-prefix exception. Unknown families and kernel IPC are denied.

On refusal the record includes current phase, fixed test identifier (or
`unassigned`), supervisor/application role, PID, effective UID, main/background
thread label, family, operation, classification, bounded stack and explicit
refusal reason. Stack capture walks frame metadata only: at most eight sanitized
Python file basenames/functions/line numbers from known code roots. It never
reads source lines, locals, arguments, exception messages, environment values,
request bodies or raw provider responses. Generated/URL filenames are redacted.
All exported fields use closed schemas and fixed labels; unknown details are
removed. Unittest error output uses sanitized exception class/stack only.

The phase/test context describes what the test process is currently doing. A
background thread's event may overlap another operation; its context is not
proof of the causal task identity. Stack metadata and the background label help
investigate that uncertainty without logging task arguments or credentials.

Denial always terminates with code 86, including persistence errors or exhausted
diagnostic record limits. Emergency records retain classification where possible.
The audit still watches only connect/getaddrinfo in the instrumented Python
process; it is not coverage of every syscall, child process or network API.
Network-none isolation remains mandatory and is the independent containment layer.

### Durable bounded evidence

Each role maintains a private 0700 snapshot directory and a 0600 regular snapshot
file. Publication uses exclusive no-follow temporary files, atomic replacement,
file fsync and directory fsync. The application snapshot is UID1000-owned; the
supervisor snapshot is root-owned in the future container. Snapshot readers check
owner, mode, type, link count and size, then rebuild a closed sanitized schema.

Each record is also emitted in one bounded NDJSON write on the inherited stdout
descriptor, independently of ordinary private application output. This lets the
host recover checkpoints if PID1 is killed before final JSON or tmpfs disappears.
The parent also reads the child's snapshot after abnormal child exit while its
own tmpfs is still available. Recovery retains both the last chronological failure
and the last socket refusal, so a generic parent error cannot hide the cause.

Limits: 128 records per role, 4,000-byte record body, 64 KiB snapshot; a handful of
persistence metadata bytes follow body sizing. Future temporary-container logging
is json-file with 1 MiB × 2 rotation, and collection is limited to 1,000 lines /
2 MiB. Each future run retains `runtime.log`, `diagnostics.json`,
`runtime-result.json` and its receipt under a new `runtime-attempt-*` directory
beside the original build receipt. No writable host bind is added and no daemon
logging settings change. Raw private service/application logs are not promoted.

Durability has limits: container log-driver buffering, log rotation, disk failure,
host power loss, a kill before emission or failure of both evidence sinks can
still lose evidence. Missing/invalid evidence is a failure or an explicit gap,
never inferred success. The isolated crash tests establish process-abort/SIGKILL
recovery on this filesystem, not a universal power-loss guarantee.

## Explicit phase evidence

| Phase | Completion evidence required |
| --- | --- |
| PostgreSQL | initdb succeeds, readiness succeeds, disposable database created |
| Redis | authenticated PING succeeds |
| Django setup | actual django.setup returns successfully |
| Migrations | migrate returns; migration-row count and ordered-name MD5 fingerprint queried |
| Celery startup | actual worker context entered; eager execution disabled |
| Task registration | required native and synthetic task names exist in app registry |
| Actual task execution | Redis-backed result retrieved and the test's outcome assertions pass; cumulative count |
| Native API | every designated native-API test has explicitly passed |
| Xtream/XMLTV | native adapter returns and selected stream/channel, EPG ID and programme assertions pass |
| uWSGI | two fresh Redis-backed worker heartbeats and local HTTP 200 |
| Application suite | all tests succeed with no skips |
| Final acceptance | zero child exit, successful result and all required application checkpoints; supervisor cleanup completed |

A phase-start record is never completion. A later test starting is never evidence
that a prior phase passed. Migration MD5 is a deterministic test-database
fingerprint, not a cryptographic source-integrity guarantee. All application
completion points above are prepared wiring, **not newly executed results**.

## Offline regression evidence

The complete existing **570-test** baseline passes. Added **35 pure diagnostics
tests** and **3 real isolated socket fixtures** give **608 distinct passing tests**,
zero failures. A second focused run overlaps the same 35 tests and is not counted
twice. Native offline systemd syntax/dependency verification also passes; it
executes no units and contacts no service manager.

| Suite | Tests |
| --- | ---: |
| Provider CLI/native adapter tools | 139 |
| Native provider hardening | 91 |
| Permanent streaming/security/lifecycle/registration/guard | 210 |
| Persistence | 26 |
| Guard-interface assessment | 14 |
| Trusted guard design feasibility | 28 |
| Native hardening isolated fixtures | 14 |
| Native policy/packaging permission fixtures | 40 |
| Image-harness offline tests (8 existing + 35 new) | 43 |
| New isolated socket fixtures | 3 |
| **Total** | **608** |

New tests cover Unix text/bytes/abstract IPC, IPv4/IPv6 loopback, private/public/
link-local/unknown destinations, malformed addresses, netlink refusal, DNS-free
classification, sanitized stack capture, credential/URL/locals/body redaction,
strict snapshots, phase non-inference, record limits and sink failure, sanitized
unittest errors, final-acceptance prerequisites, and recovery without final JSON.
Real subprocess `os._exit(86)` and SIGKILL tests retain explicit checkpoints.

The three actual socket fixtures run inside a fresh user/network namespace with
only loopback and no external default route. A Unix-path socket and literal IPv4
loopback client connect successfully. A genuine public-address socket.connect is
refused by the Python audit hook with exit 86 before the kernel operation, and
its destination value is absent from retained output. Actual IPv6 socket traffic
was not exercised; IPv6 classification/denial tests use synthetic events.
No real provider or production destination was contacted.

An initial fixture setup checked host-mounted sysfs rather than namespace
interfaces and stopped before socket tests ran. It was corrected to use
socket.if_nameindex in the actual namespace; the complete final run passes.
This fixture correction did not authorize additional destinations.

Machine-readable counts, source hashes and local regression-log SHA-256 values
are in `runtime-audit-results.json`. Logs contain synthetic test evidence only;
private runtime logs are not included in Git.

## Exact changed-file inventory

The report itself is excluded from its own hash inventory. No application or
production configuration bytes are changed.

| Repository path | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/hardened-image-integration/README.md` | `52acef9f92efc1ec307c843907fd7b969c62136994b7e95f15f759c6e29c857a` |
| `configs/dispatcharr-iptv/hardened-image-integration/audit_local_fixture.py` | `49462fd7e94ec9f1160839b14d742ae4e220c89aa80e9d9566edcf8b94197cb6` |
| `configs/dispatcharr-iptv/hardened-image-integration/run-audit-offline.sh` | `bf19aa8d9c2f0ae12c214f87876ce8eb2f8c7f39a49243573664d912fee8145d` |
| `configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py` | `763839d42e80e933e52918349bd7f34dd816b546b2f2fe0c92b3ff69b326a90e` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_diagnostics.py` | `de5ed39ff92da1002e2f90507511d9dd3cfc878b8e5de55126fb30d467bae432` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_test.py` | `56c68d1412984d7b0351bd0ecc4cc6c4862c6a32bccb0eccd412e9500fca6333` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_diagnostics.py` | `3cbac9f04bf49805543d9e40f87e1f1c3a27af649f46880e4d221b8153142477` |
| `configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json` | `53bdf20657e1b7046829016eac8b32a11727eed94cce3e9874bd6b31f72c53fe` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime-audit-results.json` | `c63911785d0870049dd0bc9d65fba21bcc17a8da450e34689e9974953a6617d9` |

## Remaining uncertainty and next-run prerequisites

The original socket family, address class, caller and refusal reason remain
unknown. A future refusal must be reviewed from its sanitized record; do not
broaden an allowlist merely because it classifies as local. An empty or missing
record must remain a diagnostic gap.

GO is limited to proposing **one separately authorized isolated runtime test**
against the retained image, with fresh image/source/build-receipt verification,
capacity checks, exact fixture hashes (including runtime_diagnostics.py),
network-none/no production mounts or credentials, unchanged resource limits,
owned-resource cleanup and production preservation comparisons. No rebuild is
needed for this harness-only change. Confirm bounded log support and preserve
all old receipts. Stop on a new refusal, source drift, isolation uncertainty or
application failure; do not retry automatically.

No new actual Django, PostgreSQL, Redis, Celery, API or XMLTV integration result is
claimed here. Image binding, deployment, provider activation and real AirVPN
authorization remain NO-GO pending the separately authorized application matrix.
