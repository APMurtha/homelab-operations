# UDM Pro Max migration preparation

Status: **PLANNED**. Prepared 2026-11-02; no production change or live configuration verification has occurred for this plan. The UDM Pro Max is ordered, not installed. Use [network.md](network.md) for the February 2026 design and [the discovery checklist](../runbooks/udm-discovery.md) to replace assumptions with dated evidence.

## Discovery access status — 2026-11-02

**VERIFIED locally (not a live network finding):** NEST 2.0.0 initially failed its scoped `home.py --person andrew --system andrew-network status` check because the required Andrew/network binding did not exist. `systems.py show` reported a missing binding. After creating the local binding with `systems.py bind --person andrew --system andrew-network`, both `show` and the scoped `status` command succeeded. `unifi-access doctor --local` reports Python ready and no scoped API key; scoped status reports no selected UniFi target or household profile. At this step, no service authentication or network connectivity was tested. This was a missing local skill configuration, not an observed network or production authentication failure.

**VERIFIED transport only:** The owner supplied `https://10.10.10.1/` for `anduin`. The initial HTTPS request failed certificate validation. The owner then supplied the local trust certificate `~/.config/nest/certs/anduin.pem`. With `curl --cacert` and normal hostname verification, an HTTPS GET of `/` returned `200` and `ssl_verify_result=0` on 2026-11-02. HEAD returned `403`, so use the bounded GET result for this transport check. No credential was sent and no OPNsense configuration was read. The sandboxed attempt could not open TCP 443; the verified GET succeeded outside the sandbox. TLS trust is resolved for this endpoint through this explicit CA file; no global trust override or insecure option was used.

**AUTHENTICATION BLOCKED:** NEST 2.0.0 has no bundled OPNsense helper, scoped OPNsense credential path or per-endpoint CA setting. Its UniFi API key is for UniFi Site Manager and must not be reused. Andrew reports that a read-only OPNsense API account/key still needs setup. Creating that account/key changes production OPNsense configuration and is outside the current discovery-only authorization. Consequently no authenticated read-only connectivity test ran, and NEST access to OPNsense interfaces, DHCP, firewall, NAT, WAN and IPv6 resources is unverified. A reviewed, narrowly scoped connector can use the existing PEM and a local hidden credential/OS store after the account exists; it must validate the OPNsense hostname and use only approved GET endpoints.

**SSH access gate:** Andrew reports OPNsense version `26.7.1_1-amd64` and root/password SSH access. Neither version nor SSH access has been verified in this session. Local `known_hosts` entries exist for `10.10.10.1`, but Andrew confirms they were not independently verified. No SSH command was run. [The SSH discovery proposal](../runbooks/opnsense-ssh-discovery-plan.md) requires a console-verified host-key fingerprint before a minimal identity check; full collection then needs separate approval.

The [OPNsense API access review](opnsense-api-access-review.md) maps proposed GET endpoints to upstream ACL privileges and records the areas the API cannot establish alone. It is a proposal until the installed OPNsense version and ACLs are checked.

**Owner report, not API-verified:** `lothlorien` is linked to UniFi Site Manager. This makes the NEST Site Manager route a candidate, but the scoped API key is absent and no authenticated host/site inventory has been read.

**UNKNOWN:** OPNsense, UniFi controller, Pi-hole, Proxmox and UNAS live configuration. No authenticated read-only connection is currently configured for those systems in this work session. The NEST UniFi helper uses the official Site Manager/Network API; whether the linked self-hosted `lothlorien` is exposed to this key/account is untested. Obtain an owner-confirmed endpoint and authorized local access method for each target; do not infer credentials from the OS user, Git remote or other NEST systems. The OPNsense/Proxmox/UNAS discovery commands remain proposals until access is verified.

## Evidence labels

