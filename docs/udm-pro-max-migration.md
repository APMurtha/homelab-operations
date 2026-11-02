# UDM Pro Max migration preparation

Status: **ISOLATED SETUP COMPLETE (owner report); CUTOVER NO-GO pending reconciliation**. Initial setup and firmware updates are complete. The owner reports seven UDM networks (MGMT/10, SERVERS/20, CLIENTS/30, LAB/40, IOT/50, GUEST/60, APPLE_IOT/70), each using `10.10.X.1/24`, with DHCP disabled on all seven. No live UDM configuration has yet been read. The [initial OPNsense discovery](anduin-discovery-2026-11-02.md) remains the source baseline; the February design remains in [network.md](network.md). No UDM writes, production cutover, switching or controller migration are authorized by this document.

### Current handoff — denethor to laptop, 2026-11-02

- **VERIFIED repository:** the migration work is on `docs/udm-pro-max-migration-prep`, not `main`. The published migration tip was `c6fea80`; there were no subsequent commits when pulled. Read that branch before continuing. Do not repeat the completed initial OPNsense research.
- **Owner report:** the isolated UDM management address is `10.10.30.136`; versions, WAN versus LAN interface ownership, backup restore status and adopted devices remain **UNKNOWN**. One credential-free HTTPS GET from denethor, with a five-second connection timeout, timed out before receiving an HTTP response or verifying a certificate. This does not prove the UDM is offline. Because CLIENTS `10.10.30.0/24` is also staged, determine whether `.136` is temporary WAN addressing and whether the connected subnet overlaps before further access. Never connect the overlapping UDM LAN to production to obtain access.
- **VERIFIED local gap:** denethor lacks the laptop's `andrew-network` binding, explicit OPNsense CA file and authenticated OPNsense SSH session. No scoped UniFi key/target is available here. The earlier successful access was on the laptop; it is not evidence of access on denethor. The owner selected returning to the laptop rather than recreating access here.
- **Next laptop action:** fetch this branch, inspect local changes before any pull, check the existing scoped NEST status and available SSH session without displaying credentials, then establish the UDM's actual address/interface and OS/Network versions. Use the existing access routes; do not recreate API accounts, copy another person's credentials or repeat completed setup. If the prior password SSH session has expired, the owner must reopen it using a hidden local password prompt before further OPNsense reads.
- **Decision preserved:** one Cat6 uplink, no LAG; tagged MGMT migration remains deferred. Creating a UDM MGMT network with VLAN ID 10 does not authorize changing production MGMT tagging. Verify its LAN-port native assignment against the currently untagged switch/AP path; the network definition alone does not establish the wire format.

Read-only discovery, local artifacts and documentation are authorized. Before any UDM write, show the exact target, redacted before/after, recovery and test, and obtain approval. Production switching, controller migration, DHCP/gateway activation on production and cutover require separate explicit approval. No such approval has been received.

## Discovery access status — 2026-11-02

**VERIFIED locally (not a live network finding):** NEST 2.0.0 initially failed its scoped `home.py --person andrew --system andrew-network status` check because the required Andrew/network binding did not exist. `systems.py show` reported a missing binding. After creating the local binding with `systems.py bind --person andrew --system andrew-network`, both `show` and the scoped `status` command succeeded. `unifi-access doctor --local` reports Python ready and no scoped API key; scoped status reports no selected UniFi target or household profile. At this step, no service authentication or network connectivity was tested. This was a missing local skill configuration, not an observed network or production authentication failure.

**VERIFIED transport only:** The owner supplied `https://10.10.10.1/` for `anduin`. The initial HTTPS request failed certificate validation. The owner then supplied the local trust certificate `~/.config/nest/certs/anduin.pem`. With `curl --cacert` and normal hostname verification, an HTTPS GET of `/` returned `200` and `ssl_verify_result=0` on 2026-11-02. HEAD returned `403`, so use the bounded GET result for this transport check. No credential was sent and no OPNsense configuration was read. The sandboxed attempt could not open TCP 443; the verified GET succeeded outside the sandbox. TLS trust is resolved for this endpoint through this explicit CA file; no global trust override or insecure option was used.

**API authentication remains on hold:** NEST 2.0.0 has no bundled OPNsense helper, scoped OPNsense credential path or per-endpoint CA setting. Its UniFi API key is for UniFi Site Manager and must not be reused. No OPNsense API account/key or connector was created. The approved SSH read was used instead; it does not imply API access.

