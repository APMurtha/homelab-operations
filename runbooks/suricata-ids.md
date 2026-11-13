# Historical OPNsense Suricata IDS reference

**Retired production source.** Anduin is now a UDM Pro Max; old OPNsense is
disconnected. These January 2026 observations do not establish the UDM's IDS/IPS
mode or current log ingestion. See [observability](../docs/observability.md).
Do not use OPNsense menus/commands against today's10.10.10.1.

The former deployment used IDS-only Suricata on WAN and VLAN20_SERVERS, ET Open
rules, no blocking. It exported RFC5424 events through Promtail/Loki to Grafana.
The old inspection points were its Intrusion Detection service, syslog listener
1514 and Grafana query `{job="suricata"}`. An old log result does not prove a
fresh gateway sender; verify event timestamps/source and the actual listener.

The UDM replacement pipeline is **unverified**. Read supported Anduin settings
and actual Minas-Tirith ingestion before proposing a replacement. Enabling IDS,
IPS, exporting logs or changing rules requires its own reviewed scope/approval.
Historical source: [January change](../changelog/2026-01-29-suricata-ids-and-telemetry-pipeline.md).