- **VERIFIED**: observed read-only on the named live system, with date and method.
- **HISTORICAL**: asserted in this repository's dated documentation or change history; may have drifted.
- **PLANNED**: proposed equipment or procedure; not deployed.
- **UNKNOWN**: requires inspection or an end-to-end test.

Do not promote a historical assertion to verified by repeating it here. Keep raw exports, backups, leases, credentials, public IPs and device identifiers in private storage; record only reviewed, non-secret facts in this repository.

## Current inventory and topology

| Component | Address / connection | Evidence and confidence |
|---|---|---|
| Comcast/Xfinity → ARRIS Surfboard → `anduin` OPNsense FW4C | WAN lease, modem model and bridge mode **UNKNOWN** | Surfboard/ISP from owner, medium; WAN settings unknown |
| `anduin` → `osgiliath` USW-24-G2 | MGMT untagged on `igc1`; VLANs 20–70 on `igc2` + `igc3` LAGG to switch ports 3–4 | **HISTORICAL**, February 2026 recovery design, medium |
| `ithil` U7 Pro; `lothlorien` self-hosted Network | AP native MGMT and tagged client VLANs; controller placement/version/adoption **UNKNOWN** | **HISTORICAL** design plus owner hardware report, medium |
| `orthanc` Proxmox; `moria` ZFS | `10.10.10.2`; separate management and Intel i350-T2 workload NICs | owner and January 2026 change, medium |
| `cirith-ungol`, `dol-guldur` Proxmox | `10.10.10.3`, `.4`; three-node `mordor` cluster | owner report, medium; live cluster status unknown |
| `palantir` Pi-hole + Unbound | `10.10.20.10` | owner report, medium; forwarding/enforcement unknown |
| `rivendell`, `minas-tirith`, `ithilien` | `10.10.20.30`, `.40`, `.70` | owner report, medium; live role/address unknown |
| `elessar` | authentication and reverse proxy; address unknown | owner and repository, medium |
| UniFi UNAS Pro 8 | management IP, port, VLAN, data paths and dependencies **UNKNOWN** | owner report, medium |

**PLANNED:** UDM Pro Max first, retaining the ARRIS modem. UniFi Cable Internet replaces the modem only after the gateway is stable. Pro XG 24 PoE, aggregation switch (model undecided), patch panels/Cat6A/Etherlighting, UniFi UPS/UPS Pro, PDU Pro and rack compute are planning items; no installation is established.

### Addressing reference

Preserve subnet and gateway addresses. The repository calls MGMT **untagged**, although the owner calls it VLAN 10. Treat the VLAN 10 tag as **UNKNOWN** until switch and firewall inspection; do not tag MGMT merely to match a name.

| Network | Subnet | Intended gateway | DHCP / SSID (historical) |
|---|---|---|---|
| MGMT (VLAN 10 label; untagged in 2026 design) | 10.10.10.0/24 | 10.10.10.1 | static |
| SERVERS / 20 | 10.10.20.0/24 | 10.10.20.1 | static |
| CLIENTS / 30 | 10.10.30.0/24 | 10.10.30.1 | Kea? / Valinor |
| LAB / 40 | 10.10.40.0/24 | 10.10.40.1 | Kea? / Isengard |
| IOT / 50 | 10.10.50.0/24 | 10.10.50.1 | Kea? / Gondolin |
| GUEST / 60 | 10.10.60.0/24 | 10.10.60.1 | Kea? / Bree |
| APPLE_IOT / 70 | 10.10.70.0/24 | 10.10.70.1 | Kea? / Lorien |

The owner reports Kea on OPNsense. `docs/network.md` only says OPNsense DHCP, with no backend or scope details. Confirm live backend, enabled scopes, reservations, lease times and options before building UDM DHCP. Never run Kea and UDM DHCP on the same production subnet simultaneously.

## Firewall policy translation worksheet

