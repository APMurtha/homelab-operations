# Rivendell load investigation

**The previous load rise is strongly associated with the host-side Docker image
export and its SSH/streamed verification path. Historical metrics show a CPU-heavy
burst, not a sustained disk/NFS stall or a busy Dispatcharr/Jellyfin workload.**
This conclusion uses retained Netdata history from the actual incident, plus one
new 60-second read-only observation. No image verification or application test
was repeated. The exact division between export, parsing, hashing and SSH work
cannot be reconstructed from grouped metrics alone.

Evidence baseline: `eba380cbdd567bde35737ec2c72b06c162404333`.
Target: Rivendell, four vCPUs. NEST's pinned Andrew `andrew-media` / `media`
connection verified host/account access. The requested branch remains
`docs/udm-pro-max-migration-prep`.

## Actual incident correlation

Attempt 2's immutable receipts place verification between **03:22:54 and 03:24:16
UTC on 2026-11-18**, 82 seconds. Load rose from **0.6650 to 5.8716**; RAM stayed
above 3.57 GB. Existing local Netdata retained one-second metrics covering the
interval and surrounding time, so this investigation did not recreate the job.
All successful historical chart timestamps fall inside the requested
03:22:30–03:25:30 window.

The reviewed verifier invokes `docker image save` and streams every image layer
through tar readers, selecting 18 application files for hashing. It does not read
only those 18 files from an already-mounted tree. The retained image's logical
size is 4,249,031,329 bytes. That size is not a measurement of physical disk reads:
cache and layer representation affect actual I/O. The streaming path also uses
the SSH connection and host Python interpreter. No new scan was performed here.

| Historical metric | Before verification | During verification | Shortly afterward |
| --- | ---: | ---: | ---: |
| `dockerd`, average CPU, 100% = one vCPU | 0.60% | **82.12%** | 4.13% |
| `containerd`, same scale | 0.48% | **54.60%** | 3.59% |
| SSH application group, same scale | 0.00% | **66.04%** | 2.37% |

