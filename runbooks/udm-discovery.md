# Read-only verification after UDM recovery

**Current as of 2026-11-04.** Initial setup/cutover are complete. Read
[current architecture](../docs/network.md), [acceptance](../docs/udm-pro-max-migration.md)
and [review gaps](../docs/documentation-review-2026-11-04.md). Do not repeat source
router discovery by contacting today's10.10.10.1 as OPNsense; it is the UDM.

## Access and scope

Select Andrew / andrew-network independently from the asking person; use that
person's own configured access. Verify Anduin UDM Pro Max, site/gateway IDs and
actual version before targeted API reads. NEST's installed 10.6.106 write gate
remains intact on actual10.6.109. Read-only checks do not authorize service,
WAN, firewall, DHCP, port, controller, restore or reboot changes.

Private snapshots/journals live in local protected state outside this repository.
Never dump Wi-Fi detail/passwords, full Docker environments, raw XML, tokens,
backups or broad account exports into Git/output. Prefer existing dated receipts
for completed research; refresh when live evidence or a new task warrants it.

## Bounded verification

| Target | Useful read | Limit |
| --- | --- | --- |
| Anduin | Actual network detail, DHCP/DNS/domain, mDNS scope, enabled rules/ordering, NAT and devices | Documented API/schema/read success is not write support |
| Switch/AP | Identity, adopted/online, management override/IP, exact peer ports/native/tagged fields and SSID network reference | Names/profile labels/client cached addresses can be stale |
| DHCP/DNS | A real client lease/options and normal resolution; intended resolver UDP/TCP 53; FQDN versus search suffix | Server configuration alone does not prove adoption or enforcement |
| Proxmox/K3s | Authorized console pvecm quorum and k3s node/readiness output | TCP reachability alone does not establish cluster health; no forced votes/resets |
| NAS/media | Local mount metadata, actual NAS address and container mounts; bounded read after reachability | Do not trigger blocked hard NFS I/O or remount/restart broadly |
| Published service | Backend, proxy SNI/TLS, split/public DNS, DDNS and independent external access | Local HTTP 200 alone does not prove external ingress/playback |
| Guest/IoT policy | Actual source VLAN, allowed Internet/DNS, denied destinations, replies and same-VLAN peer tests | Prevent cellular/VPN fallback; one test is not an all-pairs audit |
| Telemetry | Intended listener/publication, scrape targets, ingestion timestamp and alerts | Unreachable documented port does not prove service is down |
| Backup | Provenance, export date/size, protected copy/digest and independently tested recovery access | Opaque data/hash alone is not a validated restore/off-host backup |

Last owner evidence confirms3/3 Proxmox quorum, all three K3s nodes Ready,
Apple playback and basic Guest/IoT tests. LAB hardening is explicitly deferred.
Remaining access/decision/test gaps are tracked in the [review report](../docs/documentation-review-2026-11-04.md).
Do not retry previously denied SSH keys or guess new transport credentials.
