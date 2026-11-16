# Dispatcharr Phase 6B-3M — controlled managed restart

2026-11-16 UTC. Rivendell (`10.10.20.30`). **PASS: one authorized scoped
systemd stop/start cycle completed; the protected stack is left running.**
GO for a separately authorized controlled cold-boot validation, not a claim that
cold boot or unattended production operation is already validated.

References: [installation](dispatcharr-boot-admission-installation-phase6b3l.md),
[admission design and offline tests](dispatcharr-boot-admission-phase6b3k.md),
[previous recovery](dispatcharr-controlled-recovery-phase6b3j.md).
Installation report commit at task start:
`d6378945b84c1a45fafaa9b458f46fb4d3c52dbd`.

## 1. Preflight baseline

Read-only preflight at 20:17:37 UTC passed before either lifecycle operation:

- All three dedicated containers healthy; both persistence units enabled,
  active/exited, Result=success; Docker running.
- Authenticated Redis PING passed. Read-only inspection found zero
  `live:channel:*` keys, zero active stream clients and no FFmpeg/FFprobe
  processes. No playback was initiated or stopped by this task.
- Original seven persistence files unchanged; the two admission files match
  the reviewed versions. All nine ownership/mode checks pass (root:root 0644).
- Admission helper SHA-256:
  `649c5dcee6fff563bf7ee80d62d77d42e8c942e8a6a1205eeb4a2a570be2f917`.
- Admission drop-in SHA-256:
  `72643075862dfeb6ce968997edd19c9fbff30eea025d7ea74eb6691d372f8ceb`.
- Base stack unit SHA-256:
  `30e7f5e64b7a6ce3f8ec3cf80572d74bb2dd1ed67083929276cf55fbb65c357e`.
- Accepted guard, VPN route, DNS and IPv6 checks passed. Fresh pinned SSH and
  administrative access worked. Effective prestart commands matched the review.
- Initial three-second host sample: idle 84.140%, steal 2.003%, load1 1.43.
- Existing independent checkpoint on Denethor's secondary NVMe at
  `/mnt/data/Backups/Rivendell/dispatcharr-checkpoints/20261116T043321Z`
  remained accessible; all three recorded archive hashes matched.
- Rivendell rollback files at
  `/root/dispatcharr-minimal-recovery-20261116T051539Z` remained accessible
  with matching recorded hashes. Existing scoped rollback instructions available.
  No new backup, archive, restore or checkpoint was made.

Container identities, images, HostConfig fingerprints, restart policies, start
times, networks and unrelated service states were captured before the stop.

## 2. Exactly one managed stop and start

The only lifecycle requests were:

```sh
sudo systemctl stop --no-block dispatcharr-stack.service
sudo systemctl start --no-block dispatcharr-stack.service
```

Each was issued once, with exclusive local intent receipts and read-only polling.
The start followed confirmation of the stopped state and surviving protections.
No direct Docker restart, worker signal, retry or timeout override was used.

| UTC | Observed systemd / Compose event |
|---|---|
| 20:18:59.481 | Stack stopping |
| 20:19:00.512 | Gateway stopped; application stopping |
| 20:19:05.862 | Application stopped; dedicated VPN stopping |
| 20:19:06.514 | Dedicated VPN stopped |
| 20:19:06.800 | Stack stopped successfully |
| 20:20:21.253 | Stack starting |
| 20:22:09.092 | Stack finished successfully |

Between stop and start, all three dedicated containers were confirmed exited.
The guard remained active and its exact-policy verifier passed. All unrelated
container identities/configurations/start times, Docker process identity and
Docker network identities were unchanged. Persistent data and networks were kept.

## 3. Admission telemetry and execution ordering

The installed helper read actual `/proc/stat` and `/proc/loadavg` on four CPUs.
Policy remained: idle >=50%, steal <=10%, load1 <4, three consecutive qualifying
five-second samples, maximum wait 300 seconds. No contention was generated.

