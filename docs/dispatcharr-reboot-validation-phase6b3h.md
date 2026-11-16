# Dispatcharr Phase 6B-3H — controlled reboot validation

2026-11-16 UTC. Rivendell VM 130, 10.10.20.30, hosted on Orthanc.
Reviewed installation commit: `0ffb4f06b3df1102d115093b127ff346c041345d`.

**FAIL — automatic application recovery. NO-GO for unattended operation.**
One explicitly authorized Rivendell reboot was executed. Firewall admission and
failure cleanup worked, but Dispatcharr did not become healthy before Compose
rejected its dependency. The configured cleanup stopped only the three dedicated
containers. No manual start, retry, rollback, configuration change or second
reboot was performed.

## 1. Authorization and final pre-reboot baseline

Earlier preflight stopped because Jellyfin session and Proxmox task checks were
inconclusive. The owner subsequently explicitly confirmed no active/paused
Jellyfin playback, no maintenance tasks for VM 130, and authorized one reboot.
Those two clearances are **owner confirmations**, not successful agent API checks.
The owner also confirmed the VM console was open and usable.

The final guest inspection at **18:12:37 UTC** found no material change:

- All seven installed files still matched the reviewed commit and ownership.
- Guard and stack units enabled, active/exited, successful; running-contract
  verifier passed. All dedicated containers healthy, restart policy `no`, zero
  restart counts. Container IDs, image IDs, mounts, policies and networks captured.
- Dedicated namespace tun0 default route, OUTPUT default-drop and embedded-DNS
  rejection remained present. Fresh pinned SSH worked.
- Download clients were rechecked: no download/postprocessing jobs or transfer
  activity. Jellyfin/Proxmox idle status was owner-confirmed as described above.
- Local rollback receipts remained accessible. Independent checkpoint on
  Denethor's secondary NVMe remained accessible, with all three archive hashes
  matching. No new backup or restore was performed.
- Earlier same-boot diagnostics passed PostgreSQL, Redis, both uWSGI heartbeats,
  default/DVR workers, migrations, provider audit and application/gateway HTTP.
  Database baseline: 184 migrations, zero channels and zero EPG sources.

Recovery remains at:

- Denethor: `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`.
- Rivendell installation rollback: `/root/dispatcharr-minimal-recovery-20261116T051539Z`.
- Earlier local checkpoint: `/root/dispatcharr-minimal-recovery-20261116T043509Z`.

## 2. Reboot and observed startup timeline

After checking hostname, old boot ID and the running security contract, the
selected Rivendell root transport issued **`systemctl reboot` once**, at
**18:13:18 UTC**. SSH reset/timeout during shutdown and startup was expected.
The new boot ID proves a new guest boot:

- Before: `867bde8c-d870-4bc7-a758-0529c764b851`.
- After: `1beba908-b22b-4993-88cc-4af1e893dac1`.

Journal times below are seconds from the journal's boot monotonic clock. They
must not be mixed directly with the userspace-relative offsets displayed by
`systemd-analyze critical-chain`. Wall times come from journal/container records.

| Event | Boot monotonic seconds | Evidence / outcome |
|---|---:|---|
| Guard unit begins | 15.633 | systemd journal |
| Input check passes | 16.723 | verifier, mutations 0 |
| Accepted scoped table installed | 18.431 | guard installer |
| Guard verification passes | 19.169 | verifier, mutations 0 |
| Guard unit finishes | 19.329 | success |
| Docker begins | 20.847 | 18:14:53.954 UTC |
| Docker ready | 64.195 | 18:15:37.302 UTC |
| Protected stack begins | 64.211 | automatic systemd dependency |
| Stack input check passes | 65.612 | verifier |
| Scoped table reconciled after Docker | 70.211 | accepted table only |
| Prestart guard/topology check passes | 74.669 | before Compose workload start |
| Dedicated VPN start acknowledged | 99.933 | Compose journal |
| Dedicated VPN healthy | 132.216 | Compose health gate |
| Dispatcharr start acknowledged | 134.819 | 18:16:47.925 UTC |
| Dispatcharr dependency rejected | 438.335 | 18:21:51.441 UTC; unhealthy |
| Compose exits | 438.372 | status 1 |
| Automatic scoped cleanup finishes | 456.495 | all three dedicated containers stopped |
| Stack unit fails | 456.833 | 18:22:09.940 UTC; exit-code |

No manual intervention occurred between these events. The gateway never started
in this boot because application health never passed. Final `critical-chain`
reported approximately 6 minutes 32.6 seconds for the stack unit, including its
failed start and cleanup. The guard unit remains enabled and active/exited;
the stack unit remains enabled but failed. The Docker unit remains running.

