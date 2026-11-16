# Dispatcharr Phase 6B-3N — resource-aware cold-boot validation

2026-11-16 UTC. Rivendell (`10.10.20.30`), Proxmox VM 130 on Orthanc.

**FAIL — automatic Dispatcharr cold-boot recovery. PASS — resource-admission
refusal and protected stopped-state handling.** The helper refused startup at
its unchanged five-minute deadline. All three dedicated containers remain
stopped; the accepted firewall guard remains active and verified. No manual
startup, retry, rollback, policy adjustment or second reboot was attempted.

References: [managed restart](dispatcharr-managed-restart-phase6b3m.md),
[installed admission](dispatcharr-boot-admission-installation-phase6b3l.md),
[admission design](dispatcharr-boot-admission-phase6b3k.md).

## 1. Mandatory preflight

Fresh checks through the existing pinned Rivendell SSH profile established:

- Three dedicated containers healthy. Both persistence units enabled,
  active/exited, successful; Docker running; management access working.
- All nine persistence/admission files match reviewed hashes and root:root 0644
  ownership/mode. Effective four-command prestart order and drop-in match review.
- Input, guard and running-contract verification pass. VPN tun0/default route,
  OUTPUT DROP, embedded-DNS rejection, nameserver 127.0.0.1 and disabled IPv6
  checks pass. VPN HTTPS IP echo returns 198.44.159.163, different from the
  host's ordinary exit; no broadcaster request.
- PostgreSQL connectivity, authenticated Redis PING, default/DVR Celery
  responses, Dispatcharr HTTP 200 and gateway HTTP 200 pass. Both web workers
  (273/274) have fresh Redis-backed heartbeats: ages 0.531/0.615 seconds, TTL 29.
- No pending migrations; migration count 184, fingerprint
  `b00f51e91c5b882cd84d3b2579d074ca`. Read-only provider audit passes with
  zero channels/EPG sources and only expected built-in records.
- No Dispatcharr live-channel Redis keys, stream clients or media processes.
- qBittorrent API: 34 stalledUP torrents, zero download jobs, zero measured
  upload/download throughput. NZBGet API: zero queued groups, remaining data,
  download throughput and postprocessing jobs.
- Independent checkpoint on Denethor's secondary NVMe at
  `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`
  accessible; all three archive hashes match its existing manifest. Rivendell
  rollback files under `/root/dispatcharr-minimal-recovery-20261116T051539Z`
  accessible with recorded hashes; scoped recovery instructions available.
  No new backup, restore or checkpoint was made.
- Initial three-second CPU sample: idle 66.288%, steal 18.314%, load1 3.49.
  This is baseline evidence, not a promise of later admission capacity.

**Owner-confirmed prerequisites:** the selected profile has no authenticated
Orthanc/Proxmox connection, and existing Jellyfin session credentials were
unusable. Neither was silently treated as a successful live API check. The
owner answered “its fine” to each specific question confirming (1) no conflicting
VM 130 backup/snapshot/migration/replication task and an open, usable console;
(2) no active or paused Jellyfin playback. These satisfy the requested
owner-confirmation fallback; they are not independently observed task/session
records. No authentication or permission settings were changed.

## 2. One authorized reboot

Issued exactly once through the selected pinned SSH profile:

```sh
sudo systemctl reboot
```

Receipt: **20:38:15 UTC**, transport exit 0. An exclusive local intent record
prevents accidental repetition. No other VM or Proxmox node was targeted.

- Old boot ID: `1beba908-b22b-4993-88cc-4af1e893dac1`.
- New boot ID: `0de5c49c-061d-4180-b6ae-ad855eaa26d1`.
- First observed SSH return: 20:39:47 UTC, uptime 54.86 seconds, approximately
  92 seconds after the reboot request. Earlier SSH observations timed out;
  they were not reboot retries.

No separate Docker restart, service start, worker signal or configuration change
was performed. Recovery remained automatic throughout.

## 3. Observed boot timeline

Realtime and monotonic journal timestamps were preserved privately.

