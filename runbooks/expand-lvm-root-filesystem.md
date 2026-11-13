# Expand LVM Root Filesystem on a Proxmox VM

**INCOMPLETE PROCEDURE — do not execute as a complete recovery runbook.**
The original file ends after the Proxmox disk-resize example and omits partition,
PV/LV and filesystem growth/verification. Target VM/disk/partition/LV layout and
backup state must be inspected before an executable sequence can be written.
No disk operation was run or inferred during this documentation review.

## Purpose

Safely expand the root filesystem of a Linux VM using LVM after increasing
the virtual disk size in Proxmox.

This runbook is intended for Ubuntu-based guests using:
- LVM
- ext4 root filesystem
- Proxmox-backed virtual disks

## When to Use

- Root filesystem is near or at 100% usage
- Proxmox disk has been resized or needs resizing
- LVM resize operations fail due to lack of free space

## High-Level Steps

1. Expand the virtual disk in Proxmox
2. Resize the LVM physical volume inside the guest
3. Extend the logical volume
4. Grow the filesystem online
5. Verify free space

## Proxmox Host

Identify and resize the VM disk:

```bash
qm config <VMID>
qm resize <VMID> <disk> +<size>
```

## Missing prerequisites and steps

Confirm the VM, storage, disk and snapshot/backup constraints; read the guest
block-device tree, root filesystem and LVM layout. Determine whether a partition
needs growth before the PV, then plan the exact LV/filesystem resize and checks
for that layout. Never substitute guessed device names or use shrink operations.
The historical [Minas-Tirith change](../changelog/2026-01-28-minas-tirith-disk-expansion-and-retention.md)
is evidence of a past expansion, not proof of the present layout.
