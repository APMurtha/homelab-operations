# Observability Overview

## Purpose

Documents the structure and intent of the homelab observability stack.

This stack is designed for:
- Health visibility
- Performance troubleshooting
- Alerting
- Preparation for future security monitoring

---

## Core Node: minas-tirith

`minas-tirith` hosts the central telemetry services:

- Grafana (visualisation)
- Prometheus (metrics)
- Loki (logs)
- Promtail (log ingestion)
- Uptime Kuma (availability checks)

Telemetry retention is intentionally limited to prevent disk exhaustion.

---

## Real-Time Diagnostics: Netdata

Netdata is deployed selectively for live troubleshooting:

- `orthanc` — Proxmox host
- `rivendell` — Docker / media workloads

Netdata is used for:
- Explaining transient lag
- Identifying contention
- Real-time correlation

Netdata Cloud is intentionally not used.

---

## Log Collection

Logs are centrally collected to support troubleshooting and security visibility.

- Promtail ingests local system logs and network syslog
- Loki stores logs for short-term analysis
- Grafana provides search and dashboards

Logs are retained only as long as operationally useful.

---

## Security Telemetry (IDS)

### Overview
OPNsense runs **Suricata in IDS-only mode** to provide network-level security telemetry.
Traffic is observed but not blocked.

### Scope
- Appliance: OPNsense
- Interfaces monitored:
  - WAN
  - VLAN20_SERVERS
- Rule source: Emerging Threats Open (ET Open)

### Data Flow
```text
OPNsense (Suricata)
  → Syslog (RFC5424)
  → Promtail
  → Loki
  → Grafana