| UTC | Elapsed seconds | Idle % | Steal % | Load1 | Qualifying streak |
|---|---:|---:|---:|---:|---:|
| 20:20:26.580 | 5.005 | 75.543 | 8.641 | 2.73 | 1 |
| 20:20:31.582 | 10.008 | 76.981 | 7.474 | 2.59 | 2 |
| 20:20:36.583 | 15.009 | 81.782 | 8.218 | 3.02 | 3 |

`capacity_ready` occurred at elapsed 15.009 seconds. Native systemd execution
metadata confirms the admission helper exited normally with **status 0**; the
log message alone was not treated as proof of success.

| UTC | Ordered stage | Result |
|---|---|---|
| 20:20:21.412 | Existing input verification | PASS |
| 20:20:21.575–20:20:36.583 | Resource admission | Exit 0 after streak 3 |
| 20:20:36.902 | Accepted scoped firewall reconciliation | Completed |
| 20:20:37.552 | Existing security/topology prestart verification | PASS |
| 20:20:38.978 | First protected container start: dedicated VPN | After all prestarts |
| 20:22:09.060 | Existing running-contract verification | PASS |

All four ExecStartPre commands had nonignored successful exits. The original
Compose startup, health dependencies and scoped failure cleanup were preserved.
Normal unit startup reapplied only the accepted `rivendell_iptv` table; policy
was not changed and no manual firewall modification was performed.

**Admission refusal was not exercised live.** The unchanged source, installed
hashes, nonignored ExecStartPre failure semantics and Phase 3K offline tests
support startup refusal before Compose if admission fails. This successful run
does not provide a new live refusal/cleanup test. No thresholds were bypassed.

## 4. Application startup and readiness

| UTC | Application milestone |
|---|---|
| 20:20:39.032 | Dedicated VPN container StartedAt |
| 20:20:45.501 | Compose observes VPN healthy; application starts next |
| 20:20:45.537 | Dispatcharr container StartedAt |
| 20:20:47.838 | PostgreSQL ready |
| 20:20:56.755 | Migration check: no pending migrations |
| 20:21:06.542–06.544 | uWSGI master 270, web workers 273/274, HTTP router 275 |
| 20:21:22.453 / 20:21:26.055 | WSGI applications ready in workers 274 / 273 |
| 20:21:36.287 | Compose first records application healthy |
| 20:21:36.294 | Gateway start requested after application health |
| 20:21:51.037 / 20:21:52.123 | Default / DVR Celery ready |
| 20:22:08.233 | Gateway healthy |
| 20:22:09.092 | Managed activation complete |

Full unit activation took **107.836 seconds**, including admission. Compose
recorded application health by **50.750 seconds after application container
start**. This is a health-observation bound, not an exact first HTTP probe or
playable-media timing. Docker's recent health ring had already evicted the
initial successful probe when evidence was collected. Its earliest retained
success was later and must not be described as the first success.

Post-start acceptance passed:

- PostgreSQL connectivity and authenticated Redis PING.
- Both web workers had fresh Redis-backed heartbeats: ages 0.624 / 0.279 seconds,
  TTLs 29 / 30 seconds. Process topology matched the expected master and router.
- Validated application diagnostics: environment, migrations and default/DVR
  worker checks all exit 0; HTTP health 200; gateway HTTP health 200.
- Read-only migration fingerprint unchanged:
  `b00f51e91c5b882cd84d3b2579d074ca`, 184 migration rows.
- Read-only provider audit passed: zero channels and EPG sources; only expected
  built-in account/profile records. No new source or credential imported.
- No recurring Redis-reference exception, application traceback or migration
  failure found in the inspected startup logs. No orphan FFmpeg/FFprobe process
  or dedicated-container restart loop observed.

## 5. Resource measurements

Existing host telemetry supplied 54 approximately two-second aggregated points
across the whole activation, 20:20:21–20:22:09 UTC:

| Metric | Mean | Peak / other bound |
|---|---:|---:|
| CPU idle, inferred from other CPU dimensions | 42.811% | — |
| CPU steal | 13.835% | 59.756% |
| CPU user / system | 20.966% / 12.830% | — |
| I/O wait | 0.224% | 1.370% |
| Load1 | 3.723 | 7.552 |
| Host RAM used | 3049.105 MiB | 3581.348 MiB |