**SSH access:** Andrew explicitly authorized using the existing SSH host key or accepting a new key for this host without independent console verification, while stopping on a changed key. Root/password authentication occurred at a hidden prompt in Andrew's terminal. The SSH session returned hostname `anduin`, UID 0 and OPNsense `26.7.1_1 (amd64)`. The [dated discovery](anduin-discovery-2026-11-02.md) details the bounded findings and limits. Independent host-key provenance remains **UNKNOWN**.

The [OPNsense API access review](opnsense-api-access-review.md) maps proposed GET endpoints to upstream ACL privileges and records the areas the API cannot establish alone. It is a proposal until the installed OPNsense version and ACLs are checked.

**Owner report, not API-verified:** `lothlorien` is linked to UniFi Site Manager. This makes the NEST Site Manager route a candidate, but the scoped API key is absent and no authenticated host/site inventory has been read.

**UNKNOWN:** Complete effective OPNsense firewall behavior and remaining OPNsense details, plus UniFi controller, Pi-hole, Proxmox and UNAS live configuration. The NEST UniFi helper uses the official Site Manager/Network API; whether the linked self-hosted `lothlorien` is exposed to this key/account is untested. Obtain an owner-confirmed endpoint and authorized local access method for each remaining target; do not infer credentials from the OS user, Git remote or other NEST systems.

## Evidence labels

- **VERIFIED**: observed read-only on the named live system, with date and method.
- **HISTORICAL**: asserted in this repository's dated documentation or change history; may have drifted.
- **PLANNED**: proposed equipment or procedure; not deployed.
- **UNKNOWN**: requires inspection or an end-to-end test.
- **OWNER REPORT**: current status supplied by the owner; not independently read back.

Do not promote a historical assertion to verified by repeating it here. Keep raw exports, backups, leases, credentials, public IPs and device identifiers in private storage; record only reviewed, non-secret facts in this repository.

## Current inventory and topology

| Component | Address / connection | Evidence and confidence |
|---|---|---|
| Comcast/Xfinity → ARRIS Surfboard → `anduin` OPNsense FW4C | WAN uses DHCPv4 and DHCPv6; runtime IPv4 and global IPv6 present. Modem model/bridge mode and actual lease details **UNKNOWN** | OPNsense side **VERIFIED** 2026-11-02; modem/ISP owner report |
| `anduin` → `osgiliath` USW-24-G2 | MGMT `10.10.10.1/24` untagged on `igc1`; VLANs 20–70 on `igc2` + `igc3` `lagg0`; switch ports 3–4 remain unverified | OPNsense side **VERIFIED** 2026-11-02; switch side **HISTORICAL** |
| `ithil` U7 Pro; `lothlorien` self-hosted Network | AP native MGMT and tagged client VLANs; controller placement/version/adoption **UNKNOWN** | **HISTORICAL** design plus owner hardware report, medium |
| `orthanc` Proxmox; `moria` ZFS | `10.10.10.2`; separate management and Intel i350-T2 workload NICs | owner and January 2026 change, medium |
| `cirith-ungol`, `dol-guldur` Proxmox | `10.10.10.3`, `.4`; three-node `mordor` cluster | owner report, medium; live cluster status unknown |
| `palantir` Pi-hole + Unbound | `10.10.20.10` | owner report, medium; forwarding/enforcement unknown |
| `rivendell`, `minas-tirith`, `ithilien` | `10.10.20.30`, `.40`, `.70` | owner report, medium; live role/address unknown |
| `elessar` | reserved at `10.10.20.50` in Kea; authentication and reverse proxy role untested | reservation **VERIFIED** 2026-11-02; service role historical |
| UniFi UNAS Pro 8 | management IP, port, VLAN, data paths and dependencies **UNKNOWN** | owner report, medium |

**ISOLATED SETUP COMPLETE (owner report):** UDM Pro Max, with production migration pending. **PLANNED:** Replace Anduin while retaining the ARRIS modem; replace the modem with UniFi Cable Internet only after the gateway is stable. Pro XG 24 PoE, aggregation switch (model undecided), patch panels/Cat6A/Etherlighting, UniFi UPS/UPS Pro, PDU Pro and rack compute are later planning items; no installation is established for those later items.

