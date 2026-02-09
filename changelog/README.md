# 📅 Changelog

This directory contains **chronological change records** for significant homelab updates.
Entries document **what changed**, **why it changed**, **impact**, and **rollback considerations**.

The changelog represents *intentional infrastructure decisions*, not routine maintenance.
Procedural details are intentionally excluded and belong in `runbooks/`.

---

## Conventions

- **One change per file**
- Filenames use the format:

  `YYYY-MM-DD-short-description.md`

- Entries are written:
  - in past tense
  - factually and concisely
  - with focus on **intent, outcome, and impact**

- Changelog entries answer:
  - What changed?
  - Why was the change made?
  - What was the impact?
  - How could this be rolled back?

---

## Index

### 2026

- `2026-02-08-migrate-switch-tplink-to-unifi.md`  
  Migrate core switch from TP-Link to UniFi

- `2026-01-29-suricata-ids-and-telemetry-pipeline.md`  
  Deploy Suricata IDS and centralized telemetry pipeline

- `2026-01-28-minas-tirith-disk-expansion-and-retention.md`  
  Expand monitoring node storage and adjust telemetry retention

- `2026-01-20-separate-server-traffic-intel-nic.md`  
  Separate server traffic using dedicated Intel NIC

- `2026-01-01-enable-dhcp-vlan40.md`  
  Enable DHCP on VLAN 40 (LAB)

- `2026-01-01-enable-dhcp-vlan30.md`  
  Enable DHCP on VLAN 30 (CLIENTS)

---

### 2025

- `2025-12-31-add-opnsense-vlans.md`  
  Add OPNsense VLAN interfaces and IP addressing

---

## Notes

- The changelog is **authoritative** for architectural evolution
- Incidents caused by changes are documented separately in `incidents/`
- Repeated or expected procedures derived from changes may later be promoted
  to `runbooks/`
