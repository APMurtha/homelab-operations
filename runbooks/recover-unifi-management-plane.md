# 🛠️ Recover UniFi Switch and APs After Management Plane Loss

## Purpose

This runbook documents the **safe recovery procedure** for a UniFi switch and
associated access points after loss of management-plane connectivity.

It is intended to be used when:
- the UniFi switch becomes unreachable by the controller
- devices enter reprovision or adoption loops
- management IP addressing becomes inconsistent or unexpected

This procedure is derived from a real incident and reflects a **known-good
recovery path**.

---

## Scope

Applies to environments where:
- UniFi is used for switching and wireless only
- OPNsense (or another firewall) provides routing, DHCP, and NAT
- Management traffic is intentionally untagged
- VLAN traffic is isolated to a dedicated trunk or LAGG

---

## Symptoms

Initiate this runbook if one or more of the following are observed:

- UniFi switch appears offline in the controller
- Switch or APs repeatedly reprovision
- Devices fall back to default IP addressing
- Controller loses visibility during provisioning
- Network changes cause immediate loss of management access

---

## Preconditions

Before beginning recovery:

- Physical access to the UniFi switch is available
- Controller host (VM/LXC) access is available
- Firewall configuration is reachable and stable
- MGMT network is confirmed untagged on the firewall interface

---

## Recovery Procedure

### 1. Isolate the Controller

- Disconnect the UniFi Network Controller host from the network **or**
- Stop the UniFi Network Controller service

This prevents incomplete or incorrect configurations from being re-applied
during recovery.

---

### 2. Factory Reset the UniFi Switch

- Perform a full factory reset using the physical reset button
- Wait for the switch to fully reboot

Do **not** reconnect it to trunked or VLAN-carrying ports yet.

---

### 3. Restore Minimal Connectivity

- Connect the switch to the firewall **management uplink only**
- Ensure this port:
  - carries untagged MGMT
  - blocks all tagged VLANs
  - is not part of a LAGG

Verify the switch receives a valid MGMT IP address.

---

### 4. Start the Controller and Adopt the Switch

- Start or reconnect the UniFi Network Controller
- Adopt the switch
- Wait for adoption to complete and status to stabilize

Do **not** apply VLANs, trunks, or profiles yet.

---

### 5. Apply Management-Safe Port Profile

- Assign the dedicated MGMT uplink port profile to the firewall-facing port
- Confirm no tagged VLANs are permitted on this link

Reconfirm switch reachability after the change.

---

### 6. Recreate the VLAN Trunk / LAGG

- Configure the LAGG ports on the switch
- Apply the VLAN trunk port profile
- Verify LAGG status on both switch and firewall

At this point, VLAN traffic may safely resume.

---

### 7. Re-Adopt Access Points

- Apply the AP trunk profile to AP-facing ports
- Confirm:
  - untagged MGMT is present
  - only required VLANs are tagged
- Re-adopt APs if necessary

Wait for all APs to reach a stable, connected state.

---

### 8. Final Validation

Confirm the following before closing recovery:

- Switch remains online and stable
- APs remain adopted
- Clients receive correct VLAN IPs
- No reprovision loops are occurring
- Management access persists across configuration changes

---

## Post-Recovery Actions

- Review recent configuration changes
- Update documentation if behavior differed from expectations
- Reference related incident and changelog entries
- Avoid additional changes until stability is confirmed

---

## Related Documentation

- `docs/network.md` — Authoritative network architecture
- `incidents/2026-02-08-unifi-management-plane-instability.md`
- `changelog/2026-02-08-migrate-switch-tplink-to-unifi.md`

---

## Status

Validated. This procedure has successfully restored management-plane
connectivity and stability.
