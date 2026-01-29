# 🌐 Network Architecture & Operations

## 1. Purpose & Scope

This document describes the **design, implementation, and operation** of the homelab network.
The environment is intentionally designed to simulate **real-world Linux network administration** tasks, including segmentation, firewall policy design, DNS enforcement, monitoring, and change management.

This documentation is maintained as a **living document** and evolves alongside the network.

---

## 2. Design Goals

- Enforce clear **network segmentation** to reduce blast radius
- Apply **least-privilege** traffic policies
- Centralize DNS resolution and logging
- Support observability through monitoring and telemetry
- Maintain stability during incremental changes
- Enable safe experimentation via isolated lab networks
- Use tools and patterns relevant to small enterprise environments

---

## 3. Physical & Platform Architecture

### Firewall / Router

- **Software:** OPNsense
- **Device:** Protectli Vault FW4C
- **Hostname:** `anduin`
- **Role:**
  - Inter-VLAN routing
  - Firewall policy enforcement
  - DHCP (selected VLANs)
- **Notes:**
  No non-essential services are run on the firewall.

---

### Switching

- **Device:** TP-Link TL-SG108E (8-port managed switch)
- **Hostname:** `osgiliath`
- **Role:**
  - Layer 2 switching
  - 802.1Q VLAN tagging
- **Management:** Web UI

---

### Wireless Access

- **Device:** UniFi U7 Pro
- **Hostname:** `ithil`
- **Management:** UniFi Controller (`lothlorien`)
- **Mode:** Access Point (no routing)
- **Role:**
  - Wireless access only
  - VLAN-aware SSIDs
  - All routing and firewalling handled upstream by `anduin`

---

### Virtualization Platform

- **Platform:** Proxmox VE
- **Hostname:** `orthanc`
- **NIC Configuration:**
  - Multiple physical NICs
  - Dedicated interfaces used for management and server traffic
  - Intel i350-T2 interfaces carry server VLAN traffic
  - VLAN trunking handled at the switch and hypervisor layers
- **Role:**
  - Hosts Linux VMs and containers
  - VLAN awareness handled at the hypervisor level

---

## 4. Logical Network Architecture

The network is segmented using VLANs to separate **management, servers, clients, IoT, lab, and guest traffic**.
All routing and policy enforcement occurs on `anduin` (OPNsense).

VLAN tagging is applied consistently across:
- The managed switch
- The Proxmox virtualization layer
- Firewall interfaces

There is **no flat network**.

---

## 5. IP Addressing & VLAN Plan

### Base Address Space

- **RFC1918 Range:** `10.10.0.0/16`

### VLAN Summary

| VLAN ID | Name        | Subnet          | Purpose |
|-------:|-------------|------------------|--------|
| 10 | MGMT        | 10.10.10.0/24 | Network and infrastructure management |
| 20 | SERVERS     | 10.10.20.0/24 | Core infrastructure and application services |
| 30 | CLIENTS     | 10.10.30.0/24 | Trusted user devices |
| 40 | LAB         | 10.10.40.0/24 | Testing and experimental systems |
| 50 | IOT         | 10.10.50.0/24 | General IoT devices |
| 60 | GUEST       | 10.10.60.0/24 | Internet-only guest access |
| 70 | APPLE_IOT   | 10.10.70.0/24 | Apple ecosystem devices requiring mDNS |

---

## 6. VLAN Details

### VLAN 10 — Management (MGMT)

- **Gateway:** `10.10.10.1`
- **Addressing:** Static only
- **Systems:**
  - `anduin` (OPNsense management)
  - `orthanc` (Proxmox host)
  - `osgiliath` (switch management)
  - `ithil` (UniFi wireless access point management)
- **Access:** Restricted via explicit firewall rules

---

### VLAN 20 — Servers

- **Gateway:** `10.10.20.1`
- **Addressing:** Static only
- **Systems:**
  - `palantir` (Pi-hole + Unbound DNS)
  - `rivendell` (Docker / media services)
  - `minas-tirith` (monitoring & telemetry)
  - `lothlorien` (UniFi Controller)
  - `elessar` (Authentication & Access Gateway)

