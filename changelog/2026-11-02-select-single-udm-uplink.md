# Select a single UDM gateway uplink

## Date
2026-11-02

## Description
Selected one Cat6 cable between the planned UDM Pro Max and existing `osgiliath` switch for the gateway migration. The initial link is planned for 1 Gbps and tagged VLANs 20–70. MGMT remains `10.10.10.0/24` and will stay untagged during the first cutover if the verified device configuration requires it. Tagged VLAN 10 management was deferred to a separate controlled change. The existing OPNsense LAGG will be retired from the target design.

## Reason for Change
The replacement gateway should use a simpler single-uplink path while preserving current addressing and management access. A later switch upgrade can provide a faster link.

## Scope
Planning and documentation only. The UDM has not been installed, and no gateway, switch, controller, VLAN or cable configuration was changed. Actual `osgiliath` ports and native/tagged behavior still require authenticated discovery.

## Validation / Success Criteria
The [migration plan](../docs/udm-pro-max-migration.md) and [planned topology](../diagrams/udm-single-uplink.mmd) require one UDM-to-switch cable, preserve the existing OPNsense MGMT/LAGG paths for rollback, and make the tagged MGMT transition a separate gate. Physical port and controller verification remain pending.

## Rollback Plan
Before a production cutover, reverting this documentation decision restores the prior design proposal. During a future cutover, disconnect the UDM link before restoring the recorded OPNsense MGMT and both LAGG member cables and its WAN handoff.

## Outcome
The single-uplink architecture was selected for the plan; production remains unchanged.
