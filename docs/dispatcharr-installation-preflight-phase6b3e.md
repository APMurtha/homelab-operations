# Dispatcharr Phase 6B-3E — installation preflight

**Storage reconciliation update (2026-11-16):** Its recovery NO-GO predates the completed Phase 6B-3F checkpoint. Current scoped-installation recovery readiness is GO after hash/access reconciliation; full unattended production readiness remains separate. See
[verified current evidence](storage-source-of-truth-reconciliation.md). Original
observations below are retained at their collection dates.

Inspection: 2026-11-16 04:20 UTC (2026-11-15 US/Eastern).
Target: Rivendell, 10.10.20.30. **Read-only; no activation or configuration changes.**

**Decision: NO-GO for installation at present.** The simplified candidate passes
its configuration/compatibility preflight. The unresolved gate is recovery:
current Dispatcharr-consistent backup coverage and installation-specific rollback
copies are not verified/staged. This does not require another VM or a security
controller. Resolve the recovery prerequisites, then seek installation approval.

## Candidate and dependency compatibility

Exact candidate:
[minimal-phase6b3d](../configs/dispatcharr-iptv/minimal-phase6b3d/README.md).
The recorded artifact manifest matches every file. All 12 minimal offline tests
passed again. No candidate file was changed in this phase.

Current target versions:

- systemd 255.4-1ubuntu8.18, Ubuntu 24.04.
- Docker 29.9.2; Compose v5.6.0.
- nftables 1.0.9.

Required Compose create/up/stop flags are supported on the target. The accepted
base Compose hash matches the repository. Existing guard, policy parser, startup
gates, Caddy, resolver and VPN post-rules match the candidate's reviewed source
pins and are root-owned mode 0644. WireGuard, app.env and egress-policy files are
root-owned 0600; contents were not reported.

Docker is Type=notify, Restart=always, requires docker.socket and wants containerd
and network-online. Docker/socket/containerd are active; Docker has no drop-ins.
The proposed guard, stack and historical controller units are not installed.
Generic nftables.service is disabled/inactive. Configuration is on local ext4 `/`,
so RequiresMountsFor does not introduce an NFS dependency or a Docker/mount cycle.

Combining the exact proposed Unit/drop-in directives with the inspected relevant
effective target dependencies produced an acyclic ordering graph:

```text
local storage → guard apply/verify → Docker → stack post-Docker apply/verify
                                              → Compose VPN → app → gateway
```

This is a static review of the relevant graph, not execution of a systemd job.
The exact unit/native syntax validation from Phase 6B-3D ran on Denethor, not by
installing or staging units on Rivendell. The directives are compatible with the
inspected systemd 255 semantics. Full target job behavior remains a live check.

## Guard and startup safety

**Verified now:** the entire live `inet rivendell_iptv` JSON matches the accepted
template after removing only handles/counters/metainfo and substituting the peer
privately. The ready marker matches the current policy digest. Native
`python3 -B guard.py check --policy …` completed successfully (exit 0): the exact
scoped replacement transaction passed nftables --check, with no rules applied.

The installer source touches only this table; no global flush, Docker-managed
chain replacement or SSH rule change is present. Existing allow/drop scope is
unchanged, so the intended transaction does not broaden permissions or change
unrelated networking. Atomic replacement and prior isolated tests support that
design. **A syntax check cannot prove a future live apply will cause zero
connectivity disruption.** Fresh SSH and neighbor checks must accompany the
first authorized application.

Startup protection requires all parts of the existing plan:

1. Recreate only the three **stopped** dedicated containers with restart=`no`
   before installing the Docker Wants drop-in. Current policies remain
   `unless-stopped`; merely adding units would leave an autostart bypass.
2. Guard unit applies/verifies before Docker. Docker's dependencies are soft so
   unrelated services can still start if that guard fails.
3. Stack has Requires+After/BindsTo guard and Docker. Guard failure blocks its
   startup job. Stack additionally reapplies/verifies the actual accepted table
   after Docker becomes ready, before Compose starts any protected container.
4. Preflight requires the exact existing network, static address, container
   references, images, mounts and exposure. A missing network/Gluetun fails;
   the unit does not repair or silently create a changed network.
