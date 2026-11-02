# Prepare UDM Pro Max migration documentation

## Date
2026-11-02

## Description
Created a discovery checklist and staged UDM Pro Max migration plan. Marked the February 2026 network design as historical pending live verification, corrected a stale switch label, and noted the owner-reported Proxmox cluster change.

## Reason for Change
The ordered gateway requires a reviewed inventory, policy translation and rollback procedure before any installation or production cutover.

## Scope
Documentation only. No firewall, DHCP, DNS, controller, switch, wireless, Proxmox, modem or storage configuration was changed.

## Validation / Success Criteria
Reviewed existing architecture, diagrams, incident reports and changelog. The plan separates the ARRIS-to-UDM gateway cutover from the later cable modem replacement. A bounded, read-only SSH inspection of `anduin` verified selected interfaces, Kea settings, saved firewall rules and NAT, and runtime WAN/routing observations. The [dated findings](../docs/anduin-discovery-2026-11-02.md) record the evidence and remaining gaps. Effective firewall and client behavior remain unverified.

## Rollback Plan
Revert this documentation branch if the review rejects it. Production rollback is documented separately in `docs/udm-pro-max-migration.md` and requires an isolated rehearsal before cutover.

## Outcome
Documentation and initial OPNsense discovery prepared for review; the remaining systems and migration remain pending.
