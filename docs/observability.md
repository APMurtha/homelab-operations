# Observability Overview

## Purpose

Documents the structure and intent of the homelab observability stack.

This stack is designed for:
- Health visibility
- Performance troubleshooting
- Alerting
- Preparation for future security monitoring

## Core Node: minas-tirith

`minas-tirith` hosts the central telemetry services:

- Grafana (visualisation)
- Prometheus (metrics)
- Loki (logs)
- Promtail (log ingestion)
- Uptime Kuma (availability checks)

Retention is explicitly limited to prevent disk exhaustion.

## Real-Time Diagnostics: Netdata

Netdata is deployed selectively for live troubleshooting:

- `orthanc` — Proxmox host (VM/LXC contention, IO wait, CPU steal)
- `rivendell` — Docker-heavy media host

Netdata is used for:
- Explaining transient lag
- Identifying contention sources
- Real-time correlation

Netdata Cloud is intentionally not used.

## Access Model

- Telemetry services are accessed from trusted internal networks
- No public exposure
- No external SaaS dependencies

## Philosophy

- Netdata answers: “What is happening right now?”
- Grafana answers: “Has this been getting worse?”
- SIEM (future) will answer: “Is this malicious or abnormal?”

Each layer has a distinct purpose.
