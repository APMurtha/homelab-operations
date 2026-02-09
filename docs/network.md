# 🌐 Network Architecture & Operations

## 1. Purpose & Scope

This document describes the **design, implementation, and operation** of the homelab network.
The environment is intentionally designed to simulate **real-world Linux and network
administration** practices, including segmentation, firewall policy design, DNS enforcement,
monitoring, and disciplined change management.

This documentation reflects the **authoritative, known-good state** of the network.

---

## 2. Design Goals

- Enforce clear **network segmentation** to reduce blast radius
- Apply **least-privilege** traffic policies
- Maintain a stable and isolated **management plane**
- Centralize DNS resolution and logging
- Support observability and troubleshooting
- Enable safe experimentation via isolated lab networks
- Mirror small-enterprise operational patterns

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

- **Device:** UniFi USW-24-G2
- **Role:**
  - Layer 2 switching
  - 802.1Q VLAN tagging
  - LACP aggregation
- **Management:** UniFi Network Controller

---

### Wireless Access

- **Device:** UniFi Access Point
- **Hostname:** `ithil`
- **Management:** UniFi Network Controller (`lothlorien`)
- **Mode:** Access Point (no routing)
- **Role:**
  - VLAN-aware wireless access
  - All routing and firewalling handled upstream by `anduin`

---

### Network Controller

- **Software:** UniFi Network Controller
- **Hostname:** `lothlorien`
- **Platform:** LXC container on Proxmox
- **Role:**  
  Switch and access point management only

UniFi gateways are **not** used.

---

### Virtualization Platform

- **Platform:** Proxmox VE
- **Hostname:** `orthanc`
- **NIC Configuration:**
  - Dedicated management interface
  - Dedicated server VLAN interfaces
  - VLAN awareness handled at the hypervisor level
- **Role:**  
  Hosts Linux VMs and containers

---

## 4. Authoritative Network Architecture (Post-Recovery – 2026-02)

This section documents the **current, stable, known-good architecture** reached after
recovery from management-plane instability during switch migration.

This is **not aspirational design**.

---

### Management Network Is Untagged by Design

- **Network:** `10.10.10.0/24`
- **Gateway:** `10.10.10.1`
- **OPNsense Interface:** `igc1`
- **VLAN ID:** none (untagged)

Used **only** for infrastructure:
- OPNsense
- UniFi switch
- UniFi access points
- UniFi controller
- Proxmox hosts

MGMT is intentionally **untagged**.

Previous attempts to tag management traffic caused:
- UniFi adoption and reprovision loops
- loss of controller connectivity
- fallback to default addressing

MGMT is therefore:
- untagged
- never carried on trunks
- isolated from client and workload VLANs

---

### VLANs Traverse Only a Dedicated LAGG

All VLAN traffic is carried exclusively over a dedicated aggregated link:

- **OPNsense:** `igc2 + igc3 → LAGG`
- **UniFi switch:** ports 3–4 → LAGG

The MGMT uplink **never carries VLANs**.

This hard separation ensures:
- management-plane stability
- predictable failure domains
- elimination of native VLAN bleed

---

### Router Uplink Is Not a Trunk

The switch → firewall uplink:
- carries **only untagged MGMT**
- blocks all tagged VLANs
- uses a dedicated port profile

Treating the router uplink as a trunk was identified as a primary failure mode
during recovery and is explicitly prohibited.

---

### UniFi Is Controller-Only

UniFi provides:
- switching
- wireless
- centralized management

UniFi does **not** provide:
- routing
- DHCP
- firewalling
- NAT

All L3 and security functions are handled by OPNsense.

---

### Access Points Require Untagged MGMT

UniFi access points:
- require untagged MGMT to remain adopted
- receive client networks via tagged VLANs

AP-facing ports therefore:
- provide untagged MGMT
- carry only required VLANs
- are never full trunks

---

## 5. UniFi Ethernet Port Profiles (Authoritative)

This section documents the **approved UniFi port profiles** and their allowed usage.
Misapplication has previously resulted in management-plane outages.

---

### MGMT_UPLINK

**Purpose:**  
Dedicated management uplink between the switch and firewall.

