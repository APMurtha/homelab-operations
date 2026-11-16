# Dispatcharr Phase 6B-3I — failed boot recovery investigation

2026-11-16 UTC. Rivendell VM 130, 10.10.20.30. **Read-only investigation;
no recovery attempted.** This follows the [Phase 6B-3H reboot report](dispatcharr-reboot-validation-phase6b3h.md).

**Finding:** application initialization did not finish before Docker's health
policy rejected Dispatcharr. Internal Nginx returned 502 because the uWSGI Unix
socket was not accepting connections; later probes timed out while workers were
still initializing. Severe CPU scheduling contention is measured, not merely
suspected. It is a strong contributor, but the evidence does not prove that the
application would eventually have become healthy. No timeout, worker, Redis,
image, firewall or VPN change is justified automatically.

## 1. Evidence and limits

Preserved locally under Git-ignored `.ai-local/dispatcharr-phase6b3i/`, directory
mode 0700 and evidence files mode 0600:

- Current-boot systemd/Docker/containerd and kernel journals; unit results.
- Bounded timestamped application, VPN and Jellyfin logs; Docker health records.
- Docker event-cache readback, container identity/limits/mounts and creation times.
- Existing Netdata historical CPU/load/RAM/disk charts, sysstat records, and the
  earlier Phase 6B-3H pressure/process samples.
- Static startup scripts and uWSGI configuration read from the stopped pinned
  container, without executing application code. A SHA-256 evidence manifest
  records the local files. No database or Redis command was executed.

Only sanitized reports are approved for Git publication. Raw evidence, static
source captures, credentials and recovery contents are excluded.

**Event retention limitation:** Docker returned its bounded 256-event cache.
Its earliest surviving event was **18:24:08.776 UTC**, after cleanup. The boot's
start/health/stop events had already been evicted. They cannot be claimed as
preserved Docker events; the journal, timestamped logs and inspect records supply
that chronology instead. Available application logs cover initialization through
clean shutdown and did not hit the requested 4,000-line limit.

All table times below are UTC. Guest timezone is Etc/UTC; application log text
uses America/New_York. Docker's outer timestamps are used to avoid mixing those
zones. Some uWSGI inner timestamps precede their outer emission timestamps, so
subsecond application-stage timing is not claimed. Journal monotonic ordering
is retained independently in Phase 6B-3H.

## 2. Timestamped failure timeline

| UTC | Evidence / event |
|---|---|
| 18:13:18 | One authorized Rivendell reboot requested |
| approximately 18:14:33 | Boot origin inferred from journal monotonic/wall correlation; sysstat separately records a restart marker at 18:14:48 |
| 18:14:52.276 | Guard verification passes, boot +19.169 seconds |
| 18:14:53.954 | Docker service begins, after guard verification |
| 18:15:00.018–18:15:29.529 | Sixteen unrelated containers start during Docker restore |
| 18:15:37.302 | Docker service ready |
| 18:15:43.318 | Accepted scoped table reconciled after Docker |
| 18:15:47.776 | Protected prestart topology/guard verification passes |
| 18:16:09.733 | Dedicated VPN container start timestamp |
| 18:16:36.151 | WireGuard setup logged; DNS ready immediately afterward |
| 18:16:45.322 | Compose reports dedicated VPN healthy |
| 18:16:45.605 | Dispatcharr container starts; no recreation |
| 18:16:46.475 | Gluetun reports accepted VPN exit 198.44.159.163 |
| 18:16:52.817 | Original Dispatcharr 0.33.0 entrypoint running |
| 18:17:02.198 | PostgreSQL startup announced |
| 18:17:05.039 | PostgreSQL ready to accept connections |
| 18:17:23.112 | Internal Nginx startup announced |
| 18:17:30.018 | First preserved Nginx 502-path error: connection refused at `/app/uwsgi.sock` |
| 18:18–18:20 | Further local health requests encounter the same missing/not-listening uWSGI socket |
| 18:20:02.986 | Migration command reports **No migrations to apply** |
| 18:20:53.355 | collectstatic: 0 copied, 242 unmodified |
| 18:20:56.529 | uWSGI production launch announced |
| 18:21:12–13 | uWSGI master, two web workers and HTTP router spawn records emitted |
| 18:21:14.990 | Redis attached-daemon spawn logged |
| 18:21:15 | Default/DVR Celery and other attached-daemon spawns logged; no confirmed worker-ready response |
| 18:21:51.137 | Third counted post-grace health probe completes unsuccessfully |
| 18:21:51.441 | Compose rejects unhealthy Dispatcharr dependency |
| 18:21:51.478 | systemd records main process exit 1 |
| 18:21:52–18:22:09 | Configured ExecStopPost stops gateway, application, then VPN |
| 18:21:54.613 | PostgreSQL clean shutdown logged |
| 18:22:09.940 | Stack unit records failed/exit-code |

