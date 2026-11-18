# Dispatcharr runtime test transport

**Offline transport PASS: 674 distinct tests pass. GO for review and a separately
authorized isolated application test after the live preflight below.** No actual
application test, Docker operation, Rivendell access, image operation or production
change occurred in this task. Image binding/deployment remain NO-GO.

Baseline: `8ac8d182e288aed6f688dbad0ccd86bd22949862`.
Branch: `docs/udm-pro-max-migration-prep`.
Retained image reference:
`sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be`.

## Implementation and preserved runner

`runtime_transport.py` supplies two operator commands: **launch** and **status**.
It wraps the exact approved runner, SHA-256
`c5aeadca482d51d4beb61c8b9396fe613dad6ab00304ce3ee6404762ec7090e7`, without modifying its source or calling its main function during
status. The approved image verifier, 18 source hashes, 120-second stabilization,
180-second stabilization ceiling, load ≤ 2, RAM ≥ 2 GiB, disk ≥ 1 GiB, 1 CPU /
1.5 GiB / 256-PID container limits, network-none isolation, 240-second runtime
watchdog, diagnostics and scoped Docker cleanup are unchanged.

Only the new transport, tests, README, evidence and two added test-source inventory
entries are published. All existing source pins and **80 installed mappings**
remain unchanged. No service, timer, scheduled job, listener, proxy, package or
permanent infrastructure is introduced.

## Launch and detachment protocol

The owner must select a fresh explicit attempt ID. Launch refuses an already-used
transport directory or the underlying `runtime-attempt-<id>` directory; there is
no resume/reset/force option. It creates `transport-attempt-<id>` exclusively in the
existing private build workspace. Even a partial reservation remains consumed.
Old attempt intents and all previous receipts are untouched.

Launch validates private ownership/modes and the exact runner SHA-256. It requires
an operator-reviewed whole-payload digest, checks the pinned runtime and socket
diagnostic fixture bytes and the runner's pinned host helpers, then snapshots
runner, payload and transport source into private files. This digest is not an
independent grant of authority: the operator must review the synthetic-only
fixture inventory under the approved test authorization.

A POSIX double fork creates a temporary supervisor independent of the SSH parent.
The short-lived intermediate is reaped; the detached supervisor is adopted
outside the launcher. All inherited file descriptors close, stdin/stdout/stderr
become /dev/null, and the environment is reduced to non-secret PATH/LANG/HOME.
Internal Python execution uses isolated mode. The supervisor ignores SIGHUP;
its runner is also a separate session/process group with no SSH streams.
A lost SSH response cannot cause another launch through any status path.

The supervisor claims its identity exclusively, records boot ID/PID/start ticks,
and launches exactly one worker. The worker takes its own exclusive claim,
checks its actual parent against the supervisor identity, snapshots production /
network / volume fingerprints, then invokes the unchanged runner once with the
same attempt ID. Claims cannot be reused. A supervisor must begin within 60
seconds of the reservation; a stale reservation does not authorize delayed work.

The temporary supervisor has a fixed **1,200-second overall budget**. It heartbeats
atomic private status every **five seconds**. This outer budget accommodates
verification + stabilization + the original runtime watchdog without changing any
of them. At deadline it attempts TERM against only its direct, identity-checked
runner process group, waits ten seconds, then uses KILL if necessary with one
five-second wait. It never signals the Docker daemon or a protected container.
No transport code issues Docker create/start/stop/rm: only the unchanged authorized
runner owns that lifecycle. Deadline cleanup may leave an owned test container
requiring reconciliation; it is never reported as automatically removed.

## Durable private receipts and logs

Directories are mode **0700**, files **0600**, owned by the selected SSH account.
Source/payload reads reject symlinks, non-regular files, hard links, wrong ownership
or permissions and oversized input. Snapshots/claims use exclusive creation;
status files use fsynced temporary files, atomic replacement and directory fsync.

| Artifact under transport-attempt-ID | Meaning |
| --- | --- |
| launch.json and source/payload snapshots | Immutable identity, boot, input digests and reservation |
| supervisor.claim / runner.claim | PID, boot identity and process-start ticks |
| baseline.json | Private production/container and network/volume comparison snapshot |
| state.json | Atomic heartbeat, identities and overall deadline |
| transport.log | Bounded fixed event labels and timestamps only |
| runner-exit.json | Sanitized normal/failed return candidate; no exception body |
| completion.json | Supervisor exit/deadline candidate; not independent cleanup proof |

The original `runtime-attempt-<id>` directory still holds admission.jsonl,
runtime-receipt.json, runtime-result.json and sanitized diagnostics produced by
the existing runner. They are preserved, not copied into Git or rewritten by
status. Raw worker stdout/stderr and exception bodies are discarded, not buffered
or promoted to transport logs. The original runner retains its existing diagnostic
files. The transport log has an 8 KiB cap and no heartbeat history growth; input
JSON files are capped at 8 MiB. Status never prints raw payload, private config,
credentials, provider URLs, command arguments or environment values. CLI parse
errors suppress supplied argument values.

