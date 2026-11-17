# Persistence proposal selection — Phase 6B-3D

Current deployment: exact `minimal-phase6b3d/` candidate installed and enabled
on Rivendell 2026-11-16 UTC under Phase 6B-3G approval. Both oneshot units are
active/exited; all three dedicated containers are healthy with restart=no.
See [installation and acceptance](../../docs/dispatcharr-minimal-persistence-installation-phase6b3g.md).
The [original plan](../../docs/dispatcharr-minimal-persistence-phase6b3d.md) remains
historical; do not rerun installation without fresh authorization/preflight.
Cold boot/Docker failure and permanent Jellyfin integration remain untested.

The controller/enrollment/cgroup work in `persistence-phase6b3/`,
`isolation-phase6b3a/` and `controller-phase6b3b/` is retained as historical
research, not an activation path. Do not install its units, overrides,
authentication records, approval-token mechanism, cgroup slice or controller.
No Phase 6B-3C artifact was found in this checkout; no findings are invented for it.
The earlier reports retain their original experimental conclusions.

Retain accepted guard.py/security.py, startup gates, Gluetun kill switch, Docker
namespace/network contract, Caddy configuration and HLS enforcement artifacts.
The new runtime uses only two systemd oneshot units, the existing Compose CLI,
restart=no and a read-only one-shot verifier. No continuous controller is planned.

## Offline trusted-guard candidate (not installed)

The repository prepares a coordinated guard/verifier/20/new guard-unit drop-in
transition. Production remains on the last accepted three-service baseline; no
installation or live health check is implied. See the trusted-guard implementation
report for exact pins, private-schema migration and whole-baseline rollback.
