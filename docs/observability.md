# Observability — documented design and current verification

**Reviewed 2026-11-04.** Minas-Tirith10.10.20.40 is the documented telemetry host.
Historical deployment/retention records remain useful, but removal of OPNsense
changed the network-security log source. Do not infer a working current pipeline
from a running Grafana UI or the old Suricata change record.

## Current evidence

| Service/path | Observation from Denethor CLIENTS | What remains unknown |
| --- | --- | --- |
| Grafana port 3000 /api/health | HTTP 200 during this review | Current data-source health, dashboards and alert delivery |
| Prometheus port 9090 /-/ready | No HTTP response within bounded check | Listener/bind/port publication, service health, scrape targets/retention |
| Loki port 3100 /ready | No HTTP response within bounded check | Listener/publication, ingestion, query/retention/deletion behavior |
| Uptime Kuma port 3001 | No HTTP response within bounded check | Actual listener/reverse-proxy path, monitored targets and notifications |
| Promtail/syslog1514 | Historical deployment only; not inspected this review | Current listener, permissions, sender and fresh ingestion timestamps |
| OPNsense Suricata source | Retired gateway disconnected | UDM IDS/IPS/syslog replacement is not verified |
| Netdata on Orthanc/Rivendell | Historical host/workload diagnostics documented | Current install, endpoints and alerts not independently audited |

An unresponsive guessed/documented port is not proof the service is down; these
services may be bound privately or exposed through a reverse proxy. Authenticated
host/Compose and Grafana data-source inspection is needed before proposing fixes.
No restart, port publication, retention change or IDS activation occurred.

## Historical architecture

January records describe Grafana, Prometheus, Loki, Promtail and Uptime Kuma on
Minas-Tirith; Netdata on Orthanc/Rivendell; no Netdata Cloud. Historical flow:

```text
OPNsense Suricata (WAN + SERVERS; IDS-only, ET Open)
  -> RFC5424 syslog -> Promtail -> Loki -> Grafana
```

That OPNsense source is no longer producing production gateway telemetry. Whether
Anduin has IDS/IPS enabled or exports equivalent logs has not been established.
Do not describe the old IDS-only posture as the UDM's current mode.

[Recorded retention policy](../runbooks/set-telemetry-retention.md): Prometheus 7d /
2GB cap; Loki 7d with compactor/deletion. Current settings and successful deletion
are unverified. [Suricata reference](../runbooks/suricata-ids.md) is historical.

## Required follow-up before operational changes

Read Minas-Tirith's actual containers/services, published/bound ports and config
paths through authorized access; inspect current Grafana data-source status,
scrape targets, fresh log/metric timestamps, disk use and notification tests.
Then inspect Anduin's supported IDS/IPS/syslog UI and approve the intended mode,
scope, destination and retention. Do not enable IPS or a new logging service as a
side effect of documentation review. Track these gaps in the
[review report](documentation-review-2026-11-04.md).