## Read-only status and outcome rules

Status validates the reserved source/input snapshots and boot identity. It checks
current-path receipts and process identities using boot ID plus start ticks, not
PID alone. A running status requires a matching live supervisor and a consistent
heartbeat no more than 20 seconds old. It means the coordinator is active; it is
not evidence that application tests have passed.

For terminal/recovery status, it performs bounded **read-only** Docker queries:
exact generated name, attempt label and known immutable container ID. It does not
interpret an inspect error as authoritative absence. Any retained or conflicting
container prevents cleanup acceptance. It then compares current production and
network/volume fingerprints against the transport baseline. These queries have
short per-call budgets and an approximately 30-second metadata-query deadline.
No image layers are scanned.

| State | Meaning |
| --- | --- |
| running | Matching live supervisor and fresh consistent heartbeat; no pass claim |
| completed | Verified normal worker return, matching original successful runtime receipt, no live worker/supervisor, scoped Docker absence and unchanged production fingerprints |
| failed | Application/worker failed or exited abnormally; only after read-only reconciliation proves scoped absence and preserved production |
| uncertain | Missing/invalid/stale proof, changed boot, lost supervisor with live worker, unavailable Docker, retained resource or fingerprint conflict; cleanup is not accepted |

A stale heartbeat never triggers a restart. If the supervisor crashes but the
worker finishes, status may later reconcile the durable worker/application receipts
and report completed or failed. Missing normal-return proof can never produce an
application PASS. Abnormal exit with no owned container and matching baseline may
be reported failed/cleanup-complete; that is a reconciled failure, not inferred
application success. Missing worker identity or successful runtime receipt remains
uncertain. `completion.json` alone is never sufficient.

**Status has no launch, mkdir, receipt write, signal, cleanup or main-call path.**
Repeated terminal polling was tested against byte/mtime snapshots and mocked
process-launch entry points. A successful status-command exit code means the
query returned; operators must inspect the JSON state and cleanup_complete fields.
An SSH timeout or `launch` exit 0 means neither application acceptance nor cleanup.

## Exact future launch and monitoring commands

These commands are a plan, **not executed here**. Before separately authorized
execution, stage the reviewed files and synthetic payload at the private paths
below, directory mode 0700 / files mode 0600. Verify their published hashes and
all existing test prerequisites. The approved runner must retain its original
bytes; source files copied directly from Git commonly need private staging modes.
The payload must contain the same reviewed synthetic client/publisher/runtime
fixtures, all 18 expected hashes, and both host helper entries required by the
sequencing release. Do not include real policies, credentials or provider data.

The workspace below is the existing retained-build workspace, not a production
configuration directory. Select a newly authorized unused ID and retain it across
all later monitoring calls. Replace the payload digest placeholder with the digest
from the separately reviewed payload manifest; leaving it unchanged fails closed.

```sh
DISPATCHARR_ATTEMPT_ID='isolated-runtime-review-03'
DISPATCHARR_REVIEWED_PAYLOAD_SHA256='REPLACE_WITH_REVIEWED_64_HEX_DIGEST'

python3 /home/murth/.codex/plugins/cache/nest-shared/nest-home/2.1.0/runtime/nest_plugin.py \
  --person andrew --system andrew-media run server-access exec media -- \
  python3 /tmp/dispatcharr-runtime-transport-review/runtime_transport.py launch \
  --work /tmp/dispatcharr-native-image-20261118T020258Z \
  --attempt-id "$DISPATCHARR_ATTEMPT_ID" \
  --runner /tmp/dispatcharr-runtime-transport-review/run_runtime.py \
  --payload /tmp/dispatcharr-runtime-transport-review/runtime-payload.json \
  --payload-sha256 "$DISPATCHARR_REVIEWED_PAYLOAD_SHA256"
```

**Invoke launch once.** If its response is lost, do not repeat it. Reconnect and
query the same attempt, using the reviewed staged entry point:

```sh
python3 /home/murth/.codex/plugins/cache/nest-shared/nest-home/2.1.0/runtime/nest_plugin.py \
  --person andrew --system andrew-media run server-access exec media -- \
  python3 /tmp/dispatcharr-runtime-transport-review/runtime_transport.py status \
  --work /tmp/dispatcharr-native-image-20261118T020258Z \
  --attempt-id "$DISPATCHARR_ATTEMPT_ID"
```

Repeat only this status command at a modest cadence (for example ten seconds).
It does not run another application attempt. Do not invoke internal _supervise or
_execute commands manually. The job's snapshotted sources allow already-started
work to continue if the staging directory or SSH client disappears; keep the
reviewed staging/status entry point available for subsequent monitoring.

