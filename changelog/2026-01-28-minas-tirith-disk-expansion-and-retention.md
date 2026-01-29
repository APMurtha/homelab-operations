# Expand Minas-Tirith Disk and Enforce Telemetry Retention

## Summary

Expanded the `minas-tirith` observability VM disk and implemented explicit
retention limits for Prometheus and Loki to prevent unbounded disk growth.

This change stabilised the telemetry stack after the root filesystem reached
100% utilisation and established long-term safeguards appropriate for a
homelab environment.

## Changes

- Expanded the Proxmox virtual disk for `minas-tirith` from 20G to 40G
- Extended the LVM physical volume, logical volume, and ext4 filesystem
- Temporarily removed telemetry containers to recover emergency disk space
- Reconfigured Prometheus to use a persistent data directory with:
  - 7-day retention window
  - 2GB maximum TSDB size
- Enabled Loki log retention with:
  - 7-day retention period
  - Compactor-driven deletion using filesystem storage
- Installed Netdata for real-time diagnostics on:
  - `orthanc` (Proxmox host)
  - `rivendell` (media and Docker workload host)
- Netdata Cloud was intentionally not enabled

## Outcome

- Root filesystem utilisation returned to stable levels
- Telemetry data growth is now bounded and predictable
- The observability stack is prepared for future SIEM integration without
  requiring rework or data migration
