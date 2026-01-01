# Homelab Network Design & Operations Documentation

## 1. Purpose & Scope

This document describes the design, implementation, and ongoing operation of my home lab network. The goal of this lab is to simulate real-world Linux network administration tasks, including segmentation, security, monitoring, logging, and change management, in a controlled environment suitable for professional development and resume demonstration.

This document is a *living document* and will be updated as the environment evolves.

---

## 2. Design Goals

* Implement clear network segmentation to reduce blast radius
* Follow least-privilege networking principles
* Maintain service availability during changes
* Use enterprise-relevant tools and patterns
* Support observability (logging & monitoring)
* Enable safe experimentation via isolated lab networks

---

## 3. Physical Hardware Inventory

### Firewall / Router

* **Device:** Protectli Vault FW4C
* **Role:** Dedicated firewall and router
* **Software:** OPNsense
* **Notes:** No additional services run on this hardware

### Switch

* **Device:** TP-Link TL-SG108E (8-port Gigabit Easy Smart Switch)
* **Role:** Layer 2 switching with VLAN support (802.1Q)
* **Management:** Web UI

### Wireless Access

* **Device:** AmpliFi Alien
* **Mode:** Bridge mode
* **Uplink:** Connected to managed switch
* **Role:** Wireless access layer only (routing handled by OPNsense)

### Virtualization Host

* **Platform:** Proxmox VE
* **NICs:** Single physical NIC (VLAN trunk)
* **Role:** Hosts Linux containers and virtual machines

---

## 4. Logical Network Architecture Overview

The network is segmented using VLANs to separate management, servers, clients, IoT devices, and lab/test systems. Routing and firewall enforcement are handled by OPNsense. VLAN tagging is performed at the switch and virtualization layers.

---

## 5. VLAN & IP Addressing Plan

### Base Address Space

* **RFC1918 Network:** 10.10.0.0/16

### VLAN Summary

| VLAN ID | Name      | Subnet        | Purpose                             |
| ------- | --------- | ------------- | ----------------------------------- |
| 10      | MGMT      | 10.10.10.0/24 | Network & infrastructure management |
| 20      | SERVERS   | 10.10.20.0/24 | Core infrastructure and services    |
| 30      | CLIENTS   | 10.10.30.0/24 | User devices                        |
| 40      | DMZ / LAB | 10.10.40.0/24 | Test and experimental systems       |
| 50      | IOT       | 10.10.50.0/24 | Smart devices and appliances        |

---

## 6. VLAN Details

### VLAN 10 – Management

* **Gateway:** 10.10.10.1
* **Static addressing only**
* **Systems:**

  * OPNsense management interface
  * Proxmox host
  * Switch management IP

### VLAN 20 – Servers

* **Gateway:** 10.10.20.1
* **Static addressing preferred**
* **Systems:**

  * Pi-hole (DNS)
  * Ubuntu Server (Docker media services)
  * Central logging VM (planned)
  * Monitoring VM (planned)

### VLAN 30 – Clients

* **Gateway:** 10.10.30.1
* **Addressing:** DHCP via OPNsense
* **Systems:**

  * Desktops
  * Laptops
  * Mobile devices

### VLAN 40 – DMZ / Lab

* **Gateway:** 10.10.40.1
* **Purpose:**

  * Testing new services
  * Failure simulations
  * Experimental configurations

### VLAN 50 – IoT

* **Gateway:** 10.10.50.1
* **Addressing:** DHCP via OPNsense
* **Systems:**

  * Apple HomePods
  * Smart TVs
  * Other network-connected appliances

---

## 7. DNS & DHCP Design

### DNS

* **Primary DNS:** Pi-hole (VLAN 20)
* **Secondary DNS:** OPNsense
* **Clients:** All VLANs use internal DNS resolvers

### DHCP

* **Handled by:** OPNsense
* **Enabled on:** VLAN 30 (Clients), VLAN 50 (IoT)
* **Disabled on:** VLAN 10 (Management), VLAN 20 (Servers)

---

## 8. Firewall & Traffic Policy Philosophy

### Default Policy

* Deny all inter-VLAN traffic by default

### Explicit Allows (High Level)

* Clients → DNS (Pi-hole)
* Clients → Media services
* IoT → Internet only
* Management → Infrastructure access

Multicast and mDNS reflection will be selectively enabled to support Apple device discovery while maintaining isolation.

---

## 9. Change Management

All significant network changes are documented with:

* Date
* Description
* Reason
* Impact assessment
* Rollback plan

---

## 10. Future Enhancements

* Centralized logging (rsyslog / Graylog)
* Monitoring & alerting (Prometheus / Grafana)
* Configuration automation (Ansible)
* AI-assisted log and incident analysis

---

## VLAN Architecture

| VLAN ID | Name     | Subnet          | Gateway        | Status |
|--------|----------|-----------------|----------------|--------|
| 10     | MGMT     | 10.10.10.0/24   | 10.10.10.1     | Assigned, IP configured (not enforced) |
| 20     | SERVERS  | 10.10.20.0/24   | 10.10.20.1     | Assigned, IP configured (not enforced) |
| 30     | CLIENTS  | 10.10.30.0/24   | 10.10.30.1     | Assigned, IP configured (not enforced) |
| 40     | LAB      | 10.10.40.0/24   | 10.10.40.1     | Assigned, IP configured (not enforced) |
| 50     | IOT      | 10.10.50.0/24   | 10.10.50.1     | Assigned, IP configured (not enforced) |

VLAN 40 trunking to OPNsense verified. End-host testing pending due to unavailable test device.


*Last Updated:* Initial draft