---

### VLAN 30 — Clients

- **Gateway:** `10.10.30.1`
- **Addressing:** DHCP (OPNsense)
- **SSID:** Valinor
- **Systems:**
  - Desktops
  - Laptops
  - Mobile devices

---

### VLAN 40 — Lab

- **Gateway:** `10.10.40.1`
- **Addressing:** DHCP (OPNsense)
- **SSID:** Isengard
- **Purpose:**
  - Service testing
  - Failure simulations
  - Experimental configurations
- **Status:**
  Trunking and routing verified end-to-end.

---

### VLAN 50 — IoT

- **Gateway:** `10.10.50.1`
- **Addressing:** DHCP (OPNsense)
- **SSID:** Gondolin
- **Systems:**
  - Smart TVs
  - Network-connected appliances
- **Trust Level:** Untrusted

---

### VLAN 60 — Guest

- **Gateway:** `10.10.60.1`
- **Addressing:** DHCP (OPNsense)
- **SSID:** Bree
- **Access:** Internet only

---

### VLAN 70 — Apple IoT

- **Gateway:** `10.10.70.1`
- **Addressing:** DHCP (OPNsense)
- **SSID:** Lorien
- **Systems:**
  - Apple TVs
  - HomePods
- **Notes:**
  Selective mDNS reflection is enabled to support Apple service discovery while maintaining VLAN isolation.

---

## 7. DNS & DHCP Architecture

### DNS
- **Primary Resolver:** Pi-hole (`palantir`)
- **Secondary Resolver:** Pi-hole (`bombadil`) — out-of-band continuity
- **Upstream:** Unbound
- **Policy:**
  - All VLANs are forced to use internal DNS
  - Direct external DNS is blocked by firewall rules

> **Verification:**
> DNS egress filtering is enforced at the firewall. Client attempts to resolve
> domains via external resolvers (e.g., `1.1.1.1`) time out, confirming that
> all DNS traffic is forced through internal resolvers.

---

### DHCP

- **Provided by:** OPNsense (`anduin`)
- **Enabled on:**
  - VLAN 30 (CLIENTS)
  - VLAN 40 (LAB)
  - VLAN 50 (IOT)
  - VLAN 60 (GUEST)
  - VLAN 70 (APPLE_IOT)
- **Disabled on:**
  - VLAN 10 (MGMT)
  - VLAN 20 (SERVERS)

---

## 8. Firewall Policy Philosophy

### Default Policy

- **Inter-VLAN traffic:** Deny by default
- **WAN inbound:** Deny all
- **WAN outbound:** Explicit allow by role

### High-Level Allowed Flows

- CLIENTS → DNS (Pi-hole only)
- CLIENTS → Media services
- IOT / APPLE_IOT → Internet (DNS, NTP, required service ports only)
- MGMT → Infrastructure administration
- SERVERS → Required outbound services only

Selective multicast and mDNS reflection are enabled **only where required** to support Apple device discovery without compromising isolation.

---

## 9. Change Management

All significant network changes are documented in the `changelog/` directory and include:

- Date
- Description
- Reason for change
- Impact assessment
- Rollback considerations

This mirrors formal change management practices used in production environments.

---

## 10. Future Enhancements

- Expanded alerting and dashboards
- Configuration automation (Ansible)
- Centralized authentication services
- Further reduction of temporary access exceptions

---

## Appendix A: Wireless SSID Lore (Optional)

SSID theming is applied **only at the wireless layer** to provide intuitive context for users without affecting operational clarity.

| SSID      | Lore Blurb |
|-----------|------------|
| Valinor   | The Blessed Realm — calm, orderly, and meant for everyday life. |
| Isengard  | A place of industry and experiment, where new things are forged. |
| Gondolin  | Hidden and protected, kept safe from the wider world. |
| Bree      | A crossroads for travelers — welcoming, but not to be trusted. |
| Lorien    | Fair, quiet, and carefully guarded; harmony through careful design. |

---

*Last updated: Maintained continuously*