**UNKNOWN:** every row's actual OPNsense rule order, floating/interface scope, aliases, NAT, IPv6 behavior and tested outcome. Fill this from the discovery runbook before approval. A deny-by-default design statement is not proof of implementation. UniFi zone defaults and rule order must be reviewed on the installed Network version. Create separate zones where distinct trust policies require them; placing all VLANs in one broad Internal zone can erase intended boundaries. Include gateway-local services, IPv6 and established/related behavior in tests.

| Source → destination | Intended behavior (historical) | Required evidence before translation |
|---|---|---|
| MGMT → infrastructure | restricted administration | exact source hosts, ports, gateway-local access |
| CLIENTS → `palantir`, services, WAN | DNS/services and internet allowed by role | DNS redirect/block rules, service exceptions, egress NAT |
| LAB → servers/MGMT/WAN | isolated except explicit allows | actual rules and exceptions |
| IOT, APPLE_IOT → DNS/services/WAN | limited access; selective mDNS for APPLE_IOT | mDNS reflector paths, device exceptions, IPv6 |
| GUEST → internal networks/WAN | internet only | gateway-local DNS/DHCP, captive portal/isolation |
| WAN → internal/gateway | deny except explicit published services/VPN | port forwards, NAT reflection, VPN listeners, IPv6 |
| All VLAN pairs | deny by default design | ordered allow/deny tests in both directions |

For each live rule record source, destination, protocol/ports, action, logging, schedule, alias expansion, order, family, gateway/interface and purpose. Map to UniFi source/destination zone, network and rule order; record any unsupported feature and its compensating design. Test both permitted and forbidden flows from representative clients. A Network backup does **not** contain OPNsense firewall, NAT, routes or DHCP configuration.

## Readiness gates

1. **Discovery complete:** WAN IPv4/IPv6, modem behavior, all OPNsense interfaces/VLANs/rules/aliases/NAT/routes/VPNs, Kea scopes/options/reservations, DNS enforcement, switch ports/LAGG, SSIDs, Proxmox bridges, UNAS management/storage paths, firewall-IP dependencies and monitoring are recorded with dates. Keep sensitive source files private.
2. **Design reviewed:** exact gateway IPs, native/tagged port design, WAN settings, zone matrix, DHCP options, DNS, NAT, VPN, IPv6 and controller migration path are approved. Resolve whether UDM physical ports/aggregation can reproduce the current separate MGMT and LAGG arrangement; do not assume existing LAGG is portable. Confirm UDM feature support and throughput for every required policy.
3. **Recovery rehearsed:** save private OPNsense configuration, UniFi Network backup, switch port profile/port map and screenshots or notes. Label every cable. Confirm direct OPNsense console access, modem activation details, spare client, power and a timed abort decision. Rehearse restoring the original cable path and single-DHCP/gateway state in isolation. A production rollback is untested until actually exercised; record rehearsal result and elapsed time.
4. **Preconfigure in isolation:** connect UDM only to an isolated test segment with separate address space; no production LAN/WAN or shared DHCP. Update its software, restore a compatible self-hosted Network backup, inspect migrated site/networks/profiles/SSIDs/adoption references, stage gateway/zone/DHCP/NAT settings and export a private backup. Confirm the backup is a Network backup, restore compatibility and single-site behavior on the actual versions. Identify whether devices use local L2 discovery, DNS, DHCP option 43 or a custom inform URL; document the exact inform-host transition and reversal. Ensure the test UDM cannot answer production DHCP or use `10.10.x.1` on a connected production segment. Keep `lothlorien` operational until adoption migration is confirmed and reversible. Do not forget devices from the old controller until the new controller has remained stable through acceptance.

## Stage 1: UDM gateway cutover with ARRIS retained

This is an execution plan, **not authorization to perform a cutover**. Set a maintenance window and owner-approved stop time only after all gates pass.

