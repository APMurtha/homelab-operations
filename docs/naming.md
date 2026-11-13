# Naming and identity

Current roles reconciled **2026-11-04**; names do not imply a specific OS or
current reachability. Addresses and evidence live in [network architecture](network.md).

## Infrastructure and services

| Name | Current role |
| --- | --- |
| Anduin | UDM Pro Max gateway and UniFi Network controller; name retained from retired OPNsense |
| Eärendil | UCI Comcast modem; modem-local management is separate from LAN addressing |
| Osgiliath | USW-24-G2 managed switch |
| Ithil | U7 Pro AP |
| mordor | Three-node Proxmox cluster |
| Orthanc / Cirith-Ungol / Dol-Guldur | Proxmox cluster members; fresh owner quorum check passes |
| Palantir | Pi-hole + Unbound DNS infrastructure; complete resolver-chain review pending |
| Rivendell | Media/Docker host; Audiobookshelf, Jellyfin and observed Arr/download services |
| Elessar | Authentik, Nginx Proxy Manager and books-only Cloudflare DDNS |
| Minas-Tirith | Observability host; Grafana reachable, complete telemetry pipeline unverified |
| Ithilien | Access/bastion host; hardening and current Mosh behavior not audited |
| Lothlorien | Retired UniFi controller; owner-decommissioned/shut down |
| k3s-01 / k3s-02 / k3s-03 | LAB control-plane/etcd members; Ready at restored addresses |
| Denethor | Andrew's Omarchy administrative workstation |

Plex was historically named in the media description; its current deployment
was not verified. Do not infer an active service from the naming scheme.

## Storage identity

**Moria** names the UNAS Pro 8 at `10.10.10.8`. Orthanc also has a **local ZFS pool
named `moria`**, exposed separately through `10.10.10.2`. Qualify NAS versus local
pool in mounts, backups and recovery instructions; they are not interchangeable.

## Networks and SSIDs

| VLAN | Network | Current SSID | Role / state |
| --- | --- | --- | --- |
| native 1 | Default | None | `10.0.0.1/24`; DHCP/internet/mDNS off, subnet retained |
| 10 | MGMT | None | Infrastructure management |
| 20 | SERVERS | None | Core services |
| 30 | CLIENTS | Calacirya | Trusted devices; historical name Valinor |
| 40 | LAB | None | Wired K3s; optional Isengard not recreated; hardening deferred |
| 50 | IOT | Gondolin | Restricted IoT source policy |
| 60 | GUEST | Bree | Guest source policy and Wi-Fi peer isolation flag |
| 70 | APPLE_IOT | Lorien | HomePods/Apple TV, selected discovery with CLIENTS |

Names are mnemonic; the network reference and live rule set establish placement
and access. This scheme does not claim every VLAN pair is isolated.

## Reserved names

Historical reservations remain available; none is evidence of deployment:
`barad-dur` (additional compute), `rohan` (client services/VDI), `aule`
(automation/CI), `tengol` (SMTP lab), `yavanna` (home automation), `haldir`
(last-man-standing watcher). Reconfirm intent before assigning one.
