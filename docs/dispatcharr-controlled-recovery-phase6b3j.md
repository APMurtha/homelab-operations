# Dispatcharr Phase 6B-3J — controlled recovery start

2026-11-16 UTC. Rivendell, 10.10.20.30. References:
[reboot validation](dispatcharr-reboot-validation-phase6b3h.md) and
[boot failure investigation](dispatcharr-boot-failure-investigation-phase6b3i.md).

**PASS — one unchanged-configuration start and all acceptance checks succeeded.**
The protected stack is left running. This demonstrates recovery under settled
pre-start conditions; it does not reverse the failed cold-boot result or certify
unattended reboot readiness.

## 1. Authorization, scope and preflight

Exactly one `systemctl start --no-block dispatcharr-stack.service` request was
issued, at **18:53:39 UTC**. The nonblocking flag changes only how the caller
waits; the installed oneshot executed its existing Compose command, health gates,
360-second Compose wait option and 540-second systemd startup timeout unchanged.
No reset-failed, restart, second start, worker signal or manual Redis reset was
issued. A local exclusive intent receipt prevents silently retrying this run.

Before startup:

- The three dedicated containers were stopped with restart policy `no`; Docker
  and the guard unit were active. The stack retained its prior failed state.
- All seven installed persistence files matched the reviewed versions and root
  ownership/permissions. Input, guard and prestart verifiers passed, mutations 0.
- Docker dependencies and installed unit were inspected. No file, image, timeout,
  network, gateway, VPN or capability setting was changed.
- Rivendell's installation rollback files remained present and were fingerprinted.
  The independent Denethor secondary-NVMe checkpoint remained accessible and all
  three existing archive SHA-256 values matched. No new backup was created.
- All containers, image IDs, HostConfig fingerprints, restart policies/counts,
  health, start times, network IDs and Docker process identity were captured.
  CPU/memory/pressure and process-name snapshots were recorded privately.

The initial ten-second CPU sample showed 64.4% idle but 17.5% steal, so no start
was issued then. Three bounded follow-up samples at 18:52:19–18:52:39 showed
**89.0–91.6% idle, 1.7–3.4% steal and load1 0.52–0.61**. They met the chosen
conservative comparison criteria: idle at least 50%, steal at most 10%, load1
below four. A final three-second check immediately before starting measured
**95.63% idle and 0.42% steal**. Available RAM was approximately 4.95 GiB.

These were observations, not resource-policy adjustments. No infrastructure was
started until the bounded follow-up established suitable conditions.

## 2. Observed startup timeline

Times use UTC outer log timestamps; inner application timestamps use a different
zone and may be buffered. PostgreSQL's own UTC readiness line is identified.

| UTC | Observed milestone |
|---|---|
| 18:53:39.738 | Stack unit begins its one authorized start |
| 18:53:39.834 | Installed input verifier passes |
| 18:53:40.710 | Existing ExecStartPre reapplies only the accepted scoped guard |
| 18:53:41.007 | Prestart guard/topology verifier passes |
| 18:53:43.381 | Dedicated VPN container starts |
| 18:53:48.408 | WireGuard setup completes |
| 18:53:50.391 | Gluetun reports accepted public VPN exit 198.44.159.163 |
| 18:53:50.475 | Compose reports VPN healthy, before starting application |
| 18:53:50.621 | Dispatcharr container starts |
| 18:53:54.128 | PostgreSQL 17.11 ready to accept connections |
| 18:53:56.585 | Internal Nginx starts |
| 18:54:07.895 | Migration command: **No migrations to apply** |
| 18:54:14.008 | Static collection: 0 copied, 242 unmodified |
| 18:54:16.257 | uWSGI production launch announced |
| 18:54:19.870–19.878 | Master, two web workers and HTTP router spawn |
| 18:54:20.403 | Redis attached daemon spawn logged |
| 18:54:45.557 / 18:54:49.971 | Both WSGI applications report ready |
| 18:55:02.452 | First preserved successful application health probe completes |
| 18:55:02.671 | Compose reports application healthy |
| 18:55:02.757 | Gateway starts automatically after application health |
| 18:55:04.110 | DVR Celery worker ready log |
| 18:55:10.642 | Default Celery worker ready log |
| 18:55:33.924 | First new-start gateway health probe succeeds |
| 18:55:34.636 | Installed running-contract verifier passes |
| 18:55:34.664 | Stack unit finishes successfully, active/exited |

**Unit activation duration: 114.926 seconds**, from systemd monotonic inactive-exit
to active-enter. **Application start to first successful recorded HTTP health:
71.831 seconds.** The gateway's approximately 31-second start-to-health interval
includes its existing health-check scheduling; it is not measured stream latency.
Early unsuccessful application probes remained within the unchanged grace period.
No playback was requested.

The guard reapplication above is the existing unit's required admission step,
not a separate manual firewall operation or policy change. Its accepted semantics
were verified before and after startup.

## 3. Application and database acceptance

The previously validated diagnostic ran with the application's generated
environment as UID/GID 1000, without changing its logic:

