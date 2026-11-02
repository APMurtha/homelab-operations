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
- **Switch:** UniFi USW-24-G2 (Layer 2, VLAN-aware)
- **Wireless AP:** `ithil` (UniFi U7 Pro, VLAN-aware access point)
- **UniFi Controller:** `lothlorien`
- **Hypervisor:** `orthanc` (Proxmox VE)
- **DNS:** `palantir` (Pi-hole + Unbound)
- **Media / Docker:** `rivendell`
- **Observability:** `minas-tirith`
- **Bastion Host:** `ithilien`
- **Storage Pool:** `moria` (ZFS)
- **Authentication:** `elessar` (Authentik + NPM)

The network design uses these VLANs; effective segmentation still needs testing:
- MGMT, SERVERS, CLIENTS, LAB, IOT, APPLE_IOT, and GUEST
- No flat network
- Inter-VLAN deny by default is the design intent; [initial OPNsense discovery](docs/anduin-discovery-2026-11-02.md) found broad allows that require policy review

---

## 📂 Repository Structure

```text
docs/        Architecture and design documentation
diagrams/    Network and architecture diagrams
runbooks/    Operational procedures and how-tos
incidents/   Incident analysis and lessons learned
changelog/   Chronological change history
automation/  Scripts and configuration automation
```

## Migration preparation

The UDM Pro Max has arrived (owner report). Its [isolated initial setup checklist](runbooks/udm-isolated-initial-setup.md) keeps Anduin in production; the [migration plan](docs/udm-pro-max-migration.md) covers the later single-uplink cutover. The replacement cable modem remains a separate later stage.
