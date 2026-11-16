# Rivendell cold-boot CPU investigation — Mordor

2026-11-16. **Interim findings: guest evidence confirmed; current hypervisor
attribution blocked pending authenticated Bag-End-to-node access.** No cluster comparison
has been executed from Denethor, Ithilien or a hypervisor agent. No Dispatcharr
recovery, VM operation, CPU change, package installation or reboot in this task.

See [access plan](mordor-proxmox-access-plan.md),
[Phase 3N cold-boot evidence](dispatcharr-cold-boot-validation-phase6b3n.md),
[Phase 3M managed restart](dispatcharr-managed-restart-phase6b3m.md).

## Confirmed guest observations from the completed boot trial

These measurements were collected in Phase 3N, not newly measured on Bag-End.

| Observation | Evidence / conclusion |
|---|---|
| Guard complete before Docker | Boot 22.430 seconds versus Docker start 23.503 seconds |
| Docker initialization | Ready at boot 82.176 seconds, about 58.674 seconds after service start |
| Admission | Begins boot 86.024 seconds / 20:40:19 UTC; refuses at elapsed 300.004 seconds / 20:45:19 UTC |
| Samples | 59 real five-second CPU/load samples; maximum qualifying streak 0 |
| CPU idle | Mean 0.083%, maximum 0.418% |
| Guest CPU steal | Mean 25.360%, maximum 51.797% |
| Load1 | Mean 36.796, range 31.57–42.21, on four guest vCPUs |
| Dispatcharr workload | Never starts during this boot; all three dedicated containers remain stopped |
| Guest memory | MemAvailable about 5.83 GiB at 20:41:40 and 4.77 GiB at 20:46:11; no swap configured |
| Other application | Jellyfin completes its startup at 20:47:01, later returns 200/healthy without intervention |

This was admission refusal under real contention, not a PostgreSQL/Redis/uWSGI
health failure during that boot. Dispatcharr could not be the producer of this
boot's contention because admission prevented it from running. Existing guest
startup processes were observed, but lifetime-average ps CPU percentages do not
attribute interval consumption or identify a runaway process reliably.

For comparison, Phase 3M's warm managed start admitted in 15.009 seconds and
completed in 107.836 seconds. Its initial qualifying samples had 75.543–81.782%
idle and 7.474–8.641% steal; later steal still rose. A gate is not a CPU
reservation. Different boot phases, cache state and neighboring work prevent a
controlled causal comparison between the two trials.

## Historical node information — not current cluster inventory

The November 8 owner-run console evidence in
the existing local `docs/rivendell-cpu-compatibility.md` historical report reported Intel
Core i7-4790S on all three nodes, four physical cores/eight logical CPUs, and
three-node Mordor quorum. It reported differing Proxmox/QEMU versions across
Orthanc and its peers. Those versions, topology, current online CPUs and quorum
must be rechecked; historical values are not silently reused as live facts.

That earlier VM CPU-model recommendation addressed missing instruction-set
features. It does not diagnose scheduling contention. Current VM 130 CPU model,
sockets/cores, cpulimit, cpuunits, affinity, QEMU cgroup throttling and other
current allocations remain unverified at the hypervisor layer.

A later Bag-End creation task records Cirith-Ungol/Dol-Guldur near 1–2% sampled
CPU with one small K3s VM each before Bag-End creation. Bag-End was then placed
on Cirith-Ungol. These are separate historical snapshots, not evidence that
peers are currently idle or that migration would be safe.

## Ranked assessment

| Hypothesis | Current support | Missing evidence |
|---|---|---|
| Hypervisor scheduling contention | Guest steal is substantial and directly supports denied guest CPU time under the virtualization layer | Orthanc host CPU/PSI/runqueue, QEMU/cgroup throttling, competing workloads during the same window |
| Rivendell startup workload saturation | Almost zero guest idle and high load; many unrelated applications initializing; delayed Jellyfin startup | Interval guest per-process/cgroup CPU, runnable versus I/O-wait tasks, simultaneous host samples |
| Orthanc allocation oversubscription | Plausible, not established by steal alone | Actual running VM/LXC vCPU allocations, physical versus SMT topology, cpulimits/weights and utilization |
| Specific excessive VM/LXC | No offender established | Per-guest/QEMU CPU time deltas and task correlation on Orthanc |
| Storage/backup activity | Not established; available guest memory does not rule out I/O stalls | Current/recent tasks, node iowait/IO PSI, device latency and ZFS activity |
| Guest memory exhaustion | Current observations do not support exhaustion at the sampled times | Full interval memory-pressure/OOM history if needed; no blanket absence-of-OOM claim |