### Target gateway-to-switch link — owner decision, 2026-11-02

**PLANNED:** Retire the current two-link OPNsense LAGG and dedicated MGMT cable at the UDM cutover. Connect the UDM Pro Max to `osgiliath` with **one Cat6 Ethernet cable**, initially at 1 Gbps on the existing switch. There will be no LAG, LACP or second gateway-to-switch connection. Carry VLANs 20–70 tagged on this link; retain `10.10.10.0/24` MGMT untagged during the initial cutover if the verified switch/device configuration requires it. The [planned topology](../diagrams/udm-single-uplink.mmd) is a design, not an observed port map. A faster uplink and replacement switch belong to a later hardware change.

**SEPARATE PLANNED CHANGE:** Move MGMT to an explicitly tagged VLAN 10 only after the UDM gateway migration is stable, with its own port/device inventory, management access path, rollback and acceptance tests. The current OPNsense interface is untagged; the existence and behavior of a UniFi VLAN 10 network are **UNKNOWN**. Do not create or tag VLAN 10 during the gateway cutover merely because the subnet is called VLAN 10.

Before cutover, use authenticated UniFi reads to identify the actual `osgiliath` MGMT uplink, LAG member ports, available spare port, native/tagged profile behavior, adopted devices and controller/inform path. Prefer a verified unused switch port for a pre-staged single-uplink profile so the original OPNsense ports can remain intact until disconnection. If no spare port or compatible native/tagged configuration exists, revise and rehearse the port sequence before approving the window. Never infer physical cabling from a profile name alone.

### Addressing reference

Preserve subnet and gateway addresses. MGMT is called VLAN 10 by the owner, but OPNsense has **no VLAN 10 interface**: `igc1` directly holds `10.10.10.1/24` (verified 2026-11-02). Switch port tagging remains unknown; do not tag MGMT merely to match a name.

| Network | Subnet | Intended gateway | DHCP saved on Anduin (verified 2026-11-02) / SSID (historical) |
|---|---|---|---|
| MGMT (VLAN 10 label; untagged on OPNsense) | 10.10.10.0/24 | 10.10.10.1 | Kea reservation-only; no dynamic pool |
| SERVERS / 20 | 10.10.20.0/24 | 10.10.20.1 | Kea reservation-only; no dynamic pool |
| CLIENTS / 30 | 10.10.30.0/24 | 10.10.30.1 | Kea pool .100–199 / Valinor (SSID historical) |
| LAB / 40 | 10.10.40.0/24 | 10.10.40.1 | Kea pool .100–199 / Isengard (SSID historical) |
| IOT / 50 | 10.10.50.0/24 | 10.10.50.1 | Kea pool .100–199 / Gondolin (SSID historical) |
| GUEST / 60 | 10.10.60.0/24 | 10.10.60.1 | Kea pool .100–199 / Bree (SSID historical) |
| APPLE_IOT / 70 | 10.10.70.0/24 | 10.10.70.1 | Kea pool .100–199 / Lorien (SSID historical) |

Kea DHCPv4 configuration and a running process were verified 2026-11-02. Confirm lease behavior and every reservation/option before building UDM DHCP. Never run Kea and UDM DHCP on the same production subnet simultaneously.

### Minimum remaining source reads

Use the existing authorized OPNsense SSH route and an allowlisted extractor as described in [SSH discovery](../runbooks/opnsense-ssh-discovery-plan.md). Keep exact MAC/client-ID mappings and raw state privately; the earlier count of 15 reservations is not a migration payload.