5. Existing owner/app gates and Gluetun kill switch remain. Compose waits for
   declared health, and a final one-shot verifies the running topology.

The guard uses interface-name matches, so installing it does not require the
bridge to exist. The network must exist before stack preflight; initial controlled
Compose `create` supplies stopped resources under the already-active accepted
guard. The startup command uses no-recreate/no-build/pull=never. Future network or
VPN-owner recreation requires an explicit stopped-project operation and fresh
checks, not an automatic policy rewrite.

Within that supported service path, failed installation/verification blocks new
Dispatcharr startup. Privileged manual Docker commands can bypass systemd; a
stale marker after an external flush is not equivalent to verified host rules.
No protection against privileged removal of both host and namespace filters is
claimed. The one-shot units do not monitor later rule loss or app crashes.

## Current runtime evidence

All three dedicated containers are healthy, with latest Docker health exits 0,
reviewed image references unchanged and no explicit cgroup parent:

| Component | ID prefix | Started UTC |
|---|---|---|
| Dispatcharr | 2c1331d8e7d7 | Nov 8 22:17:43 |
| Dedicated VPN | dfa35e0d8614 | Nov 8 22:15:22 |
| Gateway | f60893c317fb | Nov 16 00:44:51 |

All share netns 4026533142. The bridge remains `br-iptv-eg`, network
`rivendell-iptv-egress`, subnet 172.16.70.0/24 and gateway 172.16.70.1, with IPv6
disabled. Only the dedicated VPN publishes `10.10.20.30:9191 → 9192/tcp`; app and
gateway publish no additional ports.

The tunnel interface is up. All-table routing inspection confirmed a tun0 default
route and five non-main policy rules. Namespace OUTPUT remains default-drop,
with tunnel acceptance and the 127.0.0.11 rejection present. The container's `wg`
query was unavailable, so this phase does not claim a newly observed handshake or
exit-IP verification. Existing native VPN health is healthy; no external
connectivity, DNS, provider, failure or playback probe was initiated.

Original Gluetun, qBittorrent and Jellyfin remain healthy; NZBGet remains running.
Their container IDs and start times agree with the prior baseline. No service,
worker or container was signaled or restarted. HLS/gateway artifacts were not
changed, and no relay or trial was started.

## Backup and rollback readiness — blocker

| Recovery item | Current evidence | Readiness |
|---|---|---|
| Nov 8 VM 130 archive | Accessible through already-mounted NFS; exactly 31,404,796,447 bytes | Available; historical zstd/VMA integrity receipt retained, no new integrity or restore test |
| Current off-host media backup | Service failed, exit 1; timer active; script hash unchanged from failed mount-guard version | Not repaired |
| Off-host archive listing | Nov 2 main/setup archives remain | Old, and existing job excludes dedicated Dispatcharr services |
| Native Dispatcharr ZIPs | Prior Phase 6A readability evidence | Not demonstrated to be a complete current matched DB/assets/secrets recovery set |
| Jellyfin recovery ZIP | Present, 2,012,906,547 bytes | Useful for Jellyfin, not a Dispatcharr backup |
| Installation recovery receipt | No `/root/dispatcharr-minimal-recovery-*` found | Must capture before modifying containers/files |
| Reviewed candidate root staging | `/root/dispatcharr-minimal-phase6b3d` absent | Not staged; expected for this read-only phase |
| Candidate rollback commands | Present in Phase 6B-3D plan | Available procedure; not yet tied to a captured machine baseline |

The existing backup script hash is still
`4e43a88bffeb5616d51120136bb3fd51c2040c04df92f79ccd5daafdff40d79d`,
the failed source-validation version. Existing mounted export is
`10.10.10.2:/moria`. Historical Orthanc evidence reports the single-device pool
degraded; no new Orthanc inspection or repair was performed. Accessibility of an
old archive does not resolve destination trust or consistency.

Before installation, establish a verified current Dispatcharr recovery set and
trusted recovery destination, then capture the exact base Compose, restart
policies, protected source hashes, scoped table and unit/drop-in absence facts.
Application/SQL recovery must not be replaced with a raw copy of live PostgreSQL
files. This preflight did not create backups, copy files on Rivendell, repair the
backup script or expand backup scope.

