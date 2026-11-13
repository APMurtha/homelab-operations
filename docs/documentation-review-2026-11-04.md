# Homelab documentation review — 2026-11-04

## Scope and evidence

Reviewed all existing tracked Markdown, Mermaid diagrams, indexes and ignore
rules, plus the locally prepared DDNS Compose artifact. Reconciled current
references against authenticated Anduin snapshots from recovery, authorized
host/container checks and dated owner console/client tests. Additional review
checks: Grafana health HTTP 200; documented Prometheus/Loki/Kuma ports yielded no
HTTP response within a bounded timeout. No live configuration, service, account,
firewall, port, controller, disk or backup restore changes were performed.

The migration notes had been maintained locally on
`docs/udm-pro-max-migration-prep`; README/architecture/diagrams still described the
retired design. This review preserves those existing local changes as an
[archived evidence log](_archive/udm-migration-working-notes-2026-11-04.md), replaces
the active handoff with current acceptance, and updates linked operating docs.
**Changes are local and uncommitted/unpushed at review completion.** A remote
repository is not up to date until the changes are committed and published.

## Corrected in this review

| Area | Correction |
| --- | --- |
| README/network architecture | UDM gateway/controller, UCI, one uplink, tagged switch/AP MGMT, native access paths, real IP/DHCP/SSID/policy state |
| Naming/service map | Calacirya/Lorien, cluster members, retired Lothlorien, distinct Moria NAS versus Orthanc ZFS; guest placement/Plex not assumed |
| Diagrams | Replaced active OPNsense/LAGG/ARRIS/controller-only graphs with current physical/logical service paths; no invented VM-to-node placement |
| Management recovery | Removed default factory-reset/controller shutdown/LAGG reconstruction procedure; preserves current tagged management and recovery path |
| Historical boundaries | Marked old incident conclusions, OPNsense source commands and archived diagrams as historical; same IP now identifies a different appliance |
| Migration/read-only runbooks | Compact current acceptance and bounded verification; intermediate failures/approvals preserved in archive |
| Observability/IDS | Retired OPNsense source distinguished from unverified UDM replacement; endpoint evidence separated from complete telemetry health |
| Markdown/completeness | Fixed unmatched fences in observability, retention and LVM documents; removed pasted filename/wrapper from retention; incomplete LVM procedure explicitly blocked |
| Change/index tracking | Added actual UDM recovery outcome and historical incident index |
| Private data | Added `.unifi` and local-state ignores; secret-free Compose retained; raw backups/credentials/journals remain outside Git |

Historical incident/changelog bodies retain their original facts. This review
updates their applicability rather than rewriting old outcomes as today's state.

## Items that cannot be marked resolved by documentation edits

