# `anduin` SSH discovery proposal

**Historical source-appliance work only.** OPNsense is retired/disconnected;
`10.10.10.1` now belongs to the UDM Pro Max. Do not apply these OPNsense commands,
CA assumptions, ACLs or prior session authorizations to the replacement. Any
additional source recovery needs an explicitly isolated, separately authorized
console/export path. No production reconnection of overlapping gateways/DHCP.

Status: **PARTLY EXECUTED** on 2026-11-02 under Andrew's explicit SSH authorization. The minimal identity test and selected redacted reads were completed; see the [dated findings](../docs/anduin-discovery-2026-11-02.md). This page preserves the proposed command classes and safety rules. Follow [UDM discovery](udm-discovery.md) for the other systems.

## Access gate and minimal identity test

- The owner identifies the authorized account as `root`, using password authentication. This is a privileged shell, **not** a read-only account. NEST's `server-access` helper is key/agent based and the Andrew/network binding has no SSH profile. Use direct OpenSSH only for this explicitly requested target; never put the password in chat, a command argument, a file, or an automation tool.
- The workstation had existing `known_hosts` entries for `10.10.10.1`, which the owner said were **not independently verified**. Andrew explicitly authorized the existing key or `StrictHostKeyChecking=accept-new` for this host only, with a hard stop on changed/conflicting keys. No changed-key condition occurred. Independent provenance remains unknown. For later stronger verification, obtain `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` at Anduin's trusted console and compare it with `ssh-keygen -F 10.10.10.1 -f ~/.ssh/known_hosts | ssh-keygen -lf -` on the workstation.
- The owner opened a temporary local SSH control socket after entering the password at SSH's hidden prompt. The following is the **single read-only identity command** used through that socket. The exact IP, explicit known-hosts file, strict checking, and disabled host-key updates avoid silent trust changes. It returned `anduin`, `root`, UID 0, and OPNsense `26.7.1_1 (amd64)`. Stop if the host/account differs or the key check fails.

```sh
ssh -F /dev/null -o BatchMode=yes -o ControlMaster=no -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o UserKnownHostsFile="$HOME/.ssh/known_hosts" -o GlobalKnownHostsFile=/dev/null -S /private/tmp/anduin-discovery.N5Cfzy/socket root@10.10.10.1 'hostname -s; id -un; id -u; opnsense-version'
```

The temporary socket path above is session-specific and should not be reused as a durable credential. Successful SSH does not make later commands safe simply because they are sent through the same connection.

## Read-only audit command classes

| Area | Proposed remote commands / extraction | Safety class and output handling |
|---|---|---|
| Interface assignments, MGMT, VLANs, LAGGs | `ifconfig -a`; allowlisted extraction of `interfaces`, VLAN parent/tag and LAGG member/protocol fields from `/conf/config.xml` | **Sensitive read.** `ifconfig` is passive; redact WAN/public addresses before display. Parse XML on the firewall into memory and print only approved field names/values. Never print the whole file. Cross-check whether `igc1` has an untagged `10.10.10.1` address and whether a VLAN 10 interface exists. |
| WAN, IPv4/IPv6, gateways, routes | `netstat -rn -f inet`; `netstat -rn -f inet6`; allowlisted interface, gateway, DHCPv4/DHCPv6/PD and static-route XML fields | **Sensitive read.** Routing commands are passive; redact public next hops. Separate configured addresses from runtime addresses. No `route add/delete`, `dhclient`, `service`, `configctl` or interface reload. |
| Kea DHCP | Allowlisted Kea settings, subnet/pool/reservation and option fields from `/conf/config.xml`; optional `sockstat -4 -6 -l` limited to DHCP listeners | **Sensitive read.** Do not cat generated Kea config or lease files; they may contain secrets or client identifiers. Mask MAC/client IDs and omit DDNS/HA credentials. Check options 3/6/15/42/43 and v6 only where configured. |
| Legacy firewall rules and aliases | Allowlisted rule/alias fields from XML; `pfctl -sr` only through a reviewed redactor | **Privileged sensitive read.** Include interface/floating order, action, family, source/destination, ports and description. Mask public addresses and any secret-like values before output. `pfctl -sr` inspects active PF rules; no `-f`, `-F` or reload. A saved config and active PF state may differ. |
| NAT and port forwards | Allowlisted outbound/1:1/port-forward/NPT fields from XML; `pfctl -sn` only through a reviewed redactor | **Privileged sensitive read.** Redact public endpoints; no NAT apply/reload. Compare saved mode/rules with active PF translation. |
| VPNs and static routes | Allowlisted VPN type, enabled flag, interface, route and peer-name fields; `netstat -rn` above | **High-sensitivity read.** Never print certificates, pre-shared keys, private keys, peer credentials or full VPN blocks. Exclude `wg show all dump`, VPN exports and complete XML. |
| DNS and Pi-hole/Unbound dependencies | Allowlisted `system` DNS server/override fields and Unbound forwarding/host-override fields from XML; `sockstat -4 -6 -l` limited to DNS listeners | **Sensitive read.** Avoid whole resolver files or logs. Verify actual Pi-hole forwarding and DNS-enforcement firewall rules later against `palantir`; router XML alone cannot prove resolver behavior. |

The completed collection used a local PHP extractor streamed over SSH into `php /dev/stdin`; it read `/conf/config.xml` in memory and emitted allowlisted fields only, with no unredacted temporary file or raw XML output. PHP availability and syntax were checked first. Passive `ifconfig`, `netstat` and `pfctl` observations were summarized **on Anduin before output was returned**. For further collection, review the exact extractor and output fields first. Do not run an ad hoc `cat`, `grep`, `sed`, `xmllint`, `scp`, config export or broad shell pipeline over the raw file. The connector/API proposal remains on hold.

Andrew authorized the bounded read-only discovery after the initial plan was written. The collected subset is documented in the dated findings; unresolved items still require reviewed collection. A root shell can modify production even when the intended command is read-only. No production configuration change is authorized.
