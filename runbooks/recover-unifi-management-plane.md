# Recover management access in the current UDM topology

**Scope: Anduin UDM Pro Max with adopted Osgiliath/Ithil, 2026-11-04.** The former
February OPNsense/controller-isolation/factory-reset/LAGG procedure is historical
and is preserved in the [incident](../incidents/2026-02-08-unifi-management-plane-instability.md).
It is not today's default recovery. This runbook was reconciled against successful
recovery observations; a complete offline recovery rehearsal remains untested.

## Preserve the surviving path

Identify what is actually unavailable: controller UI, adopted-device heartbeat,
one client's path, DNS, or a host service. Use a surviving CLIENTS/MGMT session or
trusted local console. Avoid resets, reboots, controller shutdown, old backup
restores and simultaneous port/address changes. Operational writes still require
an approved target/diff/recovery plan; inspect read-only first.

## Known current topology

- Anduin administration: MGMT 10.10.10.1 and CLIENTS 10.10.30.1 verified.
- Default is 10.0.0.1/24; DHCP and Internet Access are off. Old 192.168.1.1 is obsolete.
- Anduin port 7↔Osgiliath port 1: one 1 Gbps Cat6 trunk, native Default/tagged Allow All.
- Ithil connects directly to Anduin port 8; native/tagged uplink preserved.
- Osgiliath 10.10.10.10 and Ithil 10.10.10.20 use tagged MGMT 10 overrides, static/24,
  gateway 10.10.10.1, DNS 10.10.20.10. MGMT has no DHCP pool.
- Moria 10.10.10.8 uses native MGMT on switch port 2; Proxmox .2/.3/.4 management paths
  use native MGMT on switch ports 5/6/7. Never substitute the retired MGMT_UPLINK profile
  that blocks tags or rebuild a LAG to match February's topology.

## Diagnose without changing configuration

1. Verify actual appliance/model/site before using administrative tools. The
   hostname Anduin and 10.10.10.1 now identify the UDM, not old OPNsense.
2. Confirm the test client's address/router/DNS and active SSID. Try the verified
   numeric management endpoints to distinguish DNS failure from routing/UI loss.
3. Read gateway WAN/LAN state and adopted switch/AP state. Provisioning may briefly
   change online status; read again rather than replaying the last write.
4. Reconcile each physical hop's peer port, native VLAN, tagged allowance and
   device management override. A device tagged for MGMT must have a working tagged
   VLAN 10 path; do not also change its attached native network to MGMT blindly.
5. Compare endpoint addresses with live service probes and persistent config.
   Stale controller client rows may retain old IP/network labels. Static MGMT
   devices should not depend on a new dynamic pool.
6. For lost Proxmox/NAS services, inspect their own address/default route and
   cluster/mount state before attributing the problem to a new firewall rule.

## Approved targeted recovery

Review the exact change and inverse from current state, including complete port
arrays and references. Capture private before-state. Change one affected device
or access port at a time, then verify adoption, administration and required flows
before continuing. Preserve all unrelated ports and radio settings. If reverting
an approved change, preserve later owner edits; reconcile uncertain outcomes
read-only before another write. Never replay an old private adapter blindly.

A direct laptop-to-UDM recovery path should be prepared separately: identify the
actual port's native network and a verified-unused static address in that subnet,
then verify local administrator login without relying on cloud access. Default
has no DHCP; do not assume an automatic address. That offline procedure has not
yet been exercised, so do not promise it will work during an outage.

Use the fresh private post-recovery console export only after an explicitly
approved restore plan. It is saved with a matching-digest copy, not restore-tested.
Restoring October's Lothlorien Network backup could overwrite the working UDM
configuration. Factory reset is a separate last-resort operation requiring a
verified backup, physical recovery path and explicit approval, not an initial step.

## Verify and record

Confirm MGMT/CLIENTS administration, switch/AP adoption, correct DHCP/DNS, NAS
reads, relevant cluster readiness and allowed/blocked client flows. Preserve
old OPNsense disconnection and Lothlorien shutdown. Reverting to the old gateway
is no longer a cable-only rollback: addresses, leases, adoption and modem/WAN
have changed. See [acceptance](../docs/udm-pro-max-migration.md) and
[review gaps](../docs/documentation-review-2026-11-04.md).