| UTC | Seconds since boot | Event |
|---|---:|---|
| 20:39:10.062 | 17.056 | Guard unit starts |
| 20:39:12.988 | 19.981 | Guard input verification passes |
| 20:39:15.385 | 22.378 | Accepted guard verification passes |
| 20:39:15.437 | 22.430 | Guard unit finishes successfully |
| 20:39:16.509 | 23.503 | Docker service starts |
| 20:40:15.183 | 82.176 | Docker service ready |
| 20:40:15.201 | 82.194 | Stack unit starts automatically |
| 20:40:17.323 | 84.316 | Stack input verification passes |
| 20:40:19.030 | 86.024 | Admission helper begins waiting |
| 20:45:19.037 | 386.030 | Helper blocked: admission_deadline |
| 20:45:19.130 | 386.123 | Helper exits status 1/FAILURE |
| 20:45:22.873–22.886 | 389.866–389.879 | Scoped cleanup confirms all three stopped |
| 20:45:22.936 | 389.930 | Stack fails with result exit-code |

Accepted guard installation/verification completed before Docker started. This
ordering is observed, not inferred solely from unit dependencies. Docker took
approximately 58.674 seconds from service start to ready.

The resource helper ran automatically after input verification and refused
admission. Therefore the later firewall reconciliation/topology prestart,
Compose startup, dedicated WireGuard connection, application initialization and
gateway startup were **not reached**. Their successful-path ordering was tested
in Phase 3M; it cannot be claimed as newly tested here.

## 4. Actual admission outcome

Policy unchanged: four expected CPUs; idle >=50%, steal <=10%, load1 <4;
three consecutive qualifying five-second samples; maximum wait 300 seconds.
No artificial contention, polling daemon or threshold override was introduced.

**59 samples; maximum qualifying streak 0.** None met all requirements.

| Metric across gate samples | Minimum | Mean | Maximum |
|---|---:|---:|---:|
| Idle CPU % | 0.000 | 0.083 | 0.418 |
| Steal CPU % | 7.905 | 25.360 | 51.797 |
| Load1 | 31.57 | 36.796 | 42.21 |

Final sample at 296.839 seconds: idle 0.103%, steal 27.901%, load1 31.57,
streak 0. At **300.004 seconds**, the helper recorded `blocked` with
`reason=admission_deadline`; native systemd metadata records exit status 1.
This was helper refusal, not the systemd nine-minute command timeout or an
application health timeout. The unit did not ignore the failure.

The full sanitized sample series appears in the appendix. Sample intervals show
ordinary scheduling variation under contention; the final deadline bounded the
wait. A three-sample qualifying streak was never attained.

## 5. Application, VPN and data result

| Dedicated container | ID prefix | Final state |
|---|---|---|
| rivendell-iptv-vpn | `1b9d20c93194` | Stopped |
| dispatcharr | `d34275eddd72` | Stopped |
| rivendell-iptv-gateway | `03ec8c82417e` | Stopped |

Complete IDs, images, HostConfig fingerprints, restart=no policies and prior
StartedAt timestamps match preflight; RestartCount remains zero. They never
started in the new boot. Retained stopped-container health labels are not
proof of a newly unhealthy running application.

Post-boot PostgreSQL/Redis, uWSGI/Celery, migration and HTTP/gateway readiness
are **not exercised** because the AIO never started. No Dispatcharr migration
or producer could be initiated by this rejected startup. No database write/reset,
restore, container recreation, image replacement or persistent-data deletion was
performed by this task. Existing containers, volumes and recovery artifacts
were retained; a new data-integrity scan or restore was not performed.

Dedicated post-boot WireGuard handshake/egress testing is not applicable because
its container never started. The separate original download VPN recovered
healthy. No live broadcaster or playback request was initiated.

## 6. Security and final protected state

At 20:46:11 and again at **20:47:18 UTC**, accepted guard verification passes;
all nine installed hashes/permissions remain unchanged. Guard unit enabled,
active/exited, Result=success. Docker active/running. Stack unit enabled but
failed, Result=exit-code, with protected workload stopped. No automatic repeated
start or dedicated restart loop was observed.

