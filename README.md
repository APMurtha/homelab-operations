# 🧙‍♂️ Homelab Operations

This repository documents a **VLAN-segmented, security-focused homelab** designed to mirror small-enterprise Linux and network operations practices.

The environment emphasizes **intentional architecture, least-privilege networking, centralized DNS, observability, and disciplined documentation**.  
While themed around *The Lord of the Rings* for memorability, the design principles are practical and professional.

---

## 📌 Overview

The homelab is built to support:

- Real-world Linux administration workflows
- Network segmentation and firewall policy design
- Centralized DNS enforcement and logging
- Monitoring, telemetry, and troubleshooting
- Safe experimentation via isolated lab networks
- Resume-ready documentation and change tracking

Core technologies include **OPNsense**, **Proxmox VE**, **Pi-hole**, Docker, and open-source observability tools (Grafana, Loki, Netdata).

---

## 🗺️ Architecture at a Glance

- **Firewall / Router:** `anduin` (OPNsense)
- **Switch:** `osgiliath` (VLAN-aware L2)
- **Wireless AP:** `ithil` (UniFi U7 Pro, VLAN-aware access point)
- **UniFi Controller:** `lothlorien`
- **Hypervisor:** `orthanc` (Proxmox VE)
- **DNS:** `palantir` (Pi-hole + Unbound)
- **Media / Docker:** `rivendell`
- **Observability:** `minas-tirith`
- **Bastion Host:** `ithilien`
- **Storage Pool:** `moria` (ZFS)
- **Authentication:** `elessar` (Authentik + NPM)

The network is fully segmented using VLANs:
- MGMT, SERVERS, CLIENTS, LAB, IOT, APPLE_IOT, and GUEST
- No flat network
- Inter-VLAN traffic denied by default

---

## 📂 Repository Structure

```text
docs/        Architecture and design documentation
diagrams/    Network and architecture diagrams
runbooks/    Operational procedures and how-tos
incidents/   Incident analysis and lessons learned
changelog/   Chronological change history
automation/  Scripts and configuration automation
