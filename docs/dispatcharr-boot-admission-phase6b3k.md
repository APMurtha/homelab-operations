# Dispatcharr Phase 6B-3K — minimal boot admission candidate

2026-11-16. Rivendell, 10.10.20.30. **Repository-only proposal; not installed.**

**Recommend A: one bounded resource-admission helper in the existing stack unit's
prestart path.** Retain the existing health grace, application startup and security
controls. GO for independent review and a separately approved controlled
installation; **NO-GO for claiming reliable unattended boot recovery yet**.

## 1. Evidence and installed baseline

Reviewed the published [3H reboot](dispatcharr-reboot-validation-phase6b3h.md),
[3I investigation](dispatcharr-boot-failure-investigation-phase6b3i.md) and
[3J recovery](dispatcharr-controlled-recovery-phase6b3j.md) reports against the
current installed minimal configuration.

| Observation | Failed cold boot | Successful unchanged recovery |
|---|---:|---:|
| Mean idle during application initialization | 0.107% | 31.165% |
| Mean CPU steal | 25.808% | 14.805% |
| Mean load1 on four vCPUs | 42.283 | 1.968 |
| Application HTTP readiness | Rejected at about 306 seconds | 71.831 seconds |
| Complete unit activation | Failed and cleaned up | 114.926 seconds |

Sixteen unrelated containers started during Docker boot restoration. The guard
and VPN succeeded, but Nginx returned 502 while uWSGI was not ready. PostgreSQL
was responsive, migrations had nothing to apply, and no OOM was observed.
Before 3J, consecutive samples showed 89–92% idle, 1.7–3.4% steal and load1 near
0.5–0.6; a final check measured 95.63% idle and 0.42% steal.

CPU contention is demonstrated; exclusive causation is not. Warm caches,
time-varying hypervisor scheduling and different sampling windows confound the
comparison. A resource gate cannot prove eventual application health or prevent
load from rising after admission. The 3J steal spike during successful startup
also rules out treating any instantaneous steal threshold as a universal guarantee.

Read-only inspection at 19:13 UTC confirmed systemd **255.4**, no existing stack
drop-ins, the original seven files matching their reviewed hashes, healthy
dedicated containers and a passing running-contract verifier. A later read-only
comparison confirmed unchanged container identities, images, start times,
HostConfig fingerprints, health, Docker process and networks; candidate targets
were absent. No running deployment file or state was changed.

## 2. Alternatives

| Approach | Complexity / maintenance | Reliability and operational risk | Decision |
|---|---|---|---|
| **A. Bounded resource-aware prestart** | One stdlib Python helper plus one existing-unit drop-in; fixed proc telemetry and explicit thresholds | Avoids starting during measured contention; can refuse conservatively or miss later spikes. Does not prove app readiness. | **Recommend** |
| **B. Additional dependency sequencing** | Few directives only if a trustworthy completion signal already exists; otherwise cross-stack polling/coupling | Docker-ready ordering already existed. Other applications may still initialize, lack healthchecks, or be intentionally stopped/unhealthy. Their failures must not become Dispatcharr dependencies. | No suitable additional readiness signal demonstrated |
| **C. Longer Docker start period** | Small Compose change but requires applying changed container configuration | Keeps strict HTTP checks, yet lets the app compete with the boot storm. No measured completion under that storm establishes a correct larger grace period. | Reserve for evidence of slow initialization after adequate admission |

