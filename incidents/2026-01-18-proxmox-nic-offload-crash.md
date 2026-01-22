# 2026-01-18 — Proxmox Network Hang Due to NIC Offload Issue

## Summary
The primary Proxmox host (`orthanc`) experienced a network hang during a large file transfer to a ZFS-backed dataset. The system became unreachable over the network and required a hard reboot to recover.

## Impact
- Loss of network connectivity to the Proxmox host
- All hosted services temporarily unavailable
- Manual intervention required to restore service

## Timeline
- **T0:** Large file transfer initiated to server storage
- **T+N minutes:** Network connectivity degraded, then dropped entirely
- **T+N minutes:** Proxmox host became unreachable via SSH and web UI
- **Recovery:** Hard reboot performed via physical access

## Detection
The issue was detected by loss of SSH connectivity and inability to reach hosted services. No prior alerts were triggered due to the sudden nature of the failure.

## Root Cause
The crash was traced to the onboard NIC using the `e1000e` driver with hardware offloading features enabled. Under sustained network load, the NIC driver entered a faulty state, causing a total network hang.

## Resolution
- Disabled NIC offloading features (TSO, GSO, GRO, LRO) on the affected interface
- Implemented a persistent systemd service to ensure offloads remain disabled across reboots
- Verified network stability under subsequent file transfer tests

## Preventive Actions
- Migrated server VLAN traffic to dedicated Intel i350-T2 interfaces
- Reduced reliance on onboard NIC for high-throughput workloads
- Documented NIC configuration and incident details

## Lessons Learned
- Hardware offloading features can introduce instability on certain NIC/driver combinations
- Network hangs can masquerade as storage or application issues
- Proactive separation of management and workload traffic improves fault isolation

## Status
Resolved. No recurrence observed after mitigation.
