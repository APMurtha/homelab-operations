# 2026-01-29 — Suricata IDS & Security Telemetry Pipeline

## Added
- Enabled **Suricata IDS** on OPNsense in **IDS-only mode**
  - Interfaces monitored: **WAN** and **VLAN20_SERVERS**
  - Rule source: **Emerging Threats Open**
  - EVE logging enabled (RFC5424 syslog)

- Implemented **security log pipeline**
  - OPNsense → RFC5424 syslog
  - Promtail syslog listener on `minas-tirith:1514`
  - Loki as central log store
  - Grafana Loki datasource for querying Suricata events

- Connected Grafana container to Loki Docker network for direct resolution

## Notes
- IPS mode intentionally disabled (future phase)
- No rule tuning or suppressions applied yet
- This establishes the foundation for future Wazuh/SIEM integration
