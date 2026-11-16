# Minimal persistence — UNAPPLIED Phase 6B-3D proposal

Read [the plan](../../../docs/dispatcharr-minimal-persistence-phase6b3d.md).
Use this folder instead of the retired controller/enrollment proposal.

Two oneshot units, one Docker ordering drop-in, one three-service restart override,
and a read-only verifier. `contracts.py` copies the historical pure guard/topology
checks; it imports no controller or enrollment code. The accepted table template
is byte-identical. `verify.py` has no signal/restart/apply/loop behavior.

The guard unit applies and verifies only the accepted table before Docker.
Docker's dependencies are soft so unrelated services can start if it fails.
The workload unit has hard guard requirements, reapplies/verifies the accepted
table after Docker starts, checks the existing fixed network and three containers,
then calls bounded Compose up with no recreate/build/pull. Restart=no prevents
Docker autostart around these preflights. Existing owner/app startup gates remain.

Missing network/container, invalid source/image/namespace/port, stale marker or
guard mismatch blocks startup. Create/recreate stopped resources manually only
in an approved maintenance window; unit startup does not repair network drift.
ExecStopPost stops exactly the three services after failure/stop, retaining rules
and data. API-unavailable cleanup can fail; no cgroup kill is substituted.

A oneshot active state is not continuous health monitoring. Exited/unhealthy
containers do not trigger an automatic restart. Use the workload unit for normal
project restart. Docker crashes, forced namespace/network recreation, privileged
ruleset removal and host reboots require explicit target validation. No new VM
or daemon is required or proposed for those later authorized checks.

Offline validation:

```sh
python3 -m unittest discover -s configs/dispatcharr-iptv/minimal-phase6b3d/tests -v
docker compose -f configs/dispatcharr-iptv/compose.proposed.yaml \
  -f configs/dispatcharr-iptv/minimal-phase6b3d/compose.persistence.proposed.yaml \
  config --no-env-resolution --quiet
```

These parse/model checks do not start Docker workloads or prove live boot/restart
behavior. Proposed unit syntax and static combined ordering graph were verified
with systemd-analyze; none was installed or enabled.