The first two explanations may coexist. Neither proves which physical host
process consumed CPU, nor whether an explicit cap/weight or SMT placement
contributed. High load can include blocked tasks and is not a CPU percentage.
Historical degradation of Orthanc's legacy `moria` pool must not be used as
proof of present storage-induced CPU contention or conflated with Moria UNAS.

## Bounded Bag-End-side evidence plan

Use Bag-End's existing terminal and actual authorized node identities after the
[access discovery collector](../configs/proxmox/bag-end-access-discovery.py).
No SSH server on Bag-End, new management VM or hypervisor agent is required.

Collect comparable UTC-stamped snapshots from Orthanc, Cirith-Ungol and
Dol-Guldur. Prefer existing historical telemetry covering **2026-11-16
20:39–20:48 UTC**; current quiet samples cannot reconstruct the failed interval.
Record clock offsets and sampling resolution; do not correlate timestamps as
exact if those are unknown.

| Layer | Read-only evidence |
|---|---|
| Identity / versions | Verified hostname/account, installed PVE/kernel/QEMU versions, cluster membership/quorum |
| Physical CPU | lscpu topology/online CPUs, sockets/cores/SMT; CPU-frequency data if readable |
| Host CPU | Two bounded /proc/stat and QEMU CPU-time samples; load, /proc/pressure/cpu, existing node RRD CPU/iowait |
| Allocation | Running and stopped VM/LXC distinction, vCPU counts, cpulimit/cpuunits/affinity; sum allocations separately from measured utilization |
| VM 130 | Filtered CPU config/current status, actual QEMU PID tied to VMID, cgroup CPU quota/weight/throttling and allowed CPUs |
| Workload attribution | Per-QEMU/LXC interval CPU, host task state and named job ownership; avoid full arguments containing secrets |
| Operations | Active/recent backup, snapshot, migration, replication and storage jobs; bounded timestamps and statuses |
| Storage | Existing node disk/RRD metrics, IO PSI, pool status and already-running scrub/resilver evidence; no new scan or test |

PSI provides CPU/memory/I/O stall measurements at host and cgroup levels;
use it to distinguish resource pressure rather than interpreting load alone.
No monitor/trigger registration is needed. [Kernel PSI documentation](https://docs.kernel.org/accounting/psi.html).

Use installed tools only. Missing protected reads should be recorded, not solved
with broad sudo or privilege escalation. Do not run load generators, benchmarks,
scrubs, SMART tests or new playback. If historical metrics are absent, explicitly
state that contemporary samples cannot establish historical attribution; another
reboot is not authorized to fill the gap.

## Smallest corrective-action decision, pending evidence

1. Establish and verify existing Bag-End-to-node read access first; do not change
   the working firewall, gate thresholds, Dispatcharr or VM topology meanwhile.
2. If one scheduled task is proven to overlap and dominate contention, propose a
   narrowly scoped scheduling change with its owner and rollback, not an assumed
   cluster-wide redesign.
3. If VM 130 quota/affinity is the demonstrated bottleneck, propose only that
   correction after validating available host capacity and impact on neighbors.
4. If guest startup work dominates with host capacity available, propose measured
   sequencing of the identified work. Do not disable unrelated services blindly.
5. Review redistribution/capacity only if host oversubscription is demonstrated;
   no migration, resizing, node upgrade or additional infrastructure is approved.

**No corrective implementation is recommended as established yet.** The current
minimum justified action is access discovery and historical host correlation.
Changing the five-minute deadline or lowering thresholds would change admission
policy without resolving its demonstrated resource condition.

## Completion status and remaining blocker

Bag-End address/account and local public fingerprint are owner-confirmed. The
current Codex session has no Bag-End SSH endpoint or direct Samwise messaging
connection. The owner has now supplied Bag-End collector output timestamped
21:22:46 UTC: TCP 22 and 8006 connect on all three nodes; no selected SSH files
or loaded agent identities are reported. No authentication was attempted.
This removes a basic reachability concern but does not identify CPU causes.
The owner reports a new account needs creating. The access plan now contains a
reviewable API-only audit-account proposal; it has not been provisioned.

Until that happens: current node versions, ACLs, cluster health, VM/LXC allocation,
active tasks, CPU pressure and all three-node comparisons are **unverified**.
These reports are prepared evidence and a handoff, not completed live cluster
diagnostics. No new accounts, access permissions or corrective actions are
authorized by publication. Preserve the stopped, guarded Dispatcharr state.
