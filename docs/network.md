# Current network architecture and operations

**Reconciled 2026-11-04.** This is the current-state reference. Evidence comes
from authenticated Anduin reads, host/container inspection and explicitly labeled
owner tests during November recovery. Recheck live state before configuration
changes. The [migration acceptance](udm-pro-max-migration.md) and [review findings](documentation-review-2026-11-04.md)
identify what remains unverified. February's untagged-only/LAGG design is historical;
it is not a constraint on this verified UDM topology.

## Gateway, controller and physical path

Anduin is a **UDM Pro Max**, UniFi OS **5.1.34**, Network **10.6.109** at the
recovery checkpoint. It routes the LANs, provides enabled DHCP scopes, firewall
and NAT, and manages Osgiliath and Ithil. Eärendil UCI provides Comcast's handoff.
Retired OPNsense stays disconnected; Lothlorien stays off. Do not restore its old
Network backup or reconnect overlapping gateway/DHCP services to production.

| Connection | Verified role / speed | VLAN behavior |
| --- | --- | --- |
| UCI → Anduin WAN 9 | Comcast handoff, 2.5 Gbps | WAN; modem-local management `192.168.100.1` is separate from LANs |
| Anduin 7 → Osgiliath 1 | One Cat6 uplink, 1 Gbps | Native Default; tagged Allow All; no active LAG |
| Anduin 8 → Ithil | Direct AP connection, 1 Gbps | Native Default; tagged workload/MGMT path preserved |
| Osgiliath 2 → Moria NAS | 1 Gbps | Native MGMT 10; tags Allow All preserved |
| Osgiliath 5 / 6 / 7 | Proxmox management paths | Native MGMT 10; tags Allow All preserved |
| Osgiliath 13 | Orthanc server bridge path | Native SERVERS 20; tags Allow All preserved |
| Osgiliath 17 / 18 / 19 | LAB guest bridge paths | Native LAB 40; tags Allow All preserved |

The port table records verified configuration, not a recommendation to allow all
tags on every access port. Tightening those lists requires dependency review and
its own approved diff. Other port roles are not fully reconciled. Retired LAG
ports were observed down; do not recreate aggregation as a recovery step.

Osgiliath and Ithil use **Network Override MGMT 10 with static management IPs**.
Their management traffic is tagged over the unchanged native-Default uplinks.
Moria/Proxmox management uses untagged frames on native-MGMT access ports. Native
VLAN selection and tagged device overrides must not be conflated.

See [physical/logical topology](../diagrams/network.mmd), [service map](../diagrams/service-placement.mmd)
and [single-uplink detail](../diagrams/udm-single-uplink.mmd).

## Addressing and DHCP

| Network | VLAN | Gateway/prefix | DHCP range | DNS / notes |
| --- | --- | --- | --- | --- |
| Default | native 1 | `10.0.0.1/24` | Off | Internet Access/mDNS off; subnet still configured |
| MGMT | 10 | `10.10.10.1/24` | Off | Static infrastructure; no broad pool |
| SERVERS | 20 | `10.10.20.1/24` | `.200–209` | Palantir; five restored fixed-IP records |
| CLIENTS | 30 | `10.10.30.1/24` | `.100–199` | Palantir; `murtha.info` search domain |
| LAB | 40 | `10.10.40.1/24` | `.100–199` | Palantir; three K3s fixed-IP records |
| IOT | 50 | `10.10.50.1/24` | `.100–199` | Palantir |
| GUEST | 60 | `10.10.60.1/24` | `.100–199` | Palantir |
| APPLE_IOT | 70 | `10.10.70.1/24` | `.100–199` | Palantir |

Enabled DHCP servers run on Anduin. Gateway option is the matching `.1` address.
CLIENTS lease duration is **86,400 seconds**; other enabled scopes use **4,000**.
Routed IPv6 configuration is `none` on all eight LAN networks at this checkpoint;
this is not a claim about link-local IPv6 or every host's own VPN interfaces.

OPNsense Kea previously had reservation-only MGMT/SERVERS. SERVERS' small dynamic
pool is an explicit owner-approved exception; MGMT remains off with static
infrastructure. Stored disabled pool bounds do not mean an active DHCP service.
The full original Kea configuration/reservation export was not retained; restored
current records are verified, but historical export completeness cannot be claimed.

## Infrastructure and service addresses

| System | Address | Role / evidence |
| --- | --- | --- |
| Anduin | `10.10.10.1`; per-VLAN gateways above | MGMT UI owner-tested; CLIENTS administration also verified |
| Orthanc | `10.10.10.2` | Static Proxmox member; local `moria` ZFS/NFS export |
| Cirith-Ungol / Dol-Guldur | `10.10.10.3` / `.4` | Static Proxmox members; owner-confirmed 3/3 quorum |
| Moria | `10.10.10.8` | UNAS Pro 8; HTTPS/NFS and actual media mount reads verified |
| Osgiliath / Ithil | `10.10.10.10` / `.20` | Static tagged management; adopted/online under Anduin |
| Palantir | `10.10.20.10` | Pi-hole DNS/web; upstream Unbound configuration review pending |
| Rivendell | `10.10.20.30` | Docker/media, Audiobookshelf backend port 13378 |
| Minas-Tirith | `10.10.20.40` | Observability; see verification limits below |
| Elessar | `10.10.20.50` | NPM, Authentik, books-only Cloudflare DDNS |
| Ithilien | `10.10.20.70` | Access host; SSH reachable, current hardening/MOSH behavior unverified |
| k3s-01 / k3s-02 / k3s-03 | `10.10.40.102` / `.104` / `.103` | Owner-confirmed Ready control-plane/etcd nodes |