The accepted nftables table remains active. Dedicated network identity and
protected configuration are unchanged. Admission failure demonstrably prevented
startup, followed by successful scoped cleanup. No direct-WAN traffic from a
running Dispatcharr workload was possible in the observed stopped state.

There was no continuous packet capture. Boot ordering/current rules are not
proof against every transient packet or privileged removal of enforcement.
No deliberate firewall, DNS, IPv6, route or VPN-failure injection occurred.
Normal preboot routing checks passed; post-boot running-VPN checks were not
possible. The accepted security controls were not weakened or redesigned.

## 7. Unrelated services and resources

All container IDs, image IDs and HostConfig fingerprints match preflight.
Named Docker networks, including the dedicated network, retained identities;
Docker's default `bridge` network ID changed during normal daemon boot. This
exception is recorded rather than claiming every network ID was unchanged.
Start timestamps changed for services restarted by the host boot. No extra
unrelated-service action was taken.

Jellyfin initially returned 503 and was unhealthy. Logs explicitly reported
startup in progress, followed by encoder-capability checks and **startup complete
at 20:47:01 UTC** (its recorded application startup duration 7m13.249s).
At 20:47:18 public HTTP returned 200; at 20:47:20 Docker health was healthy.
No repair or restart was attempted.

A transient host media PID observed at 20:46:11 disappeared before identity
inspection. Jellyfin logs at that time show synthetic local `lavfi nullsrc`
FFmpeg startup checks, followed by FFprobe. This supports a startup-probe
explanation but does not retrospectively prove that PID's owner. No media
process remained in either final observation; no orphan was established.

Final observations:

- Jellyfin, original Gluetun, qBittorrent and Profilarr healthy.
- Sonarr, Radarr, Prowlarr and NZBGet running; those four have no configured
  Docker healthcheck, so running is not full application acceptance.
- Existing stopped Shelfarr and profilarr-parser conditions preserved.
- Seedboxapi running with RestartCount 2, **the same as preflight**; these are
  not two new restarts during this test.
- SSH and management access functional. No Jellyfin settings, libraries,
  tuners, guides, users or other service configurations modified.

At 20:41:40 load1 was 36.46 with MemAvailable approximately 5.83 GiB;
at 20:46:11 MemAvailable was approximately 4.77 GiB. No swap is configured.
Inspected current-boot kernel error-priority journal had no entries. Evidence
supports CPU/scheduling contention without demonstrating memory exhaustion or
proving one process caused it. Process snapshots show many initializing services;
lifetime-average ps percentages, including observation processes, cannot assign
precise interval CPU cost.

## 8. Assessment and next action

**High-confidence immediate cause:** no qualifying capacity throughout the full
five-minute gate window. Idle and load failed policy throughout; steal frequently
failed too. The gate behaved as configured before later security prestarts and
Compose could execute.

This proves the live refusal path that Phase 3M did not exercise. It does not
validate successful resource-aware cold boot. Natural Jellyfin recovery also
shows broader startup latency; exclusive causation of the earlier Dispatcharr
application failure remains unproven. A longer deadline or relaxed thresholds
is not automatically justified by this result.

**NO-GO for claiming automatic cold-boot recovery or unattended production
readiness.** Any next phase should separately review the natural CPU/load
settling curve and VM/host scheduling before selecting a minimal correction.
Do not relax thresholds simply to obtain a pass. A new controlled start requires
separate authorization.

Leave the protected stack stopped and guard active. No rollback, retry, second
reboot, timeout extension or permanent streaming integration was performed.
Private receipts, raw journals/logs, secrets and recovery contents are excluded
from this report. Existing backup integrity is not a newly proven full restore.

## Appendix — complete admission samples

