# Mordor — Proxmox access plan

2026-11-16. **Network discovery received; authenticated cluster access still unavailable.**
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

Owner-relayed collector output at **2026-11-16T21:22:46Z** identifies `bag-end`,
account `murth`, ens18 `10.10.40.132/24` dynamic and a link-local IPv6 address.
The collector reports no selected SSH files, public-key fingerprints or SSH
configuration. `ssh-add -l` exits 1 with no fingerprints: no loaded identities
were reported; this does not rule out credentials outside its inspected scope.

| Bag-End TCP probe | 22 / SSH | 8006 / Proxmox HTTPS |
|---|---|---|
| Orthanc 10.10.10.2 | Connected | Connected |
| Cirith-Ungol 10.10.10.3 | Connected | Connected |
| Dol-Guldur 10.10.10.4 | Connected | Connected |

Evidence provenance is supplied Bag-End collector output, not this Codex session
independently logging in. No authentication was attempted. These observations
establish TCP reachability, not node identity, TLS trust or permissions. Node
host-key pins, accounts/ACLs, sudo rights and API access remain unverified.
The owner subsequently reports that a new account must be created/authorized;
no existing authenticated Proxmox browser path is available to this workflow.
Current node versions and cluster membership still require authenticated reads.

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
Denethor stopped before probes as intended. The owner subsequently supplied the
successful Bag-End discovery result above. Authenticated node execution remains
untested; subprocess/socket timeouts do not constitute an access mechanism.

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

## Concrete first access change — proposal only

The owner reports an account needs creating. The specific first change proposed
for approval is **one cluster-local API identity `codex@pve`**, with
**`PVEAuditor` at `/`** and a **privilege-separated `bag-end-audit` token** with
**24-hour expiry**. This intentionally permits cluster-wide read-only metadata
for the requested three-node comparison. It grants no VM power/configuration,
account administration, SSH shell or sudo access. It is not a root@pam token.
Keep the identity password unset for this API-only workflow.

An existing authorized Proxmox administrator must bootstrap it through a trusted
console or management session; none is currently available to Codex. Execute
once on one healthy quorate cluster member, not once per node. Before writes:

1. Inspect local `pveum help` for the commands and installed-version semantics.
2. Verify node identity, quorum, the PVEAuditor definition and that `codex@pve`
   does not exist. Stop on a name conflict; do not adopt or alter another identity.
3. Record only relevant prechange ACL/user metadata, privately; establish verified
   Proxmox HTTPS trust from Bag-End before transferring a token.

Reviewable intended operations, **not executed**, following those checks:

```sh
pveum user add codex@pve -comment 'Bag-End read-only Mordor diagnostics'
pveum acl modify / -user codex@pve -role PVEAuditor
# Administrator creates bag-end-audit with privilege separation enabled,
# an expiry exactly 24 hours after creation, and handles its secret privately.
# The documented creation operation is:
# pveum user token add codex@pve bag-end-audit -privsep 1 -expire EXPIRY_EPOCH
pveum acl modify / -token 'codex@pve!bag-end-audit' -role PVEAuditor
pveum user permissions codex@pve
pveum user token permissions codex@pve bag-end-audit
```

`EXPIRY_EPOCH` is a required reviewed creation-time value, not a literal argument.
Token creation returns a secret: do not run it through chat/recorded automation
or paste its response into reports. The administrator must use a private local
handoff to Bag-End's protected credential store. Do not commit it, put it in
request argv, save it on Denethor, share root credentials or disable TLS checks.
No token exists yet, and no credential transfer has occurred.

Verify effective read-only permissions and authenticated GETs for version,
cluster/nodes/resources, VM 130 filtered configuration/status and historical RRD.
Do not test denial by attempting a destructive write. Record protected endpoints
that remain inaccessible; the API may not expose host PSI or all process detail.
Do not silently escalate to Administrator or create SSH accounts for those gaps.

Rollback: revoke this newly created token first; remove only its new token ACL,
then the new user ACL and identity if it was created by this operation and is
otherwise unused. Re-read the ACL/user list to confirm unrelated identities and
permissions were preserved. Exact rollback CLI options must match the installed
`pveum help`; no broad ACL or account deletion is authorized by this proposal.
If a partial creation outcome is uncertain, inspect before any retry.

This is a concrete access-change proposal awaiting explicit approval of its
identity, cluster-wide audit scope, token lifetime and private bootstrap method.
No account, ACL, password, token or SSH service was changed by this task.

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
