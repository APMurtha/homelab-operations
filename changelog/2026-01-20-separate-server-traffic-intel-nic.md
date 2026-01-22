# 2026-01-20 — Separate Server Traffic Using Dedicated Intel NIC

## Date
2026-01-20

## Description
Installed an Intel i350-T2 network interface and resegmented server traffic to use dedicated physical interfaces. Server VLAN traffic was migrated off the onboard management interface to improve isolation between the management plane and workload traffic.

## Reason for Change
The homelab had outgrown a single-NIC design. Management traffic and server workload traffic were sharing the same physical interface, increasing blast radius and making troubleshooting more difficult.

Introducing a dedicated Intel NIC for server traffic provides:
- Clear separation between management and workload planes
- Improved reliability under load
- A network layout that more closely mirrors small-enterprise design patterns

## Impact Assessment
- Brief network disruption during interface reassignment
- Temporary loss of connectivity to server VLANs during cutover
- No impact to firewall routing, VLAN IDs, or IP addressing
- Management access remained available throughout the change

## Rollback Considerations
If issues were encountered:
- Reassign server VLANs back to the original onboard interface
- Restore previous Proxmox bridge-to-interface mappings
- No firewall or IP configuration changes would require rollback

## Outcome
- Server VLAN traffic successfully migrated to Intel i350-T2 interfaces
- Management traffic remains isolated on a separate physical interface
- No post-change instability observed
- Documentation updated to reflect current NIC configuration
