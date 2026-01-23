# 📛 Naming & Identity Scheme (Lord of the Rings)

## Purpose

This homelab uses a **role-based naming convention inspired by _The Lord of the Rings_**.  
Names are chosen to reflect **function, trust level, and responsibility**, making the environment easier to operate, document, and explain in professional or interview contexts.

The theme is aesthetic; the **intentional structure** is the point.

---

## 🖥️ Compute & Infrastructure Hosts

| Name | Role | Description |
|-----|-----|-------------|
| **orthanc** | Proxmox Hypervisor | The central tower that houses all other systems. Runs and manages all VMs and containers. |
| **rivendell** | Media / Docker Server | Home to media and content services (Plex, Jellyfin, Audiobookshelf, Arr stack). A place of culture and stories. |
| **minas-tirith** | Telemetry & Observability | The watchful city. Hosts Grafana, Loki, Promtail, Netdata, and centralized logging. |
| **palantir** | DNS (Pi-hole + Unbound) | Seeing stones used for name resolution, visibility, and DNS enforcement. |
| **ithilien** | Bastion / Access Host | Hardened SSH/MOSH jump host used for administrative access into protected networks. |
| **lothlorien** | UniFi Controller | Centralized management plane for wireless infrastructure. Stable, isolated, and trusted. |
| **elessar** | Central Authentication | Authentik + Nginx Proxy Manager |

---

## 🌐 Network Infrastructure Naming

| Component | Name | Purpose |
|--------|------|--------|
| Firewall / Router | **anduin** | OPNsense gateway and inter-VLAN router. Central control point for traffic flow and policy enforcement. |
| Managed Switch | **osgiliath** | VLAN-aware distribution layer between firewall, hosts, and access points. |
| Wireless Access Point | **ithil** | Trusted Wi-Fi access point bridged into the VLAN architecture. |

---

## 🗄️ Storage Naming

| Name | Type | Description |
|-----|-----|-------------|
| **moria** | ZFS Pool | Primary data pool for media, containers, and persistent storage. Named for depth, durability, and scale. |

> Storage names are intentionally distinct from hostnames to avoid coupling data identity to compute lifecycle.

---

## 🧑‍💻 Administrative Endpoints

| Name | Role | Description |
|------|------|-------------|
| denethor | Admin Workstation | Primary privileged management workstation for infrastructure administration. |

___

## 🧩 VLAN Naming Conventions

VLANs use **numeric IDs with functional names**, prioritizing clarity over theme.

| VLAN ID | Name | Purpose |
|-------:|------|--------|
| 10 | MGMT | Management plane (firewall, hypervisor, admin access) |
| 20 | SERVERS | Infrastructure services and application servers |
| 30 | CLIENTS | Trusted user devices |
| 40 | LAB | Experimental systems and testing |
| 50 | IOT | Untrusted IoT devices |
| 60 | GUEST | Internet-only guest access |

---

## 📶 Wireless SSID Naming

Wireless networks use Tolkien-themed names that map directly to VLANs and trust levels.

| SSID Name | VLAN | Trust Level | Purpose |
|----------|------:|-------------|--------|
| **Valinor** | 30 | Trusted | Primary client network for personal devices |
| **Isengard** | 40 | Experimental | Lab and test devices; breakable by design |
| **Gondolin** | 50 | Restricted | IoT devices with limited east-west access |
| **Bree** | 60 | Untrusted | Guest access, internet-only |

___

## 🧠 Design Principles

- **Role-based naming**  
  Names encode *function*, not operating system or software stack.
- **Clear trust boundaries**  
  Names help signal access level and security posture.
- **Scalable**  
  New systems can be added without renaming existing infrastructure.
- **Operational clarity**  
  Names are used consistently across DNS, firewall rules, logs, dashboards, and documentation.
- **Interview-friendly**  
  Easy to explain, intentional, and professional.

---

## 🔮 Reserved / Future Names

| Name | Intended Role |
|-----|--------------|
| **barad-dur** | 2nd Proxmox Node |
| **cirith-ungol** | 3rd Proxmox Node |
| **rohan** | Client services or VDI |
| **aule** | Automation, CI/CD, orchestration |
| **tengol** | outbound SMTP relay lab (SPF/DKIM/DMARC practice) |
| **yavanna** | Home Assistant Automation + IoT coordination across realms |
| **haldir** | Last-Man-Standing Node Pi-based watcher for UPS, WoL, and critical monitoring when primary infrastructure is down. |

---

## 📌 Notes

- Naming is consistent across:
  - DNS records
  - Firewall aliases and rules
  - Monitoring labels and dashboards
- The theme supports memorability; **the structure supports operations**.