1. Read all current Kea subnets, pool exclusions, reservations and options 3/6/15/42/43 where set; resolve inherited versus subnet settings, renewal/rebind timers, valid/min/max lifetimes, client-ID behavior and current lease expirations. Preserve reservation-only MGMT **and SERVERS** unless a reviewed live diff shows otherwise. MGMT currently advertises router DNS `10.10.10.1`, while VLANs 20–70 advertise `palantir`; do not silently standardize these. Before allocation on the UDM, define how still-valid Kea leases are protected from reassignment. The 4,000-second default alone does not establish the longest remaining lease. Do not shorten production leases during preparation.
2. Collect complete saved rule fields and active PF order, alias expansions, NAT matching and relevant kernel routes. Reconcile broad allows, the disabled CLIENTS DNS block, missing VLAN 70 in `HOME_VLANS`, and the controller alias (`10.10.20.20`) versus MGMT reservation (`10.10.10.30`). Obtain an explicit policy decision where live behavior differs from intent; neither broad access nor a new restriction is approved automatically.
3. Complete WAN DHCPv4/DHCPv6 details: interface tag/untagged handoff, credentials if any (presence only), ISP options/client identifiers, MAC dependence, MTU, PD size/hints and LAN RA/IPv6 behavior. Existing DHCP modes do not establish all ISP requirements. Establish whether `AIRVPN_WOW_GW` or any VPN/policy route is actually used.
4. Read `lothlorien` version/site/adoption/inform path, actual switch ports/profiles and AP native/tagged management. Read UDM version, networks, DNS, zones/rules, DHCP state, WAN and adopted-device inventory. Record whether a backup restore occurred; a local `.unf` file does not prove restore. Denethor has an October 31 filename containing `v10.4.57`, which is only a backup-file observation, not a current version check.
5. On `palantir`, establish Pi-hole upstreams, Unbound recursion/forwarding, conditional forwarding, local DNS and any dependency on OPNsense's resolver. Check gateway NTP, mDNS, DDNS, IDS/syslog and critical published-service dependencies; existing OPNsense Unbound is active and some Kea scopes advertise gateway NTP. A successful public DNS lookup alone cannot establish these dependencies.

### Supported automation and idempotent implementation sequence

NEST 2.0.0 `start-here`, `diagnose-home-network`, `connect-home-service` and `manage-home-network` are the applicable installed workflows. Its offline `unifi-manage coverage` and bundled official contract were inspected on denethor; no authenticated API calls or write-right checks occurred. Write support is pinned to Network **10.6.106**. Do not downgrade or bypass the version gate. Check reachability first: Site Manager access must not require reconnecting an overlapping isolated LAN or WAN.

| Remaining setting | Supported preparation path / limitation |
|---|---|
| Networks, IPv4 DHCP ranges/options, DNS, zones, policies and ordering | Candidate NEST plan/apply resources on the reviewed version. Actual field support, readback and rights must be checked on the selected UDM. |
| Reservation-only DHCP and all MAC reservations | No dedicated reservation-write resource in the bundled helper; its DHCP-server schema requires a range. Resolve documented version-specific support or use an explicitly reviewed UI step. Never invent a one-address pool to emulate no pool. |
| WAN settings, NAT/port forwards | WAN inspection is read-only in the helper; WAN/NAT writes are not exposed. Use the supported UI or a separately reviewed documented API for the actual version. |
| Switch VLAN/native assignments, LAG removal, restore/adoption and device inform changes | Outside the helper's configuration coverage; read in the controller UI and prepare exact approved steps. No device actions or undocumented endpoints. |

