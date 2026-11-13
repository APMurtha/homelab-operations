# Homelab Operations

Architecture, operating procedures and change history for Andrew's homelab.
Current-state documentation was reconciled on **2026-11-04** against the completed
UDM recovery, authenticated network observations and owner acceptance tests.
Historical incidents and changelog entries describe their original dates.

## Current environment

| Role | System |
| --- | --- |
| Gateway and UniFi Network controller | **Anduin — UDM Pro Max** |
| Comcast modem | Eärendil — UCI |
| Switch / AP | Osgiliath — USW-24-G2 / Ithil — U7 Pro |
| Virtualization | mordor — Orthanc, Cirith-Ungol, Dol-Guldur |
| DNS | Palantir — Pi-hole + Unbound; resolver chain configuration review pending |
| Media / reverse proxy | Rivendell / Elessar — NPM, Authentik, books-only DDNS |
| Storage | Moria UNAS; distinct from Orthanc's local `moria` ZFS pool |
| Observability | Minas-Tirith; Grafana responds, other telemetry paths need verification |

OPNsense is disconnected. Lothlorien's former controller is decommissioned/off.
The active gateway-to-switch path is one Cat6 1 Gbps link, with no active LAG.
MGMT uses VLAN 10; switch/AP management is tagged, while infrastructure access
ports use native MGMT. Default/VLAN 1 is `10.0.0.1/24`, with DHCP, internet access
and mDNS disabled. The subnet still exists.

## Start here

- [Current network architecture, addressing and policy](docs/network.md)
- [Migration outcomes, evidence and remaining acceptance](docs/udm-pro-max-migration.md)
- [Documentation review: fixed issues and unresolved gaps](docs/documentation-review-2026-11-04.md)
- [Management recovery](runbooks/recover-unifi-management-plane.md)
- [Naming and identity](docs/naming.md)
- [Observability status](docs/observability.md)
- [Reproducible Elessar DDNS configuration](configs/cloudflare-ddns/compose.yaml)
- [Change history](changelog/README.md) / [historical incidents](incidents/README.md)

## Verification boundary

Core restored services and owner-tested IoT, Guest and Apple workflows are
operational. VLAN membership is not proof of isolation: LAB hardening is
**explicitly deferred**, and CLIENTS/SERVERS/MGMT have no custom source restrictions
in the reviewed classic rules. Guest peer isolation and selected policy/recovery
checks remain untested. Read the evidence/status in each document before acting.

## Repository layout

```text
docs/        Current architecture, acceptance and review findings
docs/_archive/ Historical snapshots and superseded working notes
diagrams/    Current physical/logical Mermaid source diagrams
runbooks/    Procedures with scope and verification limits
incidents/   Dated incident evidence; not current recovery instructions
changelog/   Dated architectural and operational changes
configs/     Secret-free reproducible configuration
```

Credentials, MAC inventories, private API journals, exported backups and raw
infrastructure state stay outside Git. Documentation changes do not authorize
live network/service changes.