## 3. Firewall and VPN evidence

**PASS for observed guard admission order and retained guard integrity.**
The boot journal demonstrates successful guard verification before Docker
startup, and a second reconciliation/prestart check before protected startup.
Protected containers retained `restart=no`. Final input and guard verifiers both
returned success with mutations 0; all seven installed file hashes still match.
No live firewall flush, VPN disconnect, daemon restart or policy redesign occurred.

The dedicated Gluetun started successfully using kernel WireGuard. Its logs show:

- WireGuard setup at approximately 18:16:36 UTC.
- DNS ready with its configured DoT upstream path.
- Public VPN exit **198.44.159.163** at 18:16:46 UTC, matching the accepted exit.
- Successful health probes through 18:22:05 UTC, before automatic termination.
- Clean signal-driven shutdown and exit 0 during scoped failure cleanup.

This is functional tunnel/connectivity evidence; a fresh peer handshake timestamp
was not collected. Gluetun's setup message alone was not treated as proof of a
working tunnel. Its public-IP lookup and continuing health supply that evidence.

No continuous boot packet capture was installed. There is **no proof excluding
every transient direct-WAN packet**, and no deliberate post-boot fail-closed
failure injection was performed. Current accepted input hashes, guard verification,
prestart topology checks and observed tunnel connectivity support the configured
security boundary. Complete post-start application namespace/DNS/IPv6 verification
could not finish because application acceptance failed and cleanup stopped it.
No broadcaster, channel import or playback request was initiated.

## 4. Application failure and database evidence

**FAIL for HTTP/application readiness.** Preserved health records show repeated
**HTTP 502 Bad Gateway**, followed by request/health-command timeouts. Compose
reported `dependency failed to start: container dispatcharr is unhealthy`.
This was an application health-gate failure, not an arbitrary operator timeout or
an unsuccessful VPN initialization.

Observed startup stages:

| Wall time UTC | Application evidence |
|---|---|
| 18:16:45.605 | Container start timestamp |
| 18:17:05.039 | PostgreSQL 17.11 ready to accept connections |
| 18:20:02.986 | Migration command reports **No migrations to apply** |
| 18:20:56.529 | Entrypoint announces uWSGI production startup |
| 18:21:12–13 | uWSGI master, two web workers and HTTP router spawned |
| 18:21:14–15 | Redis and default/DVR Celery processes being spawned |
| 18:21:51.441 | Health dependency rejected |
| 18:21:54.613 | PostgreSQL reports clean database shutdown |

No recurring Redis `NoneType ... exists` exception, application traceback or
migration failure appeared in the inspected application log window. Health-probe
Python tracebacks represent the failed HTTP requests and are distinct from an
application traceback. No unexpected migration was logged. There was no fresh
post-boot SQL catalog comparison, Redis PING, worker heartbeat/ping acceptance or
successful HTTP application response before cleanup; those checks are **not
claimed to pass**. Spawning worker processes is insufficient readiness evidence.

**Phase 6B-3I follow-up:** substantial cold-boot CPU contention is now verified
from historical telemetry; its exclusive causal role remains unproven. See the
[read-only investigation](dispatcharr-boot-failure-investigation-phase6b3i.md).
The measurements available during Phase 6B-3H showed the following: A sample showed CPU pressure `some avg10=93.20`, approximately 40
one-minute load average on four vCPUs, with over 5 GiB available RAM and no
material memory-pressure signal. Database readiness preceded migration completion
by nearly three minutes. Docker all-container listing also exceeded short read
budgets; known-container inspection remained usable. These observations justify
reviewing startup cost/contention and health-check timing, not automatically
increasing deadlines or changing configuration.

## 5. Unrelated service recovery and identity comparison

All 32 recorded container IDs, image IDs and restart policies remained unchanged.
Previously running unrelated containers recovered; previously stopped trial,
Lidarr, Shelfarr and profilarr-parser containers remained stopped. Shelfarr's
retained unhealthy and profilarr-parser's retained starting health labels belong
to stopped pre-existing containers, not newly failed running services.

Final readback at **18:24:16 UTC**:

| Service | Final state |
|---|---|
| Jellyfin | running, healthy; public HTTP returned 200 |
| Original download Gluetun | running, healthy |
| qBittorrent | running, healthy |
| Sonarr, Radarr, Prowlarr | running; no Docker healthcheck configured |
| NZBGet | running; no Docker healthcheck configured |
| Profilarr, deunhealth | running, healthy in final inventory |