Physical VM/LXC placement across mordor is not fully inventoried. Do not infer
all guests run on Orthanc. Lothlorien's retired guest had documented MGMT `.30`;
a stale Pi-hole FQDN record at `10.10.20.20` remains a cleanup item, not a live controller.

## Wireless

| SSID | Network | Bands | Security | Wi-Fi peer isolation |
| --- | --- | --- | --- | --- |
| Calacirya | CLIENTS 30 | 2.4 / 5 / 6 GHz | WPA2/WPA3, PMF optional | Off |
| Gondolin | IOT 50 | 2.4 GHz | WPA2, PMF/fast roaming off | Off |
| Lorien | APPLE_IOT 70 | 2.4 / 5 GHz | WPA2, PMF/fast roaming off | Off |
| Bree | GUEST 60 | 2.4 / 5 GHz | WPA2, PMF/fast roaming off | On; two-device test pending |

Ithil is the only adopted AP. No captive portal is configured. Valinor is the
historical client SSID; Isengard is an unrecreated optional LAB SSID. HomePods and
Apple TV are on Lorien; cross-VLAN AirPlay/Home control and paired-HomePod TV
playback passed owner tests. Client isolation is intentionally off there.

## DNS, discovery and ingress

Palantir (`10.10.20.10`) is advertised on all enabled scopes. Denethor acquired
Palantir plus CLIENTS' `murtha.info` search suffix: both `orthanc` and
`orthanc.murtha.info` resolve to `10.10.10.2`. `books.murtha.info` resolves internally
to Elessar `10.10.20.50`. Public and UDP/TCP53 resolver tests pass. The actual
Pi-hole upstream/Unbound/conditional-forwarding configuration still requires
authenticated inspection; do not claim a freshly audited resolver chain.

Gateway mDNS Proxy is Custom, scoped to **CLIENTS 30 + APPLE_IOT 70 only**.
Existing specific service selections were preserved for initial Apple tests.
Discovery does not itself grant firewall access. Other networks' mDNS forwarding
is off; same-VLAN multicast behavior is a separate concern.

Only approved inbound forward: **Comcast WAN TCP443 → Elessar443 (NPM)**.
NPM proxies books to Rivendell's Audiobookshelf backend. Cloudflare DDNS on Elessar
manages **only `books.murtha.info` IPv4**, with no cloudflared tunnel for this path.
Normal-TLS HTTP200 and independent owner mobile-data access pass. Historical WAN
SSH2222/MOSH forwards are not restored. No custom static routes were returned.

## Effective policy and verification limits

The reviewed configuration uses classic rules, not a migrated zone firewall.
**22 enabled custom rules** are source-scoped to IOT (7), APPLE_IOT (8), GUEST (7).
Those sources allow Palantir UDP/TCP53, DHCP and established/related replies;
block other plain DNS53, other nonpublic destinations and other gateway access.
Apple additionally permits gateway mDNS discovery. The reused IPv4 address group
covers RFC1918, CGNAT and link-local space, including Default and VLAN70.
Internet DNS encryption is not claimed blocked.

CLIENTS, SERVERS, MGMT and LAB have **no custom source restrictions in this set**.
LAB hardening is owner-deferred until workloads/storage dependencies are known.
VLAN separation is not a general inter-VLAN deny policy. Same-VLAN peers on IOT
and APPLE_IOT are not isolated; Bree's Wi-Fi isolation flag does not prove wired
or every guest-peer path is blocked.

Owner tests passed basic IoT/Guest Internet and denied MGMT/Palantir web access,
plus the Apple workflows above. Full DNS enforcement, return/negative-flow matrix,
two-client guest isolation, reboot persistence and offline recovery remain
partially untested. A fresh private console backup exists, but its restore and
off-host protection have not been verified. See the [review findings](documentation-review-2026-11-04.md).

## Historical references and change boundaries

The [November change record](../changelog/2026-11-04-complete-udm-service-recovery.md)
records recovery outcomes. The [OPNsense discovery](anduin-discovery-2026-11-02.md),
[February incident](../incidents/2026-02-08-unifi-management-plane-instability.md)
and [archived migration notes](_archive/udm-migration-working-notes-2026-11-04.md)
retain older evidence. Their addresses, LAGG and reset/controller procedures are
not current operating instructions. Changes to WAN, switching, DHCP/DNS, firewall,
controllers or services require a reviewed scope, preserved recovery and approval.
