# `anduin` initial SSH discovery — 2026-11-02

Status: **VERIFIED for the bounded observations below**. This is an initial OPNsense-only read, not a complete network or firewall-behavior audit. Andrew authorized root/password SSH with existing/accept-new host-key behavior for `10.10.10.1`; the SSH client would reject a changed key. The interactive password was entered in Andrew's local terminal and never handled by the collection commands. A temporary SSH control socket was used for reads. `hostname -s` returned `anduin`, `id -un` returned `root`, UID was `0`, and `opnsense-version` returned `26.7.1_1 (amd64)`.

Method: a PHP script streamed over SSH parsed `/conf/config.xml` **in memory** and emitted only explicitly selected fields. MACs, client IDs, alias external hosts, public IPs, DDNS credentials, VPN material, descriptions and all unselected XML fields were omitted or masked. Passive `ifconfig`, `netstat`, `pfctl` and process checks were summarized without returning raw configuration. No config export, temporary unredacted file, service restart, lease renewal, rule apply or network change occurred. The complete config was never printed or committed. Saved configuration and runtime state are identified separately below.

## Interfaces, WAN and routing

| Interface | Saved configuration | Runtime observation |
|---|---|---|
| `wan` / `igc0` | IPv4 `dhcp`, IPv6 `dhcp6` | link active; public IPv4 and global IPv6 present (masked); default IPv4 and IPv6 routes via `igc0` |
| `lan` / `igc1` | `10.10.10.1/24`, no VLAN tag | link active; `10.10.10.1` present directly on `igc1` |
| `lagg0` | LACP over `igc2` + `igc3` | active; both members present |
| `opt2`–`opt7` / `vlan02`–`vlan07` | VLANs 20, 30, 40, 50, 60, 70 on `lagg0`; gateways `10.10.X.1/24` | all six interfaces active with those gateway addresses |

**VERIFIED on OPNsense:** MGMT is untagged on `igc1`; there is no VLAN 10 interface in the saved VLAN list. This supports the February 2026 firewall-side topology. **UNKNOWN:** UniFi switch port native/tagged settings, physical cable mapping and whether the same path is stable across devices. The saved `WAN_GW` is the default IPv4 gateway with a dynamic address. A separate `AIRVPN_WOW_GW` entry references `opt1`, while the selected interface summary has no `opt1`; its purpose/current status needs a targeted follow-up. No static-route records were found in the checked legacy section; route-table completeness beyond default routes was not established.

## DHCP and DNS

- **VERIFIED saved config/runtime:** Kea DHCPv4 is enabled on `lan` and `opt2`–`opt7`; a `kea-dhcp4` process was observed. Kea DHCPv6 is disabled. The configured v4 default lifetime is 4,000 seconds, and Kea's automatic DHCP firewall rules setting is enabled.
- **VERIFIED saved config:** MGMT `10.10.10.0/24` and SERVERS `10.10.20.0/24` have no dynamic Kea pool but do have reservations. VLANs 30–70 have pools `10.10.X.100–199`. Fifteen Kea reservations were counted; they include `orthanc` `.2`, `cirith-ungol` `.3`, `dol-guldur` `.4`, `osgiliath` `.10`, `ithil` `.20`, and `lothlorien` `.30` in MGMT, plus `palantir` `.10`, `rivendell` `.30`, `minas-tirith` `.40`, `elessar` `.50`, and `ithilien` `.70` in SERVERS. Reservation presence is not proof that a device currently holds that lease.
- **VERIFIED saved config:** Kea advertises gateway `.1` and DNS `10.10.20.10` for VLANs 20–70; MGMT advertises gateway and DNS `10.10.10.1`. Some scopes also advertise NTP at their `.1` gateway. The old `dhcpd` section contains ranges/options that differ from Kea; treat it as historical/stale until its service state is confirmed, not as a second active DHCP server.
- **VERIFIED saved config/runtime:** OPNsense system DNS points to `10.10.20.10` (`palantir`); WAN-provided DNS override is allowed. OPNsense Unbound is enabled and its process was observed, with forwarding disabled in the checked configuration. This does not establish Pi-hole's upstream chain or prove DNS enforcement for clients.

## Firewall and NAT

**VERIFIED saved config:** 68 modern Firewall Filter rules and 34 aliases were present; one legacy `filter/rule` entry was empty in the inspected structure. Alias names and selected private-address/port values were inspected, but raw external host content and credential fields were not returned. The `HOME_VLANS` alias contains `10.10.10.0/24` through `10.10.60.0/24` and **omits VLAN 70**. `DNS_SERVERS` resolves in saved config to `10.10.20.10`; `UNIFI_CONTROLLER` to `10.10.20.20`.

The saved rule set contains enabled broad allows on MGMT (`lan`), CLIENTS (`opt3`), LAB (`opt4`) and IOT (`opt5`). LAB and IOT also have later DNS/internal block rules in the saved sequence. A CLIENTS direct-DNS block is **disabled**. GUEST (`opt6`) has internal-network blocks followed by internet allow; APPLE_IOT (`opt7`) has selective allows and a `HOME_VLANS` block. These observations contradict a simple claim that all inter-VLAN traffic is denied by default. Rule order, aliases, generated rules and live behavior still need careful review and bounded client tests before an effective policy matrix can be called verified.

**VERIFIED runtime:** `pfctl -sr` returned 254 top-level rules. A sanitized grammar sample showed generated blocks and passes, but the initial parser could not reliably associate all saved broad rules with active PF rules. **UNKNOWN:** complete effective PF order and whether each saved rule is active as intended. Do not infer enforcement from the XML count.

**VERIFIED saved config:** NAT outbound mode is `automatic`. Three enabled WAN destination NAT entries exist: TCP 443 → `10.10.20.50:443`, TCP 2222 → `10.10.20.40:22`, and UDP MOSH ports → `10.10.20.40`. The matching WAN firewall pass for 443 is enabled; the WAN SSH and MOSH passes are disabled in the saved modern rule set. `pfctl -sn` returned 34 active NAT lines, but their full matching/order was not collected. No modern source NAT, 1:1 NAT or NPT rule records were found in the inspected model.

## VPNs and remaining gaps

The saved WireGuard general enabled flag is set, and an `AIRVPN_WOW_GW` gateway entry exists, but the sanitized record counter found no WireGuard server/client records and `wg show interfaces` returned no names. OpenVPN instance records were absent in the inspected model. IPsec general configuration exists; key material was not read. **UNKNOWN:** whether any VPN tunnel or policy route is currently used; do not migrate or delete VPN-related settings based on this initial count.

Still **UNKNOWN**: UniFi switch port profiles and adoption state; Pi-hole/Unbound behavior on `palantir`; effective DNS bypass enforcement; complete active firewall ordering and representative allowed/denied flows; WAN IPv6 delegation to LAN; DHCP lease conflicts; NAS management/storage paths; monitoring and alerts. Continue with [UDM discovery](../runbooks/udm-discovery.md) before approving a gateway cutover.
