# Homelab Network Overview

## Goals
- Segmented home network using VLANs (MGMT / SERVERS / CLIENTS / LAB / IOT)
- Central DNS with ad-blocking + local resolution (Pi-hole + Unbound)
- Secure-by-default firewall policy with explicit allow rules
- Containerized service hosting (media + automation)
- Observability-first: logs + metrics + dashboards + alerting (in progress)

## Physical Topology
- Router/Firewall: OPNsense on Protectli Vault FW4C
- Switch: TP-Link TL-SG108E managed switch
- WiFi: AmpliFi Alien in bridge mode

## VLANs / Subnets
| VLAN | Name    | Subnet         | Purpose |
|------|---------|----------------|---------|
| 10   | MGMT    | 10.10.10.0/24   | Network management interfaces |
| 20   | SERVERS | 10.10.20.0/24   | Proxmox + infrastructure services |
| 30   | CLIENTS | 10.10.30.0/24   | User devices |
| 40   | LAB     | 10.10.40.0/24   | Experiments / testing |
| 50   | IOT     | 10.10.50.0/24   | Smart home / IoT devices |
| 60   | GUEST   | 10.10.60.0/24   | Internet-only access for untrusted or temporary devices |

## Core Services
### DNS
- Pi-hole + Unbound on `palantir`
- Policy: clients use Pi-hole; direct DNS is blocked where appropriate

### Media / Automation
- `rivendell` runs Docker services:
  - Gluetun + Mullvad (VPN overlay for torrenting)
  - qBittorrent + reseeding tools
  - *arr stack behind the VPN
  - Audiobookshelf + Jellyfin (LAN access for now)

### Observability (in progress)
- `minas-tirith` hosts:
  - Grafana
  - Loki
  - Promtail
  - Netdata
- Goal: dashboards + alerts (Slack notifications)

## Access Model (Current / Planned)
- Current: LAN-only access to service UIs
- Planned:
  - Admin access: Tailscale (iPad-friendly)
  - External media: Cloudflare Tunnel + Zero Trust + SSO (Authentik)