Rollback is technically scoped: retain/reapply accepted guard, stop only the
three dedicated services, confirm them stopped, remove only newly introduced
units/drop-in, recreate from the unchanged base and restore original policies.
If Docker is unavailable, shutdown cannot be confirmed; stop and report rather
than removing protection or substituting broad kills. Do not use a global saved
ruleset restore. The plan's file-removal commands require proof those files were
absent before installation; inspection confirms they are absent now.

## Storage assessment

Root filesystem: **87% used**, approximately **7.45 GiB available**
(7,996,633,088 bytes at the second reading), with approximately 2.93 million free
inodes. Configuration resides on that root filesystem.

The complete candidate folder is 36,550 bytes, including tests/documentation.
The seven runtime/unit files plus directories require well under 1 MiB. The
proposed start uses existing pinned images and performs no build or pull. Thus
installation itself does not materially worsen capacity. This does not authorize
cleanup or certify capacity for large local backups/image extraction; stage
recovery data with an explicit reserve rather than consuming the remaining root
space. Disk pressure remains an operational issue, not the present file-size
blocker.

## Exact installation files and impact

These remain **uninstalled**:

1. `/docker/dispatcharr-iptv/minimal-phase6b3d/verify.py`
2. `/docker/dispatcharr-iptv/minimal-phase6b3d/contracts.py`
3. `/docker/dispatcharr-iptv/minimal-phase6b3d/accepted-table.template.json`
4. `/docker/dispatcharr-iptv/minimal-phase6b3d/compose.persistence.proposed.yaml`
5. `/etc/systemd/system/dispatcharr-egress-guard.service`
6. `/etc/systemd/system/dispatcharr-stack.service`
7. `/etc/systemd/system/docker.service.d/50-dispatcharr-order.conf`

All target locations are currently absent. No historical controller/slice,
enrollment record, daemon, timer or additional network is part of installation.

Expected activation impact: a bounded outage and recreation of only dedicated
Dispatcharr, VPN and gateway containers to adopt restart=no, followed by health
startup of up to six minutes plus checks. Persistent data and image pins remain.
No Docker daemon restart, unrelated container restart, Jellyfin change or host
reboot is necessary for initial installation. Existing download services and SSH
should remain available; verify rather than assume that outcome.

Installing the Docker Wants drop-in changes future Docker-start behavior even
before explicit enablement. Do not stage that active drop-in early while the
old restart policies are still in effect.

## Recommended first live validation

After backup/rollback readiness is resolved and separate activation approval is
given, follow the existing Phase 6B-3D maintenance sequence: stop only the three
services, retain the accepted guard, create the reviewed stopped containers with
restart=no, verify, install the candidate, then start **only
`dispatcharr-stack.service` once**. Do not restart Docker or the host.

Accept only after exact guard/marker checks, real namespace/image/port checks,
three healthy containers, supported read-only application diagnostics, fresh SSH
and unchanged neighboring-service identities/health. No playback is needed.
If a preflight or health step fails, use the scoped rollback with retained rules.

Without touching unrelated services, later separately authorized checks can
exercise stack stop/start, guard-unit restart with its dependent stack, and
scoped guard reapplication while the dedicated stack is stopped. Failure fixtures
must not be injected into a running production firewall. Docker restart, abrupt
API loss, network recreation and cold boot remain separate maintenance tests;
none was run here, and none requires a new VM as a precondition for this plan.

## Evidence and conclusion

Private sanitized inspection receipts:
`.ai-local/dispatcharr-phase6b3e/target-preflight.json`, `target-followup.json` and
`ordering-review.json`. Candidate hashes and 12 offline tests passed; relevant
target/candidate ordering was checked without installing units. No credentials,
keys or upstream authentication URLs were displayed.

**NO-GO now: recovery prerequisites are incomplete.** No new candidate dependency,
CLI, source-drift, scoped-rule or file-capacity blocker was found. Once recovery
and baseline capture are ready, the recommended next step is a separately approved
single stack-unit activation, with Docker and unrelated workloads left running.