Systemd 255 offers `ConditionCPUPressure`, but a condition is a snapshot that can
skip activation, not a bounded wait for the 3J idle/steal/load criteria. See the
[versioned unit documentation](https://www.freedesktop.org/software/systemd/man/255/systemd.unit.html#ConditionCPUPressure=).
An `After=multi-user.target` dependency is inappropriate here: this enabled stack
already participates in reaching that target and can create an ordering cycle.
CPUWeight settings on the Compose-launching service would not directly control
the Docker-managed application cgroups. No new dependency on Jellyfin, Arr
applications, download services or their health is proposed.

## 3. Candidate and exact admission behavior

Candidate directory: [boot-admission-phase6b3k](../configs/dispatcharr-iptv/boot-admission-phase6b3k/README.md).
Only two future installed files:

| Source | Proposed destination | SHA-256 |
|---|---|---|
| `admit.py` | `/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py` | `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917` |
| `20-resource-admission.conf` | `/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf` | `72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb` |

The unchanged base unit hash is
`30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e`.
The artifact manifest also covers README/tests; those are not runtime components.

The drop-in resets only the ExecStartPre list, retaining every original command
in its original relative order, to insert admission after input validation:

```text
existing guard unit -> Docker ready -> input verification
  -> CPU admission -> accepted guard reapply -> final security/topology preflight
  -> existing VPN/app/gateway health sequence -> running verification
```

No dependencies, restart policy, ExecStart, ExecStartPost or ExecStopPost change.
The original seven files remain byte-identical. Resetting the prestart list makes
this candidate deliberately dependent on the reviewed base; future unit upgrades
must reconcile the repeated commands rather than blindly retain the drop-in.

The helper reads only `/proc/stat` and `/proc/loadavg`, requiring:

- Exactly four online CPUs, matching Rivendell's reviewed topology.
- Three **consecutive five-second** samples with idle >=50%, steal <=10% and
  load1 <4, reflecting the 3J pre-start criteria.
- A single **300-second monotonic admission deadline**, never reset by failures.

Earliest admission is about 15 seconds. Sleeping occurs only to measure CPU
deltas; there is no fixed boot delay. It applies on each actual stack activation,
including a normal restart, not as an ongoing monitor. An already-active unit is
not re-gated simply because its files are reloaded.

Guest counters are not counted twice. Invalid/reset/zero counter intervals reset
the streak; missing/malformed/non-finite telemetry or a topology mismatch refuses
startup. Linux documents that iowait can decrease, so such an interval is discarded
rather than clamped into a qualifying sample. See the
[kernel proc documentation](https://docs.kernel.org/filesystems/proc.html).

The helper has no Docker/systemd/nft/network API, signals, daemon, persistent state,
credential access or application-data access. It logs only bounded JSON timing,
idle/steal/load and decision fields (at most approximately 61 records per attempt).
It exits after admission and cannot reserve capacity or supervise playback.

## 4. Failure and timeout behavior

Exit 0 permits the next original prestart command. Exit 1 refuses at the admission
deadline; exit 2 indicates invalid telemetry/topology; interactive cancellation
returns 130. Normal SIGTERM semantics are retained. No result is treated as
successful after the deadline, even after oversleep or scheduling delays.
The five-minute limit bounds admission decisions; CPU starvation can delay when
the process is scheduled to report refusal. The existing service timeout remains
a fallback for a hung command.

A failed ExecStartPre prevents Compose startup and runs the original ExecStopPost.
The unit becomes failed visibly, retains `Restart=no`, and does not retry later.
Cleanup stops only gateway, Dispatcharr and the dedicated VPN; it does not delete
data, remove networks, flush rules or restart unrelated Docker services. These
are systemd's documented [prestart/failure semantics](https://www.freedesktop.org/software/systemd/man/255/systemd.service.html#ExecStartPre=),
not a newly demonstrated live failure test. Docker-API-unavailable cleanup retains
the existing limitations; no emergency controller or cgroup mechanism is added.

**Timeout clarification:** systemd 255 rearms its timeout for successive command
spawns, including prestart steps. `TimeoutStartSec=540` is not one aggregate
540-second activation budget. This is confirmed by the versioned implementation's
`service_run_next_control`, `service_enter_start_pre` and `service_spawn_internal`
paths in [systemd v255 service.c](https://github.com/systemd/systemd/blob/v255/src/core/service.c).
The new helper has its own five-minute bound; subsequent commands retain their
existing timeout behavior. Total activation may exceed nine minutes. No aggregate
job deadline, new timer or timeout increase is included in this single-change plan.

Compose's `--wait-timeout 360`, Docker's 180-second initialization grace, HTTP
readiness, retries, and the existing 240-second stop timeout stay unchanged.
Admission can add up to five minutes before normal initialization; it does not
turn a 502 into readiness or mask a Redis/database/worker fault. The selected
five-minute wait is an operational ceiling, **not measured proof that Rivendell
will settle within it without Dispatcharr**. If conditions never qualify, the
service remains failed/stopped until explicit operator action.

## 5. Security and unrelated services

The guard remains ordered before Docker. Admission happens before the existing
post-Docker guard reapplication and final namespace/network verification, so the
resource wait does not move the last security check away from Compose startup.
Protected Docker restart policies remain `no`; direct container starts outside
the managed path remain an operational limitation of the accepted design.

The gate neither installs nor weakens VPN, DNS, IPv6, gateway or firewall policy.
Existing Gluetun kill-switch/namespace protections and accepted nftables controls
remain authoritative. No gate result overrides a failed security preflight.
Deliberate privileged removal of protections is still outside that guarantee.

Docker retains soft dependencies on the stack/guard so unrelated containers can
start despite refusal. The extra wait can delay the stack's contribution to
multi-user target completion, but adds no dependency on unrelated application
success and issues no action against them. Existing SSH/management dependencies
are unchanged; reachability still needs verification during the live boot test.

## 6. Offline validation

**28 focused tests pass**, including settled admission, the 3J prestart values,
failed-boot-like contention, independent idle/steal/load failures, streak reset,
deadline preservation, exact-deadline refusal, oversleep/reader/logging delays,
counter decrease/freeze, malformed telemetry, CPU topology change and cancellation.
Tests explicitly show that later load spikes are not continuously supervised.

Unit composition tests pin the base hash, preserve original checks/order and all
other directives, and model failure blocking startup with scoped cleanup. These
are deterministic clock/proc fixtures and a lifecycle model, not running systemd
or Docker failure experiments. The helper import set contains no external-control
library, and log fields are allowlisted.

**12 existing minimal-persistence regression tests pass**, retaining the accepted
policy, namespace, port, image, missing-network/VPN and failure cleanup checks.
**Native offline systemd verification passes** against the exact base units and
candidate drop-in, using a temporary Docker readiness fixture. Local systemd is
262; Rivendell is 255. The relevant old directives/semantics were reviewed against
255, but native verification on 255 remains an installation preflight. The initial
local sandbox socket refusal was resolved by permission for the offline parser;
no services were installed or executed. Reproduction commands are in the README.

No live resource gate, restart, reboot, packet test, service-manager installation
or health-grace adjustment was used for candidate tests. Existing read-only
verifiers were used only for live inspection; candidate execution was offline.
The two candidate targets remain absent on Rivendell, and read-only before/after
inspection confirms the running deployment stayed unchanged.

## 7. Controlled installation and rollback plan — NOT EXECUTED

After explicit installation approval:

1. Confirm healthy service/SSH baseline, no viewers/jobs to disrupt, unchanged
   seven-file hashes, accessible existing checkpoint/rollback artifacts, base unit
   hash above, and no existing stack drop-ins. Reconcile any drift; never merge
   a reset list over unknown overrides. Record absence of both new target files.
2. Stage only the two reviewed candidate files privately on Rivendell. Compare
   their hashes with the Git-reviewed manifest; reject symlink/ownership surprises.
3. Install both files root:root 0644, creating only their required directories.
   Do not replace the base unit, Docker drop-in, Compose, images or security files.
4. Verify native unit syntax on systemd 255 before loading it. Run the installed
   helper once directly as a **read-only capacity probe**, without starting or
   stopping any workload; refuse activation if it fails or disagrees with telemetry.
5. Run `systemctl daemon-reload` only, then verify effective ExecStartPre order,
   unchanged start/stop commands/timeouts and service health. Reloading does not
   rerun an already-active stack. Do not restart Docker or reboot as installation.
6. Any scoped restart and subsequent cold-boot validation require separate
   authorization and the existing playback/job/console/recovery preflight.

Future root installation commands, after those checks and verified staging:

```sh
# FUTURE APPROVED INSTALLATION ONLY; not run during Phase 6B-3K.
set -eu
ADMISSION_STAGE=/root/dispatcharr-admission-reviewed
install -d -o root -g root -m 0755 /docker/dispatcharr-iptv/boot-admission-phase6b3k
install -o root -g root -m 0644 "$ADMISSION_STAGE/admit.py" /docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py
install -d -o root -g root -m 0755 /etc/systemd/system/dispatcharr-stack.service.d
install -o root -g root -m 0644 "$ADMISSION_STAGE/20-resource-admission.conf" /etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf
sha256sum /docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py /etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf
python3 - <<'PY'
import hashlib, stat
from pathlib import Path
expected = {
    '/docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py': '649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917',
    '/etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf': '72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb',
}
for filename, digest in expected.items():
    p = Path(filename)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid == s.st_gid == 0
    assert stat.S_IMODE(s.st_mode) == 0o644
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
PY
systemd-analyze verify /etc/systemd/system/dispatcharr-stack.service
python3 -B /docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py
# Require every preceding step and hash check to pass before daemon-reload.
systemctl daemon-reload
systemctl show dispatcharr-stack.service -p ExecStartPre -p ExecStart -p ExecStopPost -p TimeoutStartUSec -p TimeoutStopUSec
```

Stop after any error; the commands are a reviewed sequence, not a bypass for the
preflight. No automatic stack start is included. Root-owned manifest verification
is required at installation; the original runtime verifier is unchanged and does
not gain a separate pin for this availability-only helper.

**Rollback:** remove only the new drop-in, daemon-reload and verify restoration
of the three original prestart commands; then remove only the new helper and its
directory if empty. No database restore, image change or firewall removal is
needed. If a start is currently activating, do not race deletion against it:
wait for bounded completion, or use a separately approved scoped stack stop.
A healthy running stack need not be stopped merely to remove an unused prestart
override. Preserve the accepted guard throughout. Exact future file removals:

```sh
# FUTURE APPROVED ROLLBACK ONLY, with no activation job in progress.
set -eu
rm -- /etc/systemd/system/dispatcharr-stack.service.d/20-resource-admission.conf
systemctl daemon-reload
systemctl show dispatcharr-stack.service -p ExecStartPre
rm -- /docker/dispatcharr-iptv/boot-admission-phase6b3k/admit.py
rmdir -- /docker/dispatcharr-iptv/boot-admission-phase6b3k
```

## 8. Remaining live validation and decision

Before accepting unattended operation, separately validate a scoped start on 255,
observed refusal with no qualifying capacity through a safe approved procedure,
and a controlled reboot with console/rollback access. Capture initial load/steal,
gate samples/deadline/streak, final guard verification, actual container starts,
full PostgreSQL/Redis/uWSGI/Celery/HTTP readiness, unrelated service recovery and
management access. Do not inject host stress or change live firewall rules merely
to obtain a refusal result without a distinct safety plan.

Risks remaining: conservative load1 decay, insufficient five-minute settling,
transient capacity after admission, changed CPU topology, warm-cache confounding,
application cold-start races, Docker cleanup unavailability and absence of
continuous boot packet evidence. Neither this gate nor condition ordering is a
new proof against every transient network exposure.

**GO for review and controlled installation after approval; NO-GO for declaring
cold-boot reliability proven.** Only approach A is prepared. No health-grace,
dependency, image, controller or unrelated-service change is bundled with it.
Stop here; installation and live testing are not authorized by this phase.