Before/after summaries use 23/34 returned one-second points; the verification
summary uses all 82 points. Application-group CPU counts descendants according to
Netdata grouping, so SSH-group CPU is not proof that encryption alone consumed
that time. The sum of these three groups is **202.76% of one vCPU**, about
**2.03 vCPUs**, during verification. That is approximately **76%** of the VM's
recorded CPU work in that interval; the streams are sampled independently, so the
share is approximate. Netdata defines application CPU as 100% per core in its
[collector documentation](https://learn.netdata.cloud/docs/collecting-metrics/collectors/operating-systems/applications).

Across all four vCPUs, CPU work averaged **66.80%**, peaking at **86.19%** in a
one-second sample. User time averaged **47.01%**, system time **18.43%**, softirq
**1.18%**, nice **0.18%**. Steal averaged **0.68%**, peaking at 4.60%; this does not
support host CPU steal as the primary cause. Runnable tasks averaged **7.39**,
peaking at **21**. This indicates bursts of CPU demand/queueing; it does not mean
the VM was continuously at 100% CPU utilization.

Storage activity increased, but pressure indicators were modest:

- Physical `sda` reads averaged **10.37 MiB/s**, peaking at **16.95 MiB/s**.
- Disk busy time averaged **7.59%**, peaking at **25%** during verification
  (a brief **41%** sample appeared just afterward).
- Read await averaged **0.86 ms**, maximum **2.98 ms**; write-await magnitude
  averaged **0.65 ms**, maximum **8 ms**. These are averages of per-second
  chart values, not a request-weighted 82-second latency calculation.
- The sampled disk queue was at most **1**. Blocked-task magnitude was at most
  **1**, present in only 2 of 82 historical points.
- CPU I/O wait averaged **0.19%**, with an isolated **5.40%** sample.

These observations favor CPU work in image export/stream handling over sustained
block-device saturation. They do not rule out brief I/O stalls. No syscall trace
or per-PID history ties every CPU tick to one command; unrelated concurrent host
activity cannot be categorically excluded. The matching export timeline, large
Docker/SSH CPU increase and subsequent drop make verification the best-supported
primary contributor.

## Application and background-work comparison

Historical container CPU during verification, **100% = one vCPU**:

| Container | Mean CPU |
| --- | ---: |
| dispatcharr | 4.69 |
| rivendell-iptv-vpn | 4.01 |
| rivendell-iptv-relay | 8.80 |
| rivendell-iptv-gateway | 0.35 |
| jellyfin | 0.42 |
| nzbget | 0.06 |
| qbittorrent | 1.38 |
| radarr | 0.40 |
| sonarr | 1.47 |
| chaptarr | 0.47 |
| bazarr | 0.20 |
| prowlarr | 0.16 |

Together these 12 containers averaged **22.42% of one vCPU**, about **5.60% of the
four-vCPU VM**. The four protected services account for about 17.85% of one vCPU.
These measurements do not identify Dispatcharr's PostgreSQL/Redis/Celery workload,
Jellyfin, NZBGet, qBittorrent or the selected *arr services as the primary spike.
Container and process-group values overlap and must not be added together.
Container CPU scaling is documented in Netdata's
[container collector reference](https://learn.netdata.cloud/docs/collecting-metrics/collectors/containers-and-vms/containers).

The historical cron, unattended-upgrades and NFS process groups returned zero CPU
for the interval. Backup-group charts had no usable points and remain **unknown**;
absence of a chart is not proof that no job ran. No private command arguments,
media names or job contents were inspected. Small background monitoring overhead
was present; it does not explain the Docker/SSH burst. No scheduler, backup or
service configuration was changed.

## New bounded observation

Window: **2026-11-18T03:30:23.914757+00:00** to **2026-11-18T03:31:23.912396+00:00**
(59.998 seconds). Thirteen /proc snapshots at approximately
five-second spacing, existing `vmstat` and `iostat`, one `docker stats --no-stream`
call and short process/thread snapshots were used. The first vmstat row is a
since-boot average and is excluded from interval conclusions. No diagnostic
package was installed. Measurements include the collector's own small overhead.

| Live measurement | Result |
| --- | --- |
| CPU user / system / softirq | 4.91% / 2.80% / 0.46% |
| CPU idle / I/O wait / steal | **91.59% / 0.12% / 0.04%** |
| Load start, 1 / 5 / 15 minutes | 0.140 / 0.947 / 1.186 |
| Load end, 1 / 5 / 15 minutes | 0.099 / 0.787 / 1.115 |
| Runnable / blocked /proc task ranges | 1–3 / 0–1 |
| Persistent D-state threads in ps samples | None |
| MemAvailable range | 3,557,711,872–3,587,117,056 bytes |
| Swap configured / swap-in / swap-out | None / 0 / 0 |
| `sda` read / write rate | 80.07 / 54.67 KiB/s |
| `sda` request-weighted await | 0.93 ms |
| `sda` average queue depth / busy time | 0.0134 / 0.47% |
| Peak five-second `sda` busy time | 2.16% |

The single initial /proc blocked-task count of one was not present in the later
ps thread scan; snapshots are not atomic. This is not evidence of a persistent
hung task. vmstat independently sampled runnable counts up to four. No current
CPU, disk or memory-pressure bottleneck was observed. Local `sda`, `sda3` and
`dm-0` statistics describe stacked devices and are not summed as independent I/O.
Disk await/queue calculations follow the kernel's
[disk-statistics field definitions](https://docs.kernel.org/admin-guide/iostats.html).

Highest measured live process CPU (whole-window deltas; 100% = one vCPU):

| Process comm | Container/host | CPU |
| --- | --- | ---: |
| netdata | host | 3.68 |
| dotnet | chaptarr | 3.53 |
| apps.plugin | host | 3.30 |
| python3 | host | 2.00 |
| dockerd | host | 1.15 |
| containerd | host | 0.97 |
| qbittorrent-nox | qbittorrent | 0.42 |
| Sonarr | sonarr | 0.38 |

The host python3 process is consistent with the collector itself and is not
attributed to an application job from its name alone. Redis and Celery inside
Dispatcharr used about 0.30% and 0.18% of one vCPU in the whole-window table.
The separate Docker snapshot reported Dispatcharr 1.14% CPU / 812.6 MiB memory,
relay 8.20% / 33.37 MiB, Jellyfin 0.01% / 376.9 MiB, NZBGet 0.02%, qBittorrent
0.46%, Radarr 0.06%, Sonarr 0.05%. Snapshot CPU and whole-window means are different
measurements. The JSON preserves all 20 running containers' CPU, memory, PID and
block-I/O statistics. Docker block-I/O values are cumulative since container start,
not 60-second traffic rates.

### NFS, ZFS and warnings

`/var/lib/docker` and `/tmp` are **ext4** in this guest; the mount table also
contains six NFS and two NFS4 mounts. During the live window NFS RPC calls increased
by **72** (about 1.2/s), with **zero retransmissions**. No sustained D-state thread,
NFS timeout, filesystem error, block-I/O warning, OOM or hung-task warning appeared
in the bounded kernel-journal query. The query inspected at most the latest 200
kernel entries since 03:20 UTC; this is a limited observation, not complete health
attestation. Raw messages and mount/server paths are not published.

No local ZFS kernel statistics or zpool tool were present. A remote NFS server
could use ZFS, but its storage was not inspected. Low guest I/O wait and rare
blocked tasks argue against an NFS wait storm in the incident; remote storage
health is not established. No media contents or application databases were read.

## Admission recommendation

Linux load includes runnable and uninterruptible tasks and decays over time; it
is not a CPU utilization percentage. See the
[kernel load-average implementation](https://github.com/torvalds/linux/blob/master/kernel/sched/loadavg.c).
On four vCPUs, load ≤ 2 is a deliberately conservative admission ceiling, not the
hardware saturation boundary. It also cannot distinguish CPU queueing from I/O
wait or hypervisor steal.

**Retain the threshold and all current limits for now.** It correctly refused
an attempt immediately after a substantial host workload. The historical CPU work
was roughly 2.67 vCPUs on average; a simultaneous test with a one-vCPU limit could
have left little peak headroom. That simple additive comparison is a risk
illustration, not a performance prediction. Quiet scheduling alone may not solve
the problem because the verification step itself is the likely main contributor.

For a separately reviewed next-attempt procedure, separate expensive image
verification from the one admission decision. After verification exits, use a
fixed, bounded quiet observation/stabilization interval, then evaluate the
**unchanged** gate once. Preserve hash evidence and immutable image identity;
do not silently skip source verification, poll/retry admission indefinitely,
reuse old intent receipts or start a container while a predicate fails. This is a
recommendation only; no new attempt or runner change was made here.

For a later, separately authorized gate improvement, **supplement** load with
multi-sample CPU idle/busy, runnable tasks relative to four vCPUs, steal, CPU/I/O
pressure, disk queue/latency, memory availability and service health. Thresholds
need offline tests and calibration before replacement of the conservative load
predicate. Do not simply raise load from 2 to 4 or treat a single idle reading as
sufficient admission.

## Preservation, evidence and decision

All 33 production container identities, images, start times, restart counts,
health/status and configuration fingerprints matched the preceding checkpoint and
were unchanged across observation. The protected four-service stack and Jellyfin
remained healthy. Network and volume inventories were unchanged. Supplemental
metric queries only read the existing loopback Netdata API; redirects were refused.
An oversized chart catalog was bounded and discarded; subsequent small queries
used exact discovered contexts. No cloud telemetry or provider was contacted.

No container lifecycle operation, image scan/build/pull, process termination,
package installation, production configuration write, systemd/firewall/VPN/DNS
change, application test or playback occurred. No guard, runner or admission
threshold changed.

Sanitized evidence:
`configs/dispatcharr-iptv/hardened-image-integration/rivendell-load-investigation-results.json`
— SHA-256 **`f7193ed9b5ffbf256613da3646cc737194bc6695499cc6f48ac0569cf3ddd382`**. It includes the 60-second measurements, vmstat/iostat,
bounded historical data and summaries, container comparisons and collector hash.
The report excludes its own hash. Missing historical chart series stay marked
unavailable; negative chart writes/blocked values are mirrored display conventions
and their magnitudes are used above.

**Investigation complete. Recommend reviewing the verification/quiet-window
sequence before authorizing another isolated runtime attempt. Image binding and
deployment remain NO-GO because the application matrix is still unexecuted.**
