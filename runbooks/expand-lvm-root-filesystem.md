# Expand LVM Root Filesystem on a Proxmox VM

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