| Priority / status | Gap and current evidence | What is needed |
| --- | --- | --- |
| High — access/config verification | OPNsense Suricata production source is gone. Anduin IDS/IPS/syslog mode, sender/scope and replacement ingestion are unknown. | Authorized read of UDM security/logging settings and Minas listener/ingestion; approve any new deployment or mode change separately. |
| High — authenticated inspection | Grafana health responds. Prometheus9090, Loki3100, Kuma3001 did not respond on the documented paths. This does not prove outage. Retention/scrapes/alerts are not audited. | Authorized Minas host/Compose and Grafana data-source inspection; identify actual bindings/proxy paths and fresh targets/events before changing anything. |
| Medium — authenticated inspection | Palantir resolves required local/public names. Config API returned 401; actual Pi-hole upstream, Unbound and conditional-forwarding chain not inspected. | Owner-authenticated Pi-hole/host read using local credentials. No guessing credentials or replacing DNS as a shortcut. |
| Medium — operational test | Fresh console export 119,728 bytes and same-host digest copy verified; no semantic/restore validation, off-host copy or offline administration rehearsal. | Owner-chosen protected off-host storage; separately authorized isolated restore/recovery exercise. No destructive production test. |
| Medium — representative clients | Basic IoT/Guest web denial tests passed; direct UDP/TCP DNS enforcement, other destination/protocol/return cases and two-client guest peer isolation remain untested. | Actual clients on source VLANs, two guests for peer test, explicit endpoints and recording of allowed/denied results. No inferred all-pairs audit. |
| Medium — historical source gap | Initial Kea source summary retained counts/selected fields rather than a complete recoverable export. Current eight restored fixed records and static MGMT work; source completeness is unproven. | An approved isolated source export if historical completeness is required; never reconnect overlapping production OPNsense/DHCP to fetch it. |
| Medium — policy decision, intentionally deferred | LAB is not isolated from trusted VLANs. CLIENTS/SERVERS/MGMT have no custom source restrictions in the reviewed set. | LAB hardening stays deferred by owner. Inventory intended workloads/storage before defining a policy; no blanket deny inferred from VLAN labels. |
| Low — inventory/access | Exact VM/LXC placement, every unused switch port, current VPN provider/egress behavior, bastion hardening and some WAN/IPv6 details are not fully documented. | Scoped reads of the relevant hosts/controller/settings when needed; preserve working WAN and current policy. |
| Low — stale record edit | Pi-hole screenshot shows old `lothlorien.murtha.info -> 10.10.20.20` although controller is off. | Owner review of dependencies and separately approved DNS cleanup; no deletion inferred from retirement alone. |
| Low — incomplete procedure | LVM runbook stopped after the disk-resize example. Exact current VM/disk/partition/PV/LV/filesystem/backup layout unknown. | Read target layout and recovery prerequisites before completing an executable sequence. Formatting was fixed; missing operational facts were not invented. |
| Low — historical date ambiguity | `2026-01-01-enable-dhcp-vlan40.md` internally says `2025-01-XX`. | Owner/source-history confirmation before changing the event date; historical uncertainty retained. |
| Tooling — compatibility review | Installed NEST write contract 10.6.106 versus Anduin 10.6.109. Recovery adapters/UI worked for scoped batches; a Wi-Fi API create was rejected 400. | Reviewed per-resource/method contract/tests and a released plugin update; source [PR6](https://github.com/erwich/nest/pull/6) is not installed-version evidence or permission to bypass guards. |

## Validation and maintained boundaries

Check local relative links, Markdown fences, Mermaid source structure, diff
whitespace, secret/backup ignores and Compose syntax without reading tokens.
No infrastructure mutation is part of those checks. Functional migration
acceptance is limited to the verified/owner-tested rows in
[migration acceptance](udm-pro-max-migration.md). Deferred hardening and unknown
telemetry are visible follow-ups, not invented failures or blanket NO-GO claims.

Validation completed: **34 Markdown files** have balanced fenced blocks and
valid local link targets; `git diff --check` passes. All three Mermaid files pass
basic delimiter/source checks, but no Mermaid renderer is installed, so rendered
syntax/layout is not claimed verified. `docker compose ... config --quiet` passes
for the checked-in DDNS template without starting containers or reading tokens.
Ignore checks protect `.unf`/`.unifi`, local state, backup directories, dotenv and
DDNS secret/preimage paths while leaving the Compose template trackable. Credential
marker review found no literal credentials/private keys; remaining external IP
literals in historical evidence are the well-known probe endpoint and mDNS group,
not a household WAN address. No packages or daemons were installed for validation.

The protected backups, raw source state, full API objects/MACs and SSH bindings
remain private. The NEST contribution is separate from this homelab checkout;
its PR does not publish these homelab changes.

## Publication preparation — 2026-11-13

Prepared the existing November 4 reconciliation in an independent checkout based
on remote main `db89b0812dfc215bd88e246fbd8c348ade229323`. Original mixed worktree
contents were preserved. Unrelated Dispatcharr artifacts and Denethor backup work
are excluded. The uncommitted status above describes the original review date.

Rechecked 34 Markdown files for local link targets and balanced fenced blocks,
`git diff --check`, DDNS Compose validation without startup, protected-path ignore
rules, and credential/private-key/MAC patterns. No literal credentials or MAC
addresses were found by that bounded scan; it is not a complete secret-detection
guarantee. Mermaid source was reviewed, but rendering remains untested because
no renderer is installed. No live network, service or recovery checks were run.

This publishes a dated recovery checkpoint, not a fresh infrastructure inventory.
Bag End and later UDM ad-blocking changes are outside this migration snapshot;
current deployment and DNS implications need separate reconciliation. NEST version
claims above are historical and do not establish the installed version today.