**Configuration:**
- **Native network:** Default / LAN (MGMT)
- **Tagged VLANs:** Block All

**Used on:**
- Switch port connected to OPNsense `igc1`

**Must never be used on:**
- LAGG ports
- AP ports
- Server or client access ports

---

### LAGG_TRUNK

**Purpose:**  
Exclusive VLAN trunk between switch and firewall.

**Configuration:**
- **Native network:** None
- **Tagged VLANs:** 20, 30, 40, 50, 60, 70

**Used on:**
- Switch ports 3–4
- Connected to OPNsense `igc2 + igc3`

**Must never be used on:**
- Router management uplink
- AP ports
- Access ports

---

### AP_TRUNK

**Purpose:**  
Safe VLAN trunk for access points.

**Configuration:**
- **Native network:** Default / LAN (MGMT)
- **Tagged VLANs:** 30, 40, 50, 60, 70

**Used on:**
- UniFi AP ports only

---

### SERVERS_ACCESS

**Purpose:**  
Single-VLAN access for server workloads.

**Configuration:**
- **Native network:** SERVERS (VLAN 20)
- **Tagged VLANs:** Block All

---

### MGMT_ACCESS

**Purpose:**  
Direct management-only access.

**Configuration:**
- **Native network:** Default / LAN (MGMT)
- **Tagged VLANs:** Block All

---

## 6. IP Addressing & VLAN Plan

### Address Space

- **RFC1918 Range:** `10.10.0.0/16`

### VLAN Summary

| VLAN ID | Name        | Subnet          | Purpose |
|-------:|-------------|------------------|--------|
| — | MGMT        | 10.10.10.0/24 | Infrastructure management (untagged) |
| 20 | SERVERS     | 10.10.20.0/24 | Core infrastructure and services |
| 30 | CLIENTS     | 10.10.30.0/24 | Trusted user devices |
| 40 | LAB         | 10.10.40.0/24 | Testing and experimental systems |
| 50 | IOT         | 10.10.50.0/24 | General IoT devices |
| 60 | GUEST       | 10.10.60.0/24 | Internet-only guest access |
| 70 | APPLE_IOT   | 10.10.70.0/24 | Apple ecosystem devices |

---

## 7. VLAN Details

### MGMT — Management

- **Gateway:** `10.10.10.1`
- **Addressing:** Static only
- **Systems:** Infrastructure devices only

---

### VLAN 20 — Servers

- **Gateway:** `10.10.20.1`
- **Addressing:** Static only

---

### VLAN 30 — Clients

- **Gateway:** `10.10.30.1`
- **Addressing:** DHCP
- **SSID:** Valinor

---

### VLAN 40 — Lab

- **Gateway:** `10.10.40.1`
- **Addressing:** DHCP
- **SSID:** Isengard
- **Purpose:** Testing and experimentation

---

### VLAN 50 — IoT

- **Gateway:** `10.10.50.1`
- **Addressing:** DHCP
- **SSID:** Gondolin
- **Trust Level:** Untrusted

---

### VLAN 60 — Guest

- **Gateway:** `10.10.60.1`
- **Addressing:** DHCP
- **SSID:** Bree

---

### VLAN 70 — Apple IoT

- **Gateway:** `10.10.70.1`
- **Addressing:** DHCP
- **SSID:** Lorien
- **Notes:**  
  Selective mDNS reflection enabled

---

## 8. DNS & DHCP Architecture

### DNS

- **Resolver:** Pi-hole (`palantir`)
- **Upstream:** Unbound
- **Policy:**  
  External DNS is blocked; all VLANs use internal resolvers.

---

### DHCP

- **Provided by:** OPNsense
- **Enabled on:** VLANs 30, 40, 50, 60, 70
- **Disabled on:** MGMT, SERVERS

---

## 9. Firewall Policy Philosophy

- Inter-VLAN traffic denied by default
- Explicit allow rules only
- WAN inbound denied
- Outbound access allowed by role

---

## 10. Change Management

All significant network changes are documented in `changelog/`.
Incidents and recovery procedures are documented separately.

---

*Last updated: 2026-02 — authoritative post-recovery state*
