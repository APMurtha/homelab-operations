# Mordor — Proxmox access plan

2026-11-16. **Discovery/preparation incomplete: Bag-End-side evidence required.**
No account, key, SSH service, package, API token, ACL or Proxmox configuration was
created or changed. No hypervisor or guest lifecycle operation was performed.

## Execution architecture and evidence

| Component | Role / address | Evidence |
|---|---|---|
| Bag-End | Primary management/automation VM; Samwise's existing desktop; `murth`; DHCP `10.10.40.132/24` on ens18 | Owner-confirmed this task; not independently connected by this Codex session |
| Orthanc | Proxmox node `10.10.10.2`; Rivendell VM 130 owner | Owner target selection; current node access unverified |
| Cirith-Ungol | Proxmox node `10.10.10.3` | Owner target selection; current node access unverified |
| Dol-Guldur | Proxmox node `10.10.10.4` | Owner target selection; current node access unverified |
| Ithilien | Existing bastion/fallback, not default management path | Owner instruction; no connection attempted |
| Denethor | This Codex session's local preparation/publication host | Local hostname verified; no node diagnostics run from it |

An earlier Codex VM-creation task records Bag-End as VM 100 on Cirith-Ungol,
4 vCPUs/8 GiB on the LAB bridge. That is historical setup evidence, not current
configuration or evidence of access to Samwise's ChatGPT session.

Owner reports Bag-End has no listening SSH server and no working SSH login.
Its ED25519 host-key fingerprint was read from its local public host-key file:

`SHA256:mcji/xWBgZEmRrJrWvVSFJMkktxeBnt+7q2wROWnzWM`

This is an owner-verified local key fingerprint, not a live endpoint observation.
No keyscan or host-key trust override was used. An SSH server on Bag-End is not
required for Samwise to run local terminal diagnostics or initiate outbound SSH.
Do not enable one merely to satisfy this investigation.

## Access inventory completed here

The selected NEST `andrew-media` binding contains a named pinned Rivendell
profile, not Bag-End or the three nodes. It must not be retargeted. Another
person/system's credentials were not used. Denethor has a local Ed25519 key pair;
that does not establish Bag-End/node authorization. Its current sandbox could
not connect to an SSH authentication agent. These are local observations only.

Bag-End's keys/agent, node host-key pins, existing node accounts, sudo rights,
API credentials and reachability are **unverified**. No guessed root/murth/codex
node login was attempted. Current Proxmox versions, cluster membership and ACLs
remain to be inspected through Bag-End using actual existing permissions.

## Read-only handoff for Bag-End

Use [the discovery collector](../configs/proxmox/bag-end-access-discovery.py)
from Bag-End's existing `murth` terminal after inspecting its source. Samwise may
read the published file and execute it locally; do not execute it on a hypervisor.
It requires hostname `bag-end`, account `murth` and the reported ens18 IPv4/prefix;
on identity/address drift it stops before any network probe.

It reports only:

- ens18 address metadata, selected SSH-file permissions and public fingerprints;
- selected textual SSH configuration directives and loaded agent fingerprints;
- TCP reachability to each explicit node on 22 and 8006, without authentication.

It does not execute SSH configuration (`ssh -G` can run Match exec), follow
Include directives, read private keys/authorized_keys/API credentials, install
anything, modify files or attempt node logins. TCP reachability is not host
identity, TLS certificate validation or permission verification. Public-key
comments are omitted. Review output privately before sharing; internal addresses,
account names and public fingerprints are intended, secret values are not.

Local validation: Python syntax compiled in memory; wrong-host execution on
Denethor stopped before probes as intended. No successful Bag-End execution or
live node result is claimed. Its bounded subprocess and socket timeouts do not
constitute tested authentication or a new access mechanism.

After that output, select the actual authorized node account and independently
verify each node's host key from an existing trusted console/channel. Run one
noninteractive identity check per node with strict host-key checking, no password
fallback and no agent forwarding. Stop on failure; do not cycle through users
or keys. Then inspect available privileges before issuing privileged reads.

## Proposed least-privilege model — not provisioned

Keep Codex/management tools on Bag-End, never the hypervisors. Use existing
OpenSSH/API clients if available; no new daemon or management framework is needed.
Treat Ithilien as an explicitly selected recovery fallback, not an implicit jump.
Bag-End's DHCP address must be rediscovered before pinning access policy; do not
silently treat `.132` as a permanent static reservation.

For initial SSH diagnostics, prefer a separately attributable unprivileged
`codex` Unix account on each node, **only after approval and account-conflict
review**. Use a dedicated protected key available only through the approved
Bag-End identity/agent, pinned node host keys, no password/interactive fallback
for automation, no agent forwarding and no broad passwordless sudo. Existing
read permissions should serve CPU/proc telemetry. An API account does not itself
create a Unix SSH account. Cluster membership does not synchronize ordinary
node-local SSH account provisioning.

For API diagnostics, propose a separate Proxmox service identity and expiring,
privilege-separated token, with PVEAuditor limited to the nodes/VMs/storage paths
actually needed. Cluster-wide auditing, if required for resource comparison,
needs an explicitly reviewed wider audit scope. Grant both backing identity and
token the required read permissions; validate effective permissions and endpoint
requirements against the installed version. Keep token material on Bag-End,
outside Git and argv, with verified TLS. API token permissions are bounded by
both token and user permissions. [Official Proxmox user-management source](https://github.com/proxmox/pve-docs/blob/master/pveum.adoc).

For later administration, retain separate approval and separately scoped
credentials/roles for explicit operations. Do not turn the diagnostic token into
Administrator, permit arbitrary root shell through sudo, or add a generic
passwordless `pvesh`, Python or shell rule. If protected logs/process data require
root, document exact missing reads and have the owner supply them through the
existing trusted console until a narrow access change is approved.

## Next Bag-End-side inspection

After authenticated identity/permissions are established, collect bounded reads:

1. `pveversion -v`, cluster status/membership and effective API/Unix permissions.
2. CPU topology, node utilization/load/PSI, VM/LXC resource inventory.
3. VM 130 CPU model/topology/limits/affinity and current QEMU PID/cgroup metrics.
4. Active and recent backup/migration/storage tasks, RRD historical CPU/iowait,
   and read-only storage/ZFS status.
5. Equivalent timestamped samples from all three nodes and clock correlation
   with Rivendell's 20:40:19–20:45:19 UTC admission window.

Only read/get/list operations are in scope. Do not dump cloud-init data,
full QEMU arguments, password/token databases, private keys or full VM configs
into reports. Filter user/ACL/config output to relevant nonsecret fields.

## NEST context and approval status

A concise owner-confirmed architecture paragraph was prepared in the existing
NEST source file:
`home-foundation/context/systems/andrew-media/start-here.md`
in `/home/murth/Projects/nest`.

It identifies Bag-End as primary, Ithilien as fallback, and the no-hypervisor-agent
boundary. Current address/account are explicitly owner-reported and node access
unverified. This source already had unrelated uncommitted storage corrections;
those were preserved. No NEST release, source commit, installed plugin-cache
edit, binding update or credential change is included. The source correction
awaits the existing review/release process. Local `./scripts/validate` passed
184 tests; no release or installation followed. It is not claimed as active installed
knowledge. Homelab publication contains only the selected sanitized reports and
collector, not the NEST working tree.

**NO-GO for access provisioning without approval.** Existing Bag-End terminal
inspection may proceed read-only. A direct channel to Samwise has not been
established; an available Codex task connection is not his ChatGPT session.