1. Capture a fresh read-only baseline: OPNsense WAN address/gateway/DNS/IPv6, DHCP leases, per-VLAN connectivity, DNS resolution, VPN/port-forward behavior, switch/AP adoption, Proxmox/UNAS paths, Grafana/Prometheus/Loki and Uptime Kuma. Check dashboard alerts and syslog ingest. Record timestamps and expected values privately.
2. Freeze other network changes. Confirm physical console and old OPNsense ready. Confirm UDM WAN setting matches discovered Comcast handoff. Keep ARRIS modem and coax unchanged.
3. Remove OPNsense production LAN and WAN connectivity or otherwise positively isolate its gateway and Kea before connecting UDM production LAN. Verify only one gateway and one DHCP server are present. Transfer the exact approved MGMT and VLAN uplinks. Maintain untagged MGMT and constrained AP ports unless an explicitly reviewed redesign is required.
4. Move ARRIS Ethernet handoff to UDM WAN. Power-cycle the ARRIS modem if it retains the prior router MAC/lease; wait for modem registration and UDM WAN DHCP, gateway, DNS and IPv6 results. Do not renew a production lease during discovery. If WAN does not obtain the expected service within the pre-agreed limit, stop and roll back.
5. At checkpoints, verify (a) local management, switch/AP adoption and no reprovision loops; (b) each subnet's gateway, a single DHCP responder, correct DNS options and resolver path; (c) allowed and denied IPv4 **and** IPv6 flows across VLANs and to gateway-local services; (d) NAT, port forwards, VPN and externally tested services; (e) Proxmox cluster, `palantir`, `elessar`, `rivendell`, `minas-tirith` and UNAS storage; (f) monitoring, syslog and alerts. Compare with the pre-cutover baseline.
6. Acceptance: no unapproved inter-VLAN reachability, all required flows work, WAN lease is stable, no duplicate DHCP/gateway, devices stay adopted, and monitoring sees the new gateway. Define a soak interval and threshold from actual baseline before scheduling. Retain OPNsense intact and available through soak.

### Stage 1 rollback

Trigger rollback at the agreed stop time, loss of management, duplicate gateway/DHCP, policy breach, unresolved WAN failure or critical service/storage failure. Isolate UDM LAN and WAN first. Restore original OPNsense MGMT and LAGG cables/port profiles and ARRIS handoff; power-cycle ARRIS if needed to release the UDM MAC binding. Start/verify OPNsense gateway and Kea only after UDM is isolated. Validate WAN DHCP, all gateway IPs, one DHCP responder per scope, DNS, representative allowed/blocked flows, switch/AP adoption, Proxmox/UNAS and monitoring. Keep the UDM isolated for diagnosis. Use the private baseline and rehearsal checklist; no factory reset is part of normal rollback.

## Stage 2: UniFi Cable Internet modem replacement

Schedule separately after Stage 1 soak and documentation sign-off. Verify exact UCI model, provider/account compatibility, activation method, coax signal and UDM WAN handoff. Capture the working ARRIS/UDM WAN baseline. Disconnect ARRIS, activate UCI with Comcast/Xfinity using provider instructions, then validate registration, UDM WAN DHCP/gateway/DNS/IPv6, public reachability, speed/latency against baseline and external services. Keep ARRIS available and its account status known until the new modem is stable. For modem-stage rollback, restore ARRIS coax/Ethernet and provider activation as required, then power-cycle and verify the unchanged UDM LAN and policy. Do not combine a modem provisioning fault with gateway migration troubleshooting.

## Sources

- Local: [network architecture](network.md), [February 2026 management-plane incident](../incidents/2026-02-08-unifi-management-plane-instability.md), [switch migration](../changelog/2026-02-08-migrate-switch-tplink-to-unifi.md), [observability](observability.md).
- Ubiquiti: [zone-based firewall](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi), [Network backup migration](https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi), [UniFi Cable Internet activation](https://help.ui.com/hc/en-us/articles/18770595926551-Activating-UniFi-Cable-Internet). Recheck the installed version's interface and documentation at execution time.