Minimum free RAM was 379.254 MiB with mean cached RAM 3783.885 MiB;
free RAM is not MemAvailable. These are host measurements, not application-only
resource attribution. CPU availability deteriorated after admission while
startup still succeeded. The gate admits a momentary qualifying condition; it
neither reserves CPU nor continuously enforces thresholds. This warm managed
restart cannot establish cold-boot reliability or exclusive CPU causation of the
previous failure; caches and concurrent workload conditions differ.

## 6. Security verification

Before stop, while stopped and after startup, the accepted guard verifier passed.
Final inspection confirmed the exact 17-rule `inet rivendell_iptv` policy and
expected dedicated network/namespace topology. Application and gateway share the
dedicated VPN namespace; the existing gateway LAN restriction remains intact.

Normal-path checks confirmed tun0/default routing, kill-switch OUTPUT DROP,
Docker embedded-DNS rejection, application nameserver directives to 127.0.0.1,
and disabled IPv6. The dedicated VPN exit check returned 198.44.159.163,
different from the host's ordinary exit. Gluetun was healthy with WireGuard
initialization and functional VPN egress. No fresh peer handshake timestamp was
captured; connectivity is supported by those observations instead.

No direct-WAN fallback was observed in these supported checks. No VPN-loss test,
firewall flush, continuous packet capture or deliberate DNS/IPv6 failure was
performed. Therefore this is normal-path verification, not exhaustive proof of
absence of transient exposure under every failure or privileged host action.
No broadcaster, playlist or live-stream request was initiated. No trial relay
was started; the accepted base deployment does not require an active HLS relay.

## 7. Identities and unrelated services

| Dedicated container | Container ID before and after | Final state |
|---|---|---|
| rivendell-iptv-vpn | `1b9d20c93194` | Healthy |
| dispatcharr | `d34275eddd72` | Healthy |
| rivendell-iptv-gateway | `03ec8c82417e` | Healthy |

All three retained their complete IDs, image IDs, HostConfig fingerprints and
restart=no policies; only expected start timestamps changed. RestartCount
remained zero. The accepted original Dispatcharr 0.33.0 image remained in use;
no patched trial image was deployed. No container was recreated.

All unrelated container identities, image/configuration fingerprints and start
times remained unchanged. Jellyfin, original download Gluetun and qBittorrent
remained healthy; Sonarr, Radarr, Prowlarr and NZBGet remained running (no Docker
healthcheck for those four). Existing stopped Shelfarr and profilarr-parser
conditions were preserved, not newly diagnosed or repaired. Docker's process,
start identity and network identities were unchanged. SSH remained available.
No Jellyfin, user, library or tuner configuration was changed.

## 8. Final state, evidence and next step

Final read-only verification at **20:29:17 UTC** passed: all three dedicated
containers healthy, all nine installed hashes/permissions unchanged, both units
enabled and successful, accepted guard and running-contract checks pass, and
unrelated identities remain unchanged. No host reboot occurred.

Private evidence retains preflight/stop/start receipts, journal realtime and
monotonic timestamps, Docker observations, sanitized backend acceptance and
resource summaries. The bounded Docker event cache had evicted events before
20:21:36.552; earlier ordering is supported by the retained systemd journal,
stopped-state receipt and container inspect timestamps. Raw receipts, logs,
recovery archives and credentials are excluded from publication.

No failure required rollback or repeat startup. Existing scoped rollback assets
remain available; the installed design was not rolled back. No configuration,
image, timeout, threshold, network or unrelated-service changes were made.

**Recommendation: PASS managed restart; GO for separately authorized controlled
cold-boot validation.** Before that test, repeat job/playback clearance, security
and recovery preflight and confirm usable console access. Obtain explicit reboot
authorization. Cold-boot admission under actual startup contention, refusal under
persistent resource pressure and broader unattended-production recovery remain
unproven by this run. Stop here with the protected stack running.