The [official versioned Network contract](https://developer.ui.com/network/v10.6.106/openapi.json) was rechecked on 2026-11-02. Helper coverage is narrower than the whole API; neither schema availability nor an authenticated GET proves write permission.

1. Capture private, dated source and UDM snapshots. Match physical device/model, host, site and gateway IDs; hostname `anduin` alone cannot distinguish the two gateways.
2. Build the desired state from the reconciled live evidence and approved policy, keyed by actual IDs plus subnet/VLAN. Compare against existing objects; stop on duplicate names/subnets, mismatched ownership, unknown references or unsupported versions. Keep DHCP off and production devices on their existing controller.
3. Skip equal objects. Prepare one minimal patch per changed object, preserving unrelated fields, complete arrays and policy ordering. Resolve existing seven networks rather than creating duplicates. Plan prerequisites before references: networks/zones/lists, then policies and ordering. Treat reservations, WAN, NAT and ports as explicit manual/API gaps rather than claiming automation.
4. Show redacted before/after, complete writable replacement semantics, impact, inverse plan and validation. **STOP for UDM-write approval.** Regenerate expired plans and re-read for drift; NEST plans expire after one hour.
5. After approval, apply each supported change once with a new private journal and verify readback. Reconcile an unknown write outcome before retrying. A repeat run must produce no changes when desired state is already present. Test on isolated clients; activation on production remains a later approval boundary.

## Firewall policy translation worksheet

**PARTIALLY VERIFIED:** Saved rules, alias names and NAT categories were inspected 2026-11-02; broad enabled allows and a disabled CLIENTS direct-DNS block conflict with the deny-by-default design. Complete active rule order, floating/interface behavior, IPv6 policy and tested outcomes remain **UNKNOWN**. Fill the matrix from the [dated findings](anduin-discovery-2026-11-02.md) and later client tests before approval. UniFi zone defaults and rule order must be reviewed on the installed Network version. Create separate zones where distinct trust policies require them; placing all VLANs in one broad Internal zone can erase intended boundaries. Include gateway-local services, IPv6 and established/related behavior in tests.

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

## What blocks the cutover, and what does not block initial setup

**Initial isolated setup is complete by owner report; do not repeat it.** Retain physical isolation and verify the receipt/versions. A temporary OPNsense-fed WAN must not overlap any staged UDM LAN/VLAN. The [setup checklist](../runbooks/udm-isolated-initial-setup.md) now serves as a receipt and remaining verification list.

**Genuine cutover blockers:**

1. A manual `lothlorien` UI check records Network version, a current private backup, site count, adopted-device status and how `osgiliath`/`ithil` reach their controller. Confirm the backup can be restored to the UDM's Network version and define a reversible adoption transition. Do not retire `lothlorien` during staging.
2. Identify the actual `osgiliath` MGMT uplink, both OPNsense LAGG member ports, and one suitable UDM switch port. Verify its native/untagged MGMT behavior and tagged VLANs 20–70. Have labeled cable positions and an accessible management path for reconnecting Anduin. The UDM target uses one Cat6 link, never a LAG.
3. Approve the exact gateway IPs, Kea-to-UDM DHCP scopes/reservations/options, DNS path and **single active gateway/DHCP** sequence. Translate required firewall/zone policy, IPv6 behavior, WAN/NAT/port forwards, static routes and any **actually used** VPN dependency. The saved Anduin broad allows and disabled CLIENTS DNS block require an explicit policy decision; a deny-by-default design statement is insufficient.
4. Rehearse the physical rollback and establish a stop time: private Anduin/UniFi backups, old port/profile map, direct management access, ARRIS power-cycle and WAN DHCP checks, plus representative tests for management, every active subnet, required services and blocked flows. Keep Anduin intact until UDM acceptance and soak.

**Documentation that can follow an operational UDM:** full host-by-host Proxmox and NAS inventory, exhaustive historical alias/unused VPN annotation, rack upgrade details and polished as-built diagrams. Record only the critical service paths needed for cutover acceptance beforehand. Unknowns that affect a required flow must still be resolved before that flow is migrated.

### GO / NO-GO checklist

**Current result: NO-GO.** Every row below must have dated evidence or an explicit approved exception before the owner authorizes cutover. A value marked pending is not an execution instruction.

| Gate | Objective GO evidence | Current gap |
|---|---|---|
| DHCP | All seven scopes match approved options; every reservation maps correctly; MGMT/SERVERS have no general pool; existing leases cannot be reassigned; exactly one responder after cutover | Complete mappings/timers/lease transition and UDM support pending |
| DNS and NTP | Each VLAN reaches the approved resolver over UDP/TCP 53; public and required local names resolve; MGMT router-DNS replacement/retention and advertised NTP work; approved bypass behavior tested | Pi-hole chain and gateway-service dependencies pending |
| Firewall/IPv6 | Approved ordered rule matrix passes both allowed and denied tests, including gateway access and both families; no unexplained broad access | Effective source rules, intent decisions and UDM readback pending |
| WAN | DHCP/auth/tag/MTU/PD requirements captured; UDM matches; actual Internet/IPv6 tests pass in window | Advanced WAN and UDM state pending |
| NAT/inbound | Approved forwards work from an independent external connection; unapproved 2222/MOSH exposure remains closed; reflection/split DNS tested if required | Active NAT/filter reconciliation pending |
| Uplink/MGMT | Exact labeled UDM and spare switch port known; native MGMT plus tagged 20–70 verified; one 1 Gbps link; old three switch cables/profiles recoverable | Port map/native assignment pending; UDM VLAN 10 needs reconciliation |
| Controller | Actual restore/adoption/inform state known; approved migration and reversal documented; switch/AP stay online without loops | Versions, restore and transition pending |
| Administration | Direct UDM recovery LAN port/subnet and approved unused static laptop IP tested with WAN absent; independent OPNsense console/local login available | Recovery port/address and offline login tests pending |
| Recovery/approval | Fresh private backups verified available; cable/profile map complete; timed rollback rehearsed; owner approves exact diff and maintenance window | Approvals, rehearsal and timings pending |

Proposed timing for owner approval: check MGMT immediately after LAN connection and abort if unavailable for two minutes; WAN DHCP/Internet must work within ten minutes of modem registration; hard rollback decision at 30 minutes from first cable removal; retain OPNsense unchanged through a minimum 60-minute acceptance soak. These are proposed limits, not agreed values. Any duplicate gateway/DHCP, unauthorized internal reachability or loss of the independent recovery path triggers immediate isolation/rollback without waiting for the deadline.

## Stage 1: UDM gateway cutover with ARRIS retained

This is an execution plan, **not authorization to perform a cutover**. Set a maintenance window and owner-approved stop time only after all gates pass.

Before execution fill a private cable worksheet: ARRIS Ethernet jack/cable; OPNsense WAN `igc0`, MGMT `igc1`, LAGG `igc2` and `igc3`; each original switch port/profile; chosen spare switch port/profile; UDM LAN and WAN port numbers; separate direct-recovery port/subnet/laptop IP. No exact UniFi port numbers are verified yet, so this runbook is **not executable** until that worksheet is complete. Keep rollback switch profiles and LAG membership intact by using a verified spare uplink port where possible. Changing that spare port is still a production switching change requiring approval.

Before moving cables, save fresh private OPNsense, current `lothlorien` and staged UDM backups; verify file presence, version and recovery access. Resolve backup restore/adoption order before final UDM staging: a Network restore can replace staged settings. The [official migration procedure](https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi) covers restore and inform migration; do not blindly restore after hand-building DHCP/firewall configuration. If controller migration is included in this window, fill exact forward and reverse inform/controller steps and rehearse recovery before approving it. Otherwise propose deferring device adoption to a separate approved change, after verifying that existing controller and inform connectivity can survive the gateway change; that option is not yet selected.

1. Capture a fresh read-only baseline: OPNsense WAN address/gateway/DNS/IPv6, DHCP leases, per-VLAN connectivity, DNS resolution, VPN/port-forward behavior, switch/AP adoption, Proxmox/UNAS paths, Grafana/Prometheus/Loki and Uptime Kuma. Check dashboard alerts and syslog ingest. Record timestamps and expected values privately.
2. Freeze other network changes. Confirm physical console and old OPNsense ready. Confirm UDM WAN setting matches discovered Comcast handoff. Keep ARRIS modem and coax unchanged.
3. Label and record the verified OPNsense MGMT and LAGG switch ports. Disconnect **all three OPNsense LAN cables**: MGMT `igc1` and both LAGG members `igc2`/`igc3`; isolate its WAN `igc0` before connecting the UDM LAN. Keep OPNsense powered and its configuration intact for rollback. Verify that its gateway and Kea are no longer reachable on production. With the UDM still isolated, activate only the approved DHCP scopes after resolving old-lease protection, and confirm the final firewall/DNS configuration and direct recovery login. This activation needs explicit approval even while isolated. Connect exactly **one** Cat6 cable from the approved UDM LAN port to the approved `osgiliath` port/profile. The initial single link must carry native/untagged MGMT if required for management continuity and tagged VLANs 20–70. Do not connect a second gateway cable, form a LAG, or change AP/host MGMT tagging in this cutover. Verify only one active gateway and DHCP responder per subnet.
4. Move ARRIS Ethernet handoff to UDM WAN. Power-cycle the ARRIS modem if it retains the prior router MAC/lease; wait for modem registration and UDM WAN DHCP, gateway, DNS and IPv6 results. Do not renew a production lease during discovery. If WAN does not obtain the expected service within the pre-agreed limit, stop and roll back.
5. At checkpoints, verify (a) exactly one UDM-to-`osgiliath` link negotiated at the expected 1 Gbps, native MGMT management reachability, switch/AP adoption and no reprovision loops; (b) each subnet's gateway, a single DHCP responder, correct DNS options and resolver path; (c) allowed and denied IPv4 **and** IPv6 flows across VLANs and to gateway-local services; (d) NAT, port forwards, VPN and externally tested services; (e) Proxmox cluster, `palantir`, `elessar`, `rivendell`, `minas-tirith` and UNAS storage; (f) monitoring, syslog and alerts. Compare with the pre-cutover baseline.
6. Acceptance: no unapproved inter-VLAN reachability, all required flows work, WAN lease is stable, no duplicate DHCP/gateway, devices stay adopted, and monitoring sees the new gateway. Define a soak interval and threshold from actual baseline before scheduling. Retain OPNsense intact and available through soak.

At step 5, use an authorized representative client on each active VLAN. Obtain a fresh lease on the test client (do not release infrastructure leases), record address/mask/router/DNS/lease/server identifier, test its gateway and approved DNS via UDP and TCP, resolve a public name and a required internal name, then test the approved allow and deny destinations/ports in the matrix. Use an external cellular or other independent connection for published HTTPS and any other approved inbound service. Test management access from its approved source, GUEST denial to all internal ranges including VLAN 70, LAB/IOT restrictions, APPLE_IOT discovery exceptions, and IPv6 equivalence or explicit approved disablement. Passive DHCP capture on test links can identify competing responders; a ping or one received offer does not prove absence of a second server. Keep timed results privately and record a concise pass/fail receipt here.

### Stage 1 rollback

Trigger rollback at the agreed stop time, loss of management, duplicate gateway/DHCP, policy breach, unresolved WAN failure or critical service/storage failure. Disconnect the **single UDM LAN cable** from `osgiliath` and isolate UDM WAN first. Restore the **original separate OPNsense MGMT cable and both LAGG member cables** to their recorded switch ports/profiles; restore the ARRIS handoff and power-cycle ARRIS if needed to release the UDM MAC binding. Verify the UDM gateway/DHCP are absent before OPNsense re-enters production. Validate WAN DHCP, all gateway IPs, one DHCP responder per scope, DNS, representative allowed/blocked flows, switch/AP adoption, Proxmox/UNAS and monitoring. Keep the UDM isolated for diagnosis. Use the private baseline and rehearsal checklist; no factory reset is part of normal rollback.

Renew only affected test clients after restoring OPNsense, and refresh stale gateway neighbor entries if needed. Account for leases already granted by the UDM before allowing conflicting Kea allocations; include their reservation/exclusion handling in the approved lease-transition plan. If device management moved to the UDM, cable rollback alone is insufficient: use the pre-approved controller/inform reversal and saved switch configuration before declaring recovery. If no such reversal is documented and reachable without the UDM, combined controller cutover is NO-GO. Never forget or factory-reset devices as an improvised rollback.

## Separate later change: tagged MGMT VLAN 10

After Stage 1 acceptance and soak, discover every management endpoint and its current native/tagged port behavior, including the UDM, `osgiliath`, `ithil`, `lothlorien`, Proxmox hosts and NAS. Design an explicitly tagged VLAN 10 path with an independent management access method, staged port/device order, and a tested reversal to untagged MGMT. Preserve `10.10.10.0/24` and `10.10.10.1` unless a separate addressing decision is approved. Confirm controller reachability and adoption after each device or port transition. Schedule this as its own controlled operation; it is not part of the gateway or modem cutover.

## Stage 2: UniFi Cable Internet modem replacement

Schedule separately after Stage 1 soak and documentation sign-off. Verify exact UCI model, provider/account compatibility, activation method, coax signal and UDM WAN handoff. Capture the working ARRIS/UDM WAN baseline. Disconnect ARRIS, activate UCI with Comcast/Xfinity using provider instructions, then validate registration, UDM WAN DHCP/gateway/DNS/IPv6, public reachability, speed/latency against baseline and external services. Keep ARRIS available and its account status known until the new modem is stable. For modem-stage rollback, restore ARRIS coax/Ethernet and provider activation as required, then power-cycle and verify the unchanged UDM LAN and policy. Do not combine a modem provisioning fault with gateway migration troubleshooting.

## Sources

- Local: [network architecture](network.md), [February 2026 management-plane incident](../incidents/2026-02-08-unifi-management-plane-instability.md), [switch migration](../changelog/2026-02-08-migrate-switch-tplink-to-unifi.md), [observability](observability.md).
- Ubiquiti: [zone-based firewall](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi), [Network backup migration](https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi), [UniFi Cable Internet activation](https://help.ui.com/hc/en-us/articles/18770595926551-Activating-UniFi-Cable-Internet). Recheck the installed version's interface and documentation at execution time.
