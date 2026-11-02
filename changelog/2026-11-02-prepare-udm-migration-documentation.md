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
Reviewed existing architecture, diagrams, incident reports and changelog. The new plan records unknowns and separates the ARRIS-to-UDM gateway cutover from the later cable modem replacement. Live network behavior remains unverified.

## Rollback Plan
Revert this documentation branch if the review rejects it. Production rollback is documented separately in `docs/udm-pro-max-migration.md` and requires an isolated rehearsal before cutover.

## Outcome
Documentation prepared for review; discovery and migration remain pending.