| Check | Result |
|---|---|
| Generated application environment | PASS |
| PostgreSQL read-only SQL connectivity | PASS; expected database and role |
| Pending migrations | None; validated management command exits 0 |
| Migration catalog | 184 entries; fingerprint matches pre-reboot baseline |
| Redis PING | PASS |
| Two uWSGI web workers | PASS; container PIDs 277/278, common master 274 |
| Redis-backed worker heartbeats | PASS; ages 0.047/0.889 seconds, TTLs 30/29 seconds |
| Default and DVR Celery ping | Both expected workers respond |
| Application HTTP | 200 |
| Gateway HTTP health | 200 |
| Read-only provider audit | PASS; built-in account/profile only |
| Channels / EPG sources | 0 / 0 |
| Recurring Redis NoneType/exists errors, application tracebacks, migration failures | None in inspected current-start logs |
| FFmpeg/FFprobe in application | None |

Worker PIDs are historical evidence, not future signal instructions. Fresh
Redis-backed heartbeats and authenticated-context diagnostics establish more
than container-running or open-port status. No database records were edited by
the checks. Normal AIO initialization used the existing image and entrypoint;
no standalone Redis-reset helper or worker-recovery script was executed.

## 4. Resource comparison and hypothesis

Existing Netdata history was captured without creating a monitoring service.
The recovery application's start-to-first-success interval has 72 approximately
one-second points (18:53:51–18:55:02). The failed boot interval uses the previously
preserved 62 approximately five-second points (18:16:45–18:21:50).

| Guest measurement | Failed boot | Controlled recovery |
|---|---:|---:|
| Mean inferred idle CPU | 0.107% | 31.165% |
| Mean steal | 25.808% | 14.805% |
| Mean load1 | 42.283 | 1.968 |
| Maximum load1 | 49.410 | 4.254 |
| Mean iowait | 0.038% | 0.109% |
| Application outcome | Unhealthy at about 306 seconds | HTTP health success at 71.831 seconds |

Steal rose again during application initialization, with a short exported peak
of 54.4%. The host was therefore not contention-free throughout the run. Peaks
are not directly comparable across different averaging resolutions. Crucially,
the recovery retained substantial mean idle capacity and much lower guest load.
The successful run does not establish a universal safe steal threshold.
Guest RAM-used telemetry averaged about 2.92 GiB and peaked at 3.33 GiB, with
about 3.58 GiB cached; these are VM-wide values, not application-only RSS.

**The cold-boot contention hypothesis is supported, with moderate causal
confidence.** The unchanged image, data, security controls and health policy
succeeded when the unrelated cold-start storm was absent. PostgreSQL, migrations,
static collection and WSGI initialization progressed much faster. This weakens
the hypothesis of a permanently broken database, image or health endpoint.

This was sequential, not controlled isolation of one variable. Filesystem caches
were warmer, hypervisor scheduling varied, and the compared outcome windows have
different lengths and sampling resolutions. No Orthanc workload was measured or
changed. The result does not prove CPU contention was the sole cause, eliminate
every possible startup race, or justify a timeout increase without further review.

## 5. Security, identities and unrelated services

- Gluetun, Dispatcharr and gateway all healthy; original container IDs and pinned
  image IDs retained. Dedicated restart counts remain 0.
- Input, scoped guard and running-contract verifiers pass. Installed files match
  the reviewed versions. Namespace/bridge, mounts, capabilities and sole intended
  published gateway listener satisfy the existing contract.
- tun0 is up with the intended VPN default path. Namespace OUTPUT remains
  default-drop; embedded Docker DNS is explicitly rejected. Application resolver
  directives are exactly 127.0.0.1 and namespace IPv6 remains disabled.
- A normal HTTPS IP-echo request from the application namespace reports
  **198.44.159.163**, different from the host's normal exit. No IPTV endpoint was
  requested. Gluetun health and its own public-IP log independently support
  functional WireGuard connectivity; no peer-private material was exposed.
- Gateway health returns 200. Accepted gateway filtering/access configuration
  remains unchanged. Synthetic streaming/redirect fixtures and a destructive
  VPN-loss test were not rerun; no new packet-level fail-closed proof is claimed.
- All unrelated container IDs, image IDs, HostConfig fingerprints, running state,
  start times and healthy baselines match pre-start. Docker process identity and
  all network IDs remain unchanged. Jellyfin, original Gluetun and qBittorrent
  remain healthy; NZBGet, Sonarr, Radarr and Prowlarr remain running.
- No unrelated container was recreated/restarted, and no restart loop was found.
  No host reboot, Docker-wide restart, Jellyfin change or playback occurred.

The normal approved VPN path and guard are verified. There was no direct-WAN
fallback introduced by this start; exhaustive absence of every transient packet
is not established without continuous packet evidence/failure injection.

## 6. Final state, evidence and recommendation

**Current controlled-recovery result: PASS. Leave the protected stack running.**
Both oneshot units are enabled and active/exited with success; Docker remains
active/running. No rollback or automatic failure cleanup was invoked in this run.
The existing failure cleanup remains configured, unchanged, for a failed start.
Recovery artifacts and rollback instructions remain available.

Private evidence is retained under Git-ignored `.ai-local/dispatcharr-phase6b3j/`:
preflight, bounded CPU samples, exclusive start intent/receipt, status observations,
validated acceptance results, startup journal/logs/events and resource analysis.
The bounded Docker event cache begins at 18:53:49.818 UTC; the journal and
inspect records supply the earlier prestart/VPN-start chronology.
Only this sanitized report is published. No credentials, raw private logs,
checkpoint contents or database data are committed.

Do not treat this as repaired cold-boot persistence. The earlier boot failure
remains unresolved for unattended operation. Use these measurements to review
whether a minimal supported startup/resource sequencing adjustment is warranted;
any configuration change or another reboot test requires separate authorization.
No further recovery, permanent streaming integration or Jellyfin work is begun.
