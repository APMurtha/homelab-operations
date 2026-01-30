# Suricata IDS

## What
Suricata runs in **IDS-only mode** on OPNsense to provide network security telemetry.
Traffic is observed only; no blocking is performed.

## Where
- Platform: OPNsense (`anduin`)
- Interfaces:
  - WAN
  - VLAN20_SERVERS
- Ruleset: Emerging Threats Open (ET Open)

## Logs
Suricata events are sent via RFC5424 syslog:

OPNsense → Promtail → Loki → Grafana

## Verify
- Suricata running:
  - Services → Intrusion Detection → Administration
- Syslog listener:
  - ss -lntp | grep ':1514'
- Logs in Grafana:
  - {job="suricata"}

## Do Not
- Enable IPS
- Tune or suppress rules yet