## Failure recovery and limitations

For a lost SSH connection, first query status for the same identity. For running,
continue read-only monitoring. For uncertain, preserve all artifacts and stop
further writes. Reconcile exact process identities, admission creation intent,
known container ID/name/attempt label and the original production baseline.
Neither an empty application collection nor a PID file alone proves cleanup.
Never clear claims, reuse an identity, invoke main again, reset data or delete
uncertain resources. If a test container remains, obtain the required scoped
cleanup authorization and verify exact ownership before any mutation. This
transport supplies no automatic container-recovery/reset command.

The detach/disconnect guarantee covers ordinary POSIX SSH/channel hangup and
launcher exit. **Host policy can still kill whole login-session cgroups despite
setsid**. This behavior is documented in the [systemd logind reference](https://www.freedesktop.org/software/systemd/man/latest/logind.conf.html#KillUserProcesses=). Before the first real launch, verify the existing noninteractive SSH,
logind and cgroup teardown behavior read-only under the selected account. If that
behavior kills detached descendants or cannot be established sufficiently, stop;
no host-policy/service change is authorized by this plan. No live host policy was
inspected in this offline task. Reboot, OOM, administrative kills and kernel or
filesystem stalls remain external failures, not guaranteed survival cases.

The overall watchdog is enforced while its temporary supervisor is alive. If the
supervisor itself dies, the worker may finish under its original watchdog or
remain unresolved; status fails closed until reconciled. There is no permanent
service to resurrect it. fsync and scheduling can be delayed, so deadline handling
is not an instantaneous kernel-enforced wall-time guarantee. Trusted host owners
can alter files; private receipts and hashes protect normal operation and detect
drift, not malicious root activity. No source/image/production access is relaxed
to work around these limitations.

## Offline verification

**674 distinct tests pass: 644 preserved baseline tests plus 30 new transport
regressions.** There were zero final failures. Tests launch actual detached local
POSIX fixture processes but replace the runner pin only inside a temporary test
copy with a synthetic runner. The release CLI has no fake-runner flag; its runner
pin remains exact. Fake Docker replies are fixture functions, not daemon calls.

Coverage includes concurrent and sequential duplicate refusal; consumed runtime
identities; normal completion; real simulated SSH-parent SIGHUP; supervisor SIGKILL
with the worker continuing; worker os._exit; outer timeout TERM/KILL; uncertain
container creation; partial/missing receipts; stale heartbeat; wrong boot;
source/payload drift; private-file/symlink refusal; original-receipt conflict;
production fingerprint conflict; Docker unavailable; PID-reuse signal refusal;
secret-safe logs/errors; previous receipts intact; and polling without file or
process-launch side effects. Fixture timing is accelerated locally; the shipped
20-minute, five-second, twenty-second and ten-second constants are unchanged.
No production image, Django/Celery application or provider was executed.

All prior security, lifecycle, registration, guard, boot-admission, permission,
sequencing and socket-audit suites passed. The image-harness suite has 109 tests;
overlapping 35 diagnostic and 50 source-inventory reruns are not double-counted.
One initial test-command directory typo was corrected before the final persistence
suite passed. Log hashes and counts are in the sanitized result JSON.

## Exact changed-file inventory

The report excludes its own hash. The result JSON excludes its own hash from its
internal inventory.

| Repository path | SHA-256 |
| --- | --- |
| `configs/dispatcharr-iptv/hardened-image-integration/README.md` | `fe8fdde788c268d5e8994f738ff113d51a8e711e911fe09c2aa0129d9a521cd3` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime_transport.py` | `fb69c44a15977ca424a897665836de1047b28fd6df65e44fc8dd04023455833a` |
| `configs/dispatcharr-iptv/hardened-image-integration/test_runtime_transport.py` | `b06ba16a3704ade9331925617475cb4d638c953f4f21172007c88819cf5d1b3d` |
| `configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json` | `aa6747b538335f81644b05acf0ed8c8a155e5c6650cbbc44faa627b8bbdc766b` |
| `configs/dispatcharr-iptv/hardened-image-integration/runtime-transport-results.json` | `f51764d78eac11f70c0077ae502344d8a9ee2a9ed8aa3821b9f672f198ce0639` |

The transition manifest adds only runtime_transport.py and its regression test to
the source inventory; it changes no existing pin or installed-target mapping.
The approved runner, image verifier, stabilization helper, runtime test, diagnostics,
server/application sources, Compose, guard and systemd files are unchanged.

**GO for the transport mechanism's offline review.** One real isolated test still
requires separate owner authorization, exact artifact/payload preflight, fresh
production/capacity checks performed by the unchanged flow, and the existing host
session-policy prerequisite. No real launch, image binding, deployment, provider
activation or playback follows this publication.