The container was created at **05:15:56 UTC**, during the prior installation;
it was started, not recreated, during this reboot. Dedicated VPN/gateway creation
times are also before reboot, and all three IDs/image IDs are retained.

**First failing dependency:** Dispatcharr's HTTP readiness, specifically internal
Nginx → uWSGI. Firewall admission and VPN health had passed. PostgreSQL was
responsive in about three seconds after its startup announcement. Neither the
external Caddy gateway nor the HLS relay was handling these health requests;
the gateway never started and the accepted base has no active trial relay.

## 3. What actually expired

Installed Docker health policy:

```text
GET http://127.0.0.1:9191/ through the application's internal Nginx
Python HTTP timeout: 5 seconds
Docker health-command timeout: 10 seconds
start_period: 180 seconds
interval: 30 seconds
retries: 3
```

The endpoint/port matches the previously healthy accepted deployment. A 502 is
not a successful readiness response and must not be accepted merely because
Nginx is running.

| Counted post-grace probe | End UTC | Result |
|---|---|---|
| 18:20:22.417 | 18:20:29.045 | HTTP 502 Bad Gateway |
| 18:20:59.052 | 18:21:10.311 | Docker health command exceeded 10-second timeout |
| 18:21:40.352 | 18:21:51.137 | HTTP request timed out |

Earlier 502 probes occurred within the start period. Probe duration and subsequent
intervals explain why rejection occurred about **306 seconds after the container
start**, rather than at exactly 180 seconds. This is not a configured single
five-minute readiness timer.

The reviewed Compose command includes `--wait-timeout 360`, and systemd has
`TimeoutStartSec=540`. The observed fatal message is **unhealthy dependency**,
not a systemd timeout; unit Result is `exit-code`, not `timeout`. Raising only
the systemd timeout would not change the failing Docker health policy.

## 4. Resource measurements

Existing Netdata history was analyzed over **18:16:45–18:21:50 UTC**: 62 points,
roughly five-second averages, spanning application start through rejection.
These are aggregate guest measurements, not individual worker profiles.

| Measurement | Window mean | Maximum / supporting observation |
|---|---:|---|
| Inferred idle CPU | 0.107% | Sum of exported non-idle dimensions subtracted from 100 |
| CPU steal | 25.808% | 48.555% |
| User CPU | 54.392% | 71.492% |
| System CPU | 17.959% | 23.560% |
| One-minute load | 42.283 | 49.410 on four vCPUs |
| CPU iowait | 0.038% | 0.204% |
| Guest virtual disk utilization | approximately 16.4% | 35.3% |
| Guest disk read await | approximately 2.7 ms | 12.5 ms |
| Guest disk write await magnitude | approximately 5.7 ms | 32.1 ms |

Write-await chart values are plotted negative by the telemetry representation;
positive magnitudes are reported, not physically negative latency. Disk queries
use a slightly different sampling grid, so these are descriptive window
statistics, not request-level correlations.

The Phase 6B-3H snapshot independently measured CPU pressure `some avg10=93.20`,
load about 40 and over 5 GiB MemAvailable. Historical free RAM stayed above about
1.3 GiB, excluding reclaimable cache. The inspected kernel journal contains no
OOM-kill evidence; Docker records `OOMKilled=false`. No evidence supports memory
exhaustion as the first failure. Guest disk results do not support sustained
virtual-disk saturation, although Orthanc's physical storage latency was not
measured and cannot be ruled out completely.

**CPU contention is verified.** Steal time supports hypervisor scheduling
contention, but no Orthanc process/other-VM measurement was available to identify
its source. Sixteen concurrent unrelated container starts are verified. Their
individual CPU contribution, and whether Dispatcharr hit its own two-CPU quota,
were not measured. Its memory cap is 3 GiB; stopped cgroups no longer provide a
live CPU-throttling counter. These limits were not changed.

Sysstat was also preserved. The first query used application-local clock hours;
those records predated reboot and were excluded from boot conclusions. An
explicit UTC query identifies the restart and a coarse 18:20–18:30 aggregate.
That interval includes recovery after cleanup and is not substituted for the
five-second Netdata startup history. The sysstat file header retains the earlier
kernel version; current-boot journal/source inspection confirms the new kernel.

## 5. Readiness diagnosis and confidence

