# Migrate switch from TP-Link to UniFi

## Summary

Replaced the existing TP-Link managed switch with a UniFi USW-24-G2 to improve
management visibility, VLAN consistency, and operational stability.

This change also introduced a UniFi Network Controller into the environment,
operating in controller-only mode alongside an existing OPNsense firewall.

---

## Reason for Change

The TP-Link TL-SG108E provided basic VLAN functionality but lacked:

- centralized management and visibility
- tight integration with wireless infrastructure
- clear safeguards around management-plane configuration

As the network grew in complexity (multiple VLANs, UniFi APs, LAGG uplinks),
these limitations increased operational risk.

---

## Change Description

- Removed TP-Link TL-SG108E from the network
- Installed UniFi USW-24-G2 as the primary Layer 2 switch
- Deployed UniFi Network Controller in an LXC container on Proxmox
- Established a dedicated, untagged management network
- Migrated all VLAN traffic to a dedicated LAGG between switch and firewall
- Standardized switch behavior using explicit UniFi port profiles

Routing, DHCP, firewalling, and NAT remained handled exclusively by OPNsense.

---

## Impact

- Temporary management-plane instability during initial migration
- Required factory resets and controller isolation to recover
- Resulted in a more stable and predictable network architecture once corrected

No data loss occurred.

---

## Resulting State

- Management network is untagged and isolated
- VLANs traverse only a dedicated LAGG
- Router uplink is not a trunk
- UniFi is used strictly for switching and wireless management
- Architecture documented in `docs/network.md`

---

## Rollback Considerations

Rollback would require reinstalling the TP-Link switch and reapplying VLAN
configuration manually via its web interface.

Given the improved stability and visibility of the UniFi-based design,
rollback is not planned.
