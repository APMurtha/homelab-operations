# 2026-02-08 — UniFi Management Plane Instability During Switch Migration

## Summary

During migration from a TP-Link managed switch to a UniFi USW-24-G2, the network
experienced management-plane instability resulting in loss of switch and access
point connectivity to the UniFi Network Controller.

Recovery required multiple corrective actions before a stable configuration was
achieved.

---

## Impact

- Loss of management access to the UniFi switch
- UniFi access points entered adoption or provisioning loops
- Temporary disruption to client connectivity
- Manual intervention required to restore stable operation

No data loss occurred.

---

## Timeline

- **T0:** TP-Link switch removed and UniFi USW-24-G2 introduced
- **T+N minutes:** Switch provisioned with initial VLAN and trunk configuration
- **T+N minutes:** UniFi devices began reprovisioning repeatedly
- **T+N minutes:** Switch and APs lost connectivity to the controller
- **Recovery:** Switch factory reset, controller isolated, and configuration
  rebuilt incrementally

---

## Detection

The issue was detected through:
- Loss of UniFi controller visibility
- Devices falling back to default provisioning behavior
- Unexpected management IP assignment
- Repeated provisioning attempts observed in the controller

---

## Root Cause

The instability was caused by **management VLAN misconfiguration during initial
switch provisioning**.

Specifically:
- Management traffic was unintentionally placed on tagged VLANs
- The router uplink was treated as a trunk
- VLAN and management-plane traffic were not sufficiently isolated

This resulted in the switch losing controller connectivity mid-provision,
triggering reprovision loops and management-plane collapse.

---

## Resolution

- Factory reset the UniFi switch
- Isolated the UniFi controller during initial provisioning
- Established an untagged management network
- Restricted VLAN traffic to a dedicated LAGG between switch and firewall
- Implemented explicit UniFi port profiles to enforce correct behavior
- Re-adopted access points after management stability was confirmed

---

## Preventive Actions

- Documented authoritative network architecture in `docs/network.md`
- Formalized UniFi port profile usage and failure modes
- Ensured the router uplink is never treated as a trunk
- Limited VLAN carriage to a dedicated LAGG only
- Added change and incident documentation for future reference

---

## Lessons Learned

- Management-plane traffic must be isolated from experimental VLAN changes
- UniFi reprovisioning can amplify small configuration errors into outages
- Incremental provisioning and controller isolation reduce recovery time
- Explicit documentation is a critical stability control

---

## Status

Resolved. Network has remained stable following corrective actions.