| Explanation | Assessment |
|---|---|
| Application did not initialize before health rejection | **Confirmed, high confidence.** No successful HTTP/WSGI readiness; late worker spawn and repeated 502/timeouts |
| Severe CPU scheduling contention contributed | **Strongly supported, moderate-to-high causal confidence.** Near-zero idle, high load/steal, slow sequential initialization; not an isolated A/B proof |
| Application was healthy but falsely rejected | **Not supported.** No HTTP 200 or worker readiness before cleanup |
| Application would become healthy with more time | **Unverified.** Termination prevented observing eventual readiness |
| PostgreSQL delay/failure was the primary blocker | **Not supported.** Ready promptly; migration command finished without pending migrations |
| Redis startup race/stale singleton caused this failure | **Unproven.** No recurring NoneType/exists error or exhausted Redis retry sequence in captured logs; no post-boot authenticated PING/worker heartbeat proof |
| Wrong health endpoint or external gateway failure | **Not supported.** Local internal-Nginx endpoint is correct; Caddy was gated off |
| OOM or sustained guest disk saturation | **Not supported by available measurements** |

The pinned entrypoint runs database setup, then Nginx, migration checking and
static collection **before** starting uWSGI. Much of the delay therefore preceded
web-worker creation: Nginx→migration completion took about 160 seconds, then
static collection another 50 seconds. The latter copied no new files; this
was not bulk static-file transfer or new database initialization.

In AIO mode Redis/Celery are uWSGI-attached daemons. `lazy-apps=true` means a
spawned web worker still has Django application initialization to perform.
The image contains an exec-pre Redis helper, but textual configuration order is
not proof of the runtime order or successful Redis readiness. That helper also
flushes Redis when actually executed; it was **read only, never executed** during
this investigation. The earlier Phase 5 Redis recovery lesson remains relevant,
but does not justify diagnosing or resetting Redis from this boot's evidence.

## 6. Failure handling and retained state

Fresh readback at **18:37:23 UTC** confirms:

- All three dedicated containers remain stopped; their restart counts remain 0.
- Stack unit failed/exit-code; no automatic restart loop or manual retry.
- Guard unit enabled, active/exited, successful. Fresh input and guard verifiers
  pass with mutations 0. Accepted security files and installed unit hashes match.
- Cleanup used Compose **stop**, not down/volume removal. The application `/data`
  bind and every inspected dedicated bind source remain present; PostgreSQL
  logged clean shutdown. This proves retention, not a fresh database-integrity
  or restore test. No database was opened or modified by this investigation.
- Jellyfin, original Gluetun and qBittorrent are healthy; Sonarr, Radarr, Prowlarr
  and NZBGet remain running without configured Docker healthchecks. All sixteen
  previously running unrelated containers recovered; previously stopped ones
  remained stopped. No FFmpeg/FFprobe processes remain.

No firewall, routing, DNS, VPN, capability or gateway change was made, and no
new direct-WAN path was introduced by this investigation. The protected workload
has no running processes. There is no continuous boot packet capture, so absence
of every transient unauthorized packet remains unproven. User-defined network
IDs are retained; Docker's built-in bridge ID changed at boot as recorded in 3H.
The three dedicated runtime HostConfig fingerprint differences recorded in 3H
remain unattributed; they are not established as the readiness cause.

## 7. Ranked recommendation and recovery boundary

1. **Recommended next step: one separately authorized unchanged-configuration
   start after host load has settled**, through the existing guarded stack unit,
   with the same health policy and per-stage/resource capture. This is a scoped
   diagnostic recovery, not a permanent fix. It separates boot contention from
   an application initialization fault without changing security or deadlines.
   No such start was performed here.
2. If that succeeds, evaluate the smallest supported startup sequencing/resource
   adjustment in the existing minimal design against measured cold-start cost.
   A Docker service dependency alone does not mean its unrelated applications
   have finished booting. Do not introduce another controller or assume a fixed
   arbitrary delay is sufficient. No exact permanent sequencing change is yet
   proven necessary or sufficient.
3. Consider adjusting Docker's **start period**, rather than accepting 502 or
   merely increasing the systemd timeout, only after a bounded test establishes
   eventual full readiness and a defensible initialization budget. This remains
   an unvalidated candidate, not the selected correction.
4. Investigate Redis/worker initialization only if a subsequent capture shows
   actual Redis errors or persistent unready workers under settled resources.
   Worker reduction, quota changes or image patching are higher-risk hypotheses;
   no support exists for deploying them now.

No permanent correction is sufficiently proven for implementation from this
single interrupted cold-start record. The safest immediate choice is to preserve
the protected stopped state and obtain explicit approval for the bounded control
above. Do not silently turn a readiness diagnostic into an indefinite startup.

Existing Phase 6B-3F/3G checkpoints and scoped rollback instructions remain the
recovery basis; no new archive or restore was needed. A future guarded start's
failure should retain the existing scoped stop behavior. Installation rollback,
DB/Redis reset, repeated reboot, broad Docker recovery and unrelated-service
changes require separate authorization. **NO-GO for unattended production;
await recovery authorization.**
