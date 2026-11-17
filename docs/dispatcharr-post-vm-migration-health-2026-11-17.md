# Dispatcharr — post-VM-migration health check and recovery

2026-11-17 UTC (2026-11-16 US/Eastern). Rivendell, VM 130.

**PASS: one authorized systemd-managed start recovered the protected stack. Dispatcharr is left running.**

## Placement and resources

Andrew confirmed VM 130 remains on Orthanc. The selected Andrew/Rivendell access setup has no authenticated Orthanc profile, so placement is owner-confirmed and host CPU utilization was not independently measured. Guest telemetry was sufficient to proceed.

| Measurement | Failed cold-boot gate mean | Current prestart, three 5-second samples | Final 5-second sample |
|---|---:|---:|---:|
| CPU idle | 0.083% | 98.188%, 94.922%, 97.735% | 96.332% |
| CPU steal | 25.360% | 0%, 0%, 0% | 0% |
| Load1 | 36.796 | 0.06, 0.06, 0.05 | 0.67 |

Final load averages: 0.67 / 0.49 / 1.24. Four guest CPUs remain present. MemAvailable was 4.725 GiB before startup and 3.869 GiB afterward.

The guest now shows substantially less scheduling contention, consistent with the reported removal of two busy VMs from Orthanc. This before/after observation does not isolate causation or validate a new cold boot.

## Prerequisites and the single recovery action

At preflight the stack unit retained its earlier admission failure, and all three dedicated containers were stopped. No active Dispatcharr streaming session could be disrupted by starting these stopped containers.

Read-only input, accepted nftables guard and stopped-topology checks passed. All nine installed persistence/admission files matched reviewed hashes and root-owned 0644 permissions. The private WireGuard configuration remained present; its peer matches the guard policy. The independent secondary-drive checkpoint's three archive hashes passed verification, and existing Rivendell rollback artifacts remained readable.

Issued exactly once:

```sh
sudo -n systemctl start dispatcharr-stack.service
```

The command returned 0. Activation ran approximately 00:38:23–00:39:41 UTC. The unchanged admission gate required idle >=50%, steal <=10%, load1 <4 on four CPUs, for three consecutive five-second samples, within 300 seconds.

| Gate elapsed | Idle | Steal | Load1 | Streak |
|---:|---:|---:|---:|---:|
| 5.001 s | 97.484% | 0% | 0.03 | 1 |
| 10.001 s | 97.487% | 0.050% | 0.03 | 2 |
| 15.002 s | 97.233% | 0.050% | 0.03 | 3 |

**Admission duration: 15.002 seconds.** Native systemd metadata confirms exit 0 for all four prestarts. Installed guard reconciliation ran normally with the accepted policy.

## Final acceptance

Final checks at approximately 00:40:53–00:40:58 UTC passed:

- Dedicated Gluetun/WireGuard, Dispatcharr and gateway containers healthy; container identities, image/configuration fingerprints and restart policies retained. Restart counts remain zero.
- Stack and guard units active/exited, successful; accepted nftables guard and running namespace/topology checks pass. All nine installed hashes remain unchanged.
- VPN default route through tun0, tunnel up, OUTPUT default DROP, Docker embedded-DNS rejection, nameserver 127.0.0.1 and disabled IPv6 verified. A normal HTTPS IP-echo check exits through the VPN and differs from host egress. WireGuard peer matches the guard.
- PostgreSQL query and authenticated Redis PING pass. Both uWSGI workers have fresh Redis-backed heartbeats: ages 0.152/0.839 seconds, TTLs 30/29 seconds. Default and DVR Celery workers both respond.
- Dispatcharr HTTP and gateway health return 200.
- Migration check reports no pending migrations. The existing 184-row migration fingerprint is unchanged. Inspected startup logs contain no migration failures, tracebacks or recurring Redis-reference exception.
- Jellyfin remains Docker-healthy and its health endpoint returns 200. All unrelated container identities, images/configuration fingerprints and start times are unchanged; previously healthy services remain healthy. Existing stopped services remain stopped. Docker process and network identities are unchanged. Services without Docker healthchecks are verified running, not given a new full application certification.

No playback, broadcaster or playlist request was initiated. No restart loop was observed. VPN checks establish normal-path protection; no failure injection or continuous packet capture was performed.

## Limits and final state

No recovery blocker remains. Orthanc host CPU utilization is unavailable; VM placement is owner-confirmed. No reboot, Docker-wide restart, manual container start, second recovery attempt, VM/configuration/image/Compose/firewall-policy/timeout change, or Jellyfin modification occurred.

**Leave Dispatcharr running and stop.** Returning to the patched image, HLS relay and Jellyfin integration remains a separate task.