Jellyfin temporarily became unhealthy and returned 503 during busy startup, then
recovered automatically. No manual restart or settings change was performed.
Restart counts did not increase; seedboxapi retained its pre-existing count 2.
Unrelated HostConfig fingerprints matched the pre-reboot record.

The **three dedicated containers' HostConfig fingerprints changed** across the
automatic Compose start/stop lifecycle. Their IDs, images, restart policies and
installed input hashes remained unchanged. A raw preboot HostConfig field diff
was not retained, so the changed fields are **unattributed** and require review
before any separately approved recovery; this report does not claim complete
configuration identity for those three runtime records.

All user-defined Docker network IDs, including `rivendell-iptv-egress`, remained
unchanged. Docker's built-in `bridge` network ID changed during daemon boot;
that is recorded separately from user-defined network recreation. SSH remained
available for final evidence collection. Final process inspection found no
FFmpeg or FFprobe processes. Jellyfin briefly ran FFmpeg during its own startup;
no playback was initiated by this validation.

## 6. Warnings and limitations

- Docker logged canceled image-resolution/snapshot queries while bounded
  all-container observations timed out. These are not evidence that pinned images
  changed; image IDs did not change. No image was pulled by this procedure.
- Gluetun logged an optional version-information lookup failure and fell back
  from ICMP raw-socket health probes to DNS/UDP probes due to restricted
  capabilities. Health continued succeeding; capabilities were not broadened.
- Redis logged overcommit and unauthenticated-local-client warnings. No sysctl,
  authentication or network change was made. Redis was not readiness-certified
  in this boot before the automatic cleanup.
- The original accepted image remains deployed; the custom readiness test image
  was not substituted. No relay trial deployment or permanent Jellyfin
  integration was introduced.

## 7. Final state and recommendation

**Automatic boot recovery: FAIL. Guard ordering/integrity: PASS for the observed
checks. Unattended production readiness: NO-GO.**

The three dedicated containers are stopped, their data and images retained.
`dispatcharr-stack.service` is failed and enabled, without a restart loop.
`dispatcharr-egress-guard.service` is enabled and active/exited; scoped protection
remains installed. Docker, SSH and unrelated running media services recovered.
No rollback was executed and no security rules were removed.

Preserved evidence is in Git-ignored `.ai-local/dispatcharr-phase6b3h/`: final
preflight/job receipts, the single reboot receipt, successive observations, boot
journal/dependency captures, sanitized failure diagnostics, container inventories,
final health and final contracts. Recovery archives and their contents are not
part of this document or Git publication.

Next action requires separate approval: review cold-start application timing,
resource contention, the health gate and dedicated HostConfig differences; then
propose a single scoped recovery/validation step. Do not start the stack, extend
timeouts, modify worker initialization or reboot again automatically. Broader
backup restore rehearsal, monitoring and permanent Jellyfin integration remain
separate production-readiness work.

## 8. Read-only Phase 6B-3I follow-up

The [subsequent investigation](dispatcharr-boot-failure-investigation-phase6b3i.md)
preserved the boot journals, bounded logs/health records and historical telemetry
without restarting anything. It confirms internal Nginx returned 502 because the
uWSGI Unix socket was not accepting connections. PostgreSQL was already ready.
Migrations had nothing to apply, and collectstatic copied zero files. Web workers
and attached Redis/Celery processes appeared only shortly before health rejection;
full readiness was never demonstrated.

The installed health policy is **180 seconds start period, 30 seconds interval,
10 seconds command timeout, three retries**, with a five-second HTTP request
timeout. Three counted probes ended at 18:20:29 (502), 18:21:10 (health timeout)
and 18:21:51 UTC (request timeout). This explains rejection approximately 306
seconds after container start; it was not a single five-minute timer or the
540-second systemd timeout. The fatal Compose result was unhealthy dependency.

Sixty-two approximately five-second Netdata points over 18:16:45–18:21:50 UTC
show mean inferred idle 0.107%, mean steal 25.808% and mean one-minute load
42.283 on four vCPUs. CPU scheduling contention is measured; its precise host
source and whether the app would eventually recover remain unproven. Memory/OOM
and sustained guest-disk saturation are not supported as the first failure.

Docker's event cache had already evicted boot start/stop events by the later
capture (earliest retained event 18:24:08 UTC); journals and inspect/log records
supply those timings. Current readback still shows the three dedicated containers
stopped, guard active and verified, unrelated services recovered, and no media
processes or restart loop. No configuration, timeout, Redis, database, firewall,
VPN or service change was made. Recovery remains separately authorized; an
unchanged-configuration start under settled resource conditions is the recommended
next diagnostic control, not an already implemented fix.
