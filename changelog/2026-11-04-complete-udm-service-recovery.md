# Complete UDM gateway service recovery and reconcile current documentation

## Date and scope

Recovery occurred November 2–3, 2026 Eastern; documentation reconciled November 4.
Owner performed the physical cutover and approved scoped production changes.
This records the resulting state; it is not authorization for new operations.

## Change and outcome

Replaced OPNsense routing/DHCP and Lothlorien's controller with Anduin UDM Pro Max;
UCI Eärendil is online. Established one Cat6 gateway-switch uplink, retired the
active LAG path, restored original MGMT/static infrastructure addresses, and
recovered Proxmox quorum, K3s peer addresses, NAS media mounts and service access.
Restored approved DHCP pools/reservations and Palantir DNS/search behavior.

Recreated Calacirya/Gondolin/Lorien/Bree and source-specific IoT/Apple/Guest
policies. Restricted mDNS to CLIENTS/APPLE_IOT. Restored TCP 443→Elessar/NPM and
books-only Cloudflare DDNS. Default gateway is now 10.0.0.1/24, with DHCP, Internet
Access and mDNS off; the subnet remains configured. Lothlorien was decommissioned
and shut down by the owner; old OPNsense remains disconnected.

## Validation and limits

Owner confirmed Proxmox 3/3 quorum, all K3s nodes Ready, Apple cross-VLAN controls
and paired-HomePod TV playback, basic IoT/Guest Internet and denied management
web access, and external mobile Audiobookshelf access. Authenticated readbacks,
DNS/TLS checks and actual NAS/container mount reads supplement those tests.
A fresh private console export and matching same-host copy are saved; no restore
or off-host backup validation is claimed. LAB hardening is explicitly deferred.

[Current architecture](../docs/network.md), [acceptance](../docs/udm-pro-max-migration.md)
and [review gaps](../docs/documentation-review-2026-11-04.md) are the current
references. Full intermediate evidence is preserved in the
[working-note archive](../docs/_archive/udm-migration-working-notes-2026-11-04.md).

## Recovery considerations

Protect working UDM administration and the current backup. Old cable-only LAGG/
ARRIS rollback is obsolete after controller, lease, host and modem changes; any
return to OPNsense requires a new approved plan. The original topology-specific
factory-reset/LAGG recovery runbook was replaced with current non-destructive
management diagnosis. No additional infrastructure changes were made by the
November 4 documentation review. Complete observability, peer-isolation and
independent recovery verification remain follow-ups.