| Helper elapsed seconds | Idle % | Steal % | Load1 | Qualifying streak |
|---:|---:|---:|---:|---:|
| 5.083 | 0.053 | 31.983 | 37.85 | 0 |
| 10.173 | 0.051 | 38.222 | 39.47 | 0 |
| 15.175 | 0.000 | 24.278 | 38.55 | 0 |
| 20.238 | 0.051 | 25.371 | 38.34 | 0 |
| 25.309 | 0.050 | 24.124 | 37.27 | 0 |
| 30.366 | 0.051 | 36.697 | 39.81 | 0 |
| 35.443 | 0.208 | 38.422 | 39.91 | 0 |
| 40.484 | 0.101 | 40.554 | 38.96 | 0 |
| 45.490 | 0.000 | 17.332 | 39.60 | 0 |
| 50.499 | 0.000 | 19.583 | 39.23 | 0 |
| 55.529 | 0.051 | 19.723 | 38.25 | 0 |
| 60.542 | 0.105 | 31.031 | 38.39 | 0 |
| 65.570 | 0.418 | 31.904 | 39.96 | 0 |
| 70.573 | 0.313 | 31.818 | 39.00 | 0 |
| 75.637 | 0.051 | 36.364 | 37.72 | 0 |
| 80.639 | 0.000 | 15.147 | 36.46 | 0 |
| 85.642 | 0.102 | 20.041 | 35.47 | 0 |
| 90.654 | 0.000 | 15.338 | 35.03 | 0 |
| 95.659 | 0.050 | 18.506 | 33.58 | 0 |
| 100.709 | 0.051 | 30.597 | 33.70 | 0 |
| 105.728 | 0.102 | 40.173 | 33.16 | 0 |
| 110.850 | 0.203 | 28.065 | 33.07 | 0 |
| 115.906 | 0.050 | 27.610 | 32.42 | 0 |
| 120.925 | 0.052 | 22.612 | 32.47 | 0 |
| 125.945 | 0.101 | 16.886 | 32.75 | 0 |
| 130.947 | 0.000 | 14.597 | 31.89 | 0 |
| 135.967 | 0.152 | 22.486 | 34.06 | 0 |
| 140.969 | 0.101 | 25.596 | 34.14 | 0 |
| 146.025 | 0.153 | 31.665 | 36.05 | 0 |
| 151.027 | 0.100 | 16.876 | 35.96 | 0 |
| 156.035 | 0.051 | 18.648 | 36.37 | 0 |
| 161.068 | 0.050 | 15.800 | 35.62 | 0 |
| 166.070 | 0.102 | 19.416 | 36.29 | 0 |
| 171.095 | 0.051 | 22.273 | 39.87 | 0 |
| 176.114 | 0.103 | 29.109 | 40.04 | 0 |
| 181.120 | 0.051 | 17.806 | 39.40 | 0 |
| 186.142 | 0.103 | 23.844 | 38.64 | 0 |
| 191.147 | 0.052 | 23.347 | 38.99 | 0 |
| 196.339 | 0.051 | 18.671 | 40.43 | 0 |
| 201.349 | 0.201 | 36.601 | 40.40 | 0 |
| 206.354 | 0.051 | 35.156 | 42.21 | 0 |
| 211.359 | 0.000 | 19.591 | 41.15 | 0 |
| 216.368 | 0.051 | 15.124 | 40.82 | 0 |
| 221.374 | 0.000 | 22.239 | 39.71 | 0 |
| 226.382 | 0.000 | 21.192 | 38.45 | 0 |
| 231.430 | 0.000 | 14.858 | 36.98 | 0 |
| 236.445 | 0.103 | 28.704 | 36.02 | 0 |
| 241.472 | 0.111 | 51.797 | 35.37 | 0 |
| 246.533 | 0.153 | 19.583 | 35.26 | 0 |
| 251.541 | 0.051 | 18.402 | 34.12 | 0 |
| 256.547 | 0.104 | 42.322 | 33.63 | 0 |
| 261.549 | 0.103 | 29.985 | 38.55 | 0 |
| 266.560 | 0.000 | 21.633 | 37.06 | 0 |
| 271.644 | 0.101 | 27.410 | 35.61 | 0 |
| 276.682 | 0.052 | 38.051 | 36.13 | 0 |
| 281.807 | 0.202 | 16.776 | 34.27 | 0 |
| 286.826 | 0.050 | 18.500 | 33.61 | 0 |
| 291.828 | 0.101 | 7.905 | 31.88 | 0 |
| 296.839 | 0.103 | 27.901 | 31.57 | 0 |
