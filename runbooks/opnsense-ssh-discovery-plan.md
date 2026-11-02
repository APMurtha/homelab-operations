# `anduin` SSH discovery proposal

Status: **PLANNED** on 2026-11-02. No SSH command or production configuration read has run. This is the bounded command set for review before a UDM Pro Max migration inventory. Follow [UDM discovery](udm-discovery.md) for the other systems.

## Access gate and minimal identity test

- The owner identifies the authorized account as `root`, using password authentication. This is a privileged shell, **not** a read-only account. NEST's `server-access` helper is key/agent based and the Andrew/network binding has no SSH profile. Use direct OpenSSH only for this explicitly requested target; never put the password in chat, a command argument, a file, or an automation tool.
- The workstation has existing `known_hosts` entries for `10.10.10.1`, but the owner says they were **not independently verified**. Their presence is not a trusted host pin. Do not connect yet or accept a new key by prompt. At Anduin's physical or already trusted console, obtain `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` and compare it with `ssh-keygen -F 10.10.10.1 -f ~/.ssh/known_hosts | ssh-keygen -lf -`. Resolve any mismatch through the console; never use `ssh-keyscan` alone as proof.
- After the fingerprint is independently confirmed, the owner can run the following **single read-only identity command in their own terminal**, entering the password at SSH's hidden prompt. The ED25519 algorithm, exact IP, explicit known-hosts file, strict checking, and disabled host-key updates avoid silent trust changes. The output should contain only hostname, username, UID, and OPNsense version. Stop if the host is not `anduin`, the account differs, or the key check fails.

```sh
ssh -F /dev/null -o HostKeyAlgorithms=ssh-ed25519 -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o UserKnownHostsFile="$HOME/.ssh/known_hosts" -o GlobalKnownHostsFile=/dev/null -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive -o NumberOfPasswordPrompts=1 root@10.10.10.1 'hostname -s; id -un; id -u; opnsense-version'
```

The command above is a proposal pending host-key verification; it was **not executed**. The owner may share the non-secret command output for documentation. It does not prove that later commands are safe simply because SSH succeeded.

## Full audit command set — requires separate approval

| Area | Proposed remote commands / extraction | Safety class and output handling |
|---|---|---|
| Interface assignments, MGMT, VLANs, LAGGs | `ifconfig -a`; allowlisted extraction of `interfaces`, VLAN parent/tag and LAGG member/protocol fields from `/conf/config.xml` | **Sensitive read.** `ifconfig` is passive; redact WAN/public addresses before display. Parse XML on the firewall into memory and print only approved field names/values. Never print the whole file. Cross-check whether `igc1` has an untagged `10.10.10.1` address and whether a VLAN 10 interface exists. |
| WAN, IPv4/IPv6, gateways, routes | `netstat -rn -f inet`; `netstat -rn -f inet6`; allowlisted interface, gateway, DHCPv4/DHCPv6/PD and static-route XML fields | **Sensitive read.** Routing commands are passive; redact public next hops. Separate configured addresses from runtime addresses. No `route add/delete`, `dhclient`, `service`, `configctl` or interface reload. |
| Kea DHCP | Allowlisted Kea settings, subnet/pool/reservation and option fields from `/conf/config.xml`; optional `sockstat -4 -6 -l` limited to DHCP listeners | **Sensitive read.** Do not cat generated Kea config or lease files; they may contain secrets or client identifiers. Mask MAC/client IDs and omit DDNS/HA credentials. Check options 3/6/15/42/43 and v6 only where configured. |
| Legacy firewall rules and aliases | Allowlisted rule/alias fields from XML; `pfctl -sr` only through a reviewed redactor | **Privileged sensitive read.** Include interface/floating order, action, family, source/destination, ports and description. Mask public addresses and any secret-like values before output. `pfctl -sr` inspects active PF rules; no `-f`, `-F` or reload. A saved config and active PF state may differ. |
| NAT and port forwards | Allowlisted outbound/1:1/port-forward/NPT fields from XML; `pfctl -sn` only through a reviewed redactor | **Privileged sensitive read.** Redact public endpoints; no NAT apply/reload. Compare saved mode/rules with active PF translation. |
| VPNs and static routes | Allowlisted VPN type, enabled flag, interface, route and peer-name fields; `netstat -rn` above | **High-sensitivity read.** Never print certificates, pre-shared keys, private keys, peer credentials or full VPN blocks. Exclude `wg show all dump`, VPN exports and complete XML. |
| DNS and Pi-hole/Unbound dependencies | Allowlisted `system` DNS server/override fields and Unbound forwarding/host-override fields from XML; `sockstat -4 -6 -l` limited to DNS listeners | **Sensitive read.** Avoid whole resolver files or logs. Verify actual Pi-hole forwarding and DNS-enforcement firewall rules later against `palantir`; router XML alone cannot prove resolver behavior. |

Before approval, prepare the **exact** local extraction/redaction script for review. The proposed execution form is a locally reviewed PHP program streamed over SSH into `php /dev/stdin`; it reads `/conf/config.xml` in memory and emits only an explicit allowlist, with no unredacted temporary file or raw XML output. Verify PHP availability on the device during the identity/preflight phase before relying on it. Likewise, route `ifconfig`, `netstat`, `pfctl` and `sockstat` through reviewed filters **on Anduin before any output is returned**; do not run their raw forms in the agent session. Each area runs separately with a bounded output limit. Do not run an ad hoc `cat`, `grep`, `sed`, `xmllint`, `scp`, config export or broad shell pipeline over the raw file. The connector/API proposal remains on hold.

No full-audit command above may run until the host key, authentication path, exact redactor and command set have been reviewed and the owner explicitly authorizes the collection. A root shell can modify production even when the intended command is read-only.
