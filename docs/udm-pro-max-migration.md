# UDM Pro Max migration — recovery and acceptance

**Current checkpoint: 2026-11-04.** Physical cutover is complete. Restored services
and the owner-tested paths below work. Final checks have explicit limits; this
is not a claim of complete isolation or a restore-tested recovery plan.

Use [current architecture](network.md) for addresses, ports, DHCP and policy.
The [documentation review](documentation-review-2026-11-04.md) lists unresolved
items. [Archived working notes](_archive/udm-migration-working-notes-2026-11-04.md)
preserve all intermediate plans, approvals, failures and dated receipts. Their
old NO-GO, ARRIS/LAGG rollback and controller restore steps are not executable
instructions for today's network.

## Completed recovery

| Area | Current result / evidence |
| --- | --- |
| Gateway/WAN/controller | Anduin UDM Pro Max online; OS 5.1.34 / Network 10.6.109 observed. UCI online on WAN 9. Osgiliath/Ithil adopted by Anduin; Lothlorien owner-decommissioned/off. |
| Physical network | One Cat6 Anduin port 7→Osgiliath port 1 link at 1 Gbps; Ithil directly on Anduin port 8. Native Default/tagged Allow All preserved. No active gateway LAG. |
| Management | Anduin 10.10.10.1 UI works. Proxmox 10.10.10.2–4, Moria .8, switch .10 and AP .20 use MGMT. Tagged switch/AP overrides and native-MGMT host/NAS ports verified. |
| Default | Owner changed gateway to 10.0.0.1/24. Authenticated read verifies DHCP, Internet Access and mDNS off. Routed subnet remains; internal isolation not claimed. |
| Proxmox | Owner console output 2026-11-03 23:44 Eastern: mordor has 3/3 members/votes, quorum Yes, expected original addresses. No forced quorum/membership change. |
| K3s | Fresh owner output: all three control-plane/etcd nodes Ready at 10.10.40.102, 10.10.40.104, 10.10.40.103. Earlier API readyz/etcd passed during recovery. No datastore reset. |
| SERVERS/LAB DHCP | Approved SERVERS .200–209 pool, five fixed-IP records, LAB .100–199 and three corrected K3s fixed records; Palantir DNS/4,000-second leases verified. |
| CLIENTS DNS | Palantir 10.10.20.10 + murtha.info DHCP suffix acquired by Denethor; short/FQDN Orthanc, internal books and public lookup pass. Existing correct Pi-hole record was preserved. |
| NAS/media | Moria restored from Default addressing to 10.10.10.8; HTTPS/NFS, existing downloads read and Audiobookshelf in-container library NFS/read pass. Orthanc local moria pool is separate. |
| Published books | Only WAN TCP 443→Elessar 443/NPM; books-only DDNS updater on Elessar. Backend, normal TLS/HTTP 200, authoritative/public DNS and owner mobile-data access verified. |
| Gondolin/IOT | Correct 10.10.50.1 gateway, DHCP .100–199, Palantir DNS; seven enabled scoped rules and mDNS off. Owner tested Internet and blocked management/Palantir web. |
| Lorien/APPLE_IOT | DHCP .100–199/Palantir; eight scoped rules. mDNS only CLIENTS 30↔APPLE_IOT 70. HomePods/AppleTV on Lorien; cross-VLAN AirPlay/Home control and paired-HomePod TV playback owner-tested. |
| Bree/GUEST | Corrected initial Native/Default SSID binding to GUEST 60; DHCP .100–199/Palantir, seven scoped rules, Wi-Fi client isolation on, mDNS off. Owner Internet/blocked web tests and live guest lease pass. |
| Backup | Owner exported fresh console backup 2026-11-03 23:48 Eastern, 119,728 bytes; protected same-host copy/digest match verified. Contents/restore and off-host protection not verified. |

CLIENTS leases remain 86,400 seconds; other enabled scopes 4,000. MGMT DHCP is off.
Routed IPv6 is none on all eight LANs. Full details and test provenance remain in
the archive and private state; no secrets, MAC inventory or raw backups belong here.

## Decisions and remaining checks

- **LAB hardening explicitly deferred:** Andrew has not selected workloads/service
  policy. LAB is not isolated from trusted VLANs. Inspect K3s/storage dependencies
  before proposing restrictions; do not invent a policy or treat deferral as a
  requirement to implement new blocks. CLIENTS/SERVERS/MGMT also have no custom
  source restrictions in the reviewed 22-rule set.
- **Guest peer isolation:** configured on Bree but requires two actual guest
  clients to test. The single-phone Internet/web tests do not establish every
  destination, protocol, DNS bypass or return path.
- **Resolver chain:** Pi-hole local records/DNS behavior work. Authenticated
  upstream Unbound/conditional-forwarding inspection remains unavailable.
  Retired Lothlorien DNS cleanup needs a separately reviewed edit.
- **Telemetry/IDS:** OPNsense Suricata source is retired. UDM IDS/IPS/syslog
  replacement and complete Minas-Tirith ingestion/retention/alerts are unverified.
  See [observability](observability.md).
- **Recovery:** current backup exists, not restore-tested/off-host. Persistence
  after reboot and independent local/offline administrative recovery have not
  been fully exercised; no reboot/restore/reset is authorized as a test.
- **Historical completeness:** source Kea counts/selected fields were retained,
  not a complete restorable OPNsense export. Current restored records are not
  evidence that every old option/reservation/alias/service was reproduced.

## Automation and evidence boundaries

At the November 4 checkpoint, installed NEST 2.0.0 writes were pinned to Network 10.6.106. Anduin 10.6.109
recovery used separately reviewed, owner-approved scoped adapters and UI steps;
these do not grant general write capability or establish today's installed version or guard.
An official IOT network PUT succeeded; a Gondolin Wi-Fi POST returned 400. Read-only
reconciliation verified no SSID was created and existing state was unchanged;
Wi-Fi creation then used the supported UI. Do not blindly replay old scripts.
The rejected create's detailed validation cause was not retained.

[Sourced skill improvements](https://github.com/erwich/nest/pull/6) are proposed
for Eric's review; that PR is not evidence a new plugin version is installed.

Raw journals, plans, source MACs, backups, tokens and full provider responses
stay in owner-local protected state. Evidence labels: **API/config verified**,
**host/service verified**, **owner-tested**, **untested**, **owner-deferred**.
A healthy port or container is not a complete service/cluster test.

## Recovery boundary

Use [current management recovery](../runbooks/recover-unifi-management-plane.md)
and the fresh private UDM backup. Keep OPNsense disconnected and Lothlorien off.
Do not follow old LAGG/ARRIS cable rollback after device adoption, DHCP changes,
NAS addressing and UCI migration; a return to OPNsense now needs its own approved
lease/port/controller/WAN plan. Preserve a working MGMT/CLIENTS path and capture
state before every further approved change.
