Palantir node_exporter — prepared for review, NOT deployed
========================================================

Scope
  Only Palantir: CT 110 on Orthanc, hostname palantir, 10.10.20.10.
  The installer is intentionally target-bound, not a general-purpose remote tool.
  No SSH/sudo policy, DNS/DHCP, resolver, networking, firewall, Pi-hole, Unbound,
  Prometheus, Grafana, Proxmox, or ZFS configuration is written by this script.
  Installing the new package creates its ordinary prometheus service account,
  package files, /etc/default/prometheus-node-exporter, and service enablement.

Read-only observations (2026-11-18 Eastern)
  Dedicated codex key-based SSH access works; sudo needs a password.
  Debian GNU/Linux 12 bookworm, amd64, LXC. This is NOT Ubuntu.
  No node_exporter or Netdata executable/package was found in the audit.
  Candidate Debian package: prometheus-node-exporter 1.5.0-1+b6, 13465 KiB installed.
  Dependencies adduser and libc6 are already satisfied. apt-get simulation:
    0 upgraded, 1 new package, 0 removed; recommendations omitted.
  Installed package is NOT pinned through apt-mark: future upgrades remain subject
  to existing household package-management policy. This deployment requests an
  exact version and refuses unexpected transaction/candidate changes.
  Pi-hole FTL, Unbound, and SSH active. Ordinary example.com A lookups through
  local Pi-hole :53 and Unbound :5335 returned NOERROR.
  RAM total 512 MiB; approximately 428 MiB available. Root ext4 ~8.35 GB total,
  ~5.79 GB available. Port 9100 was unoccupied.
  These are observations, not a deployment or future health guarantee.

Proposed service
  Debian's native service/binary: prometheus-node-exporter / User=prometheus.
  Override: /etc/systemd/system/prometheus-node-exporter.service.d/palantir.conf
  Listen: 10.10.20.10:9100 only. No wildcard, IPv6, or public-interface binding.
  Internal-LAN metrics are unauthenticated HTTP; no credentials are sent there.
  CPU, meminfo, filesystem collectors only. All non-root mounts excluded.
  ZFS collector not enabled; disk-pool monitoring and Moria are out of scope.
  Limits: 64 MiB memory, 20% of one CPU, 32 tasks; NoNewPrivileges=true.
  Avoids PrivateTmp/ProtectHome mount namespaces that can fail in restricted LXCs.
  Installs the override BEFORE the package can automatically start the service.
  Uses existing journald, warn-level logs, no added daemon besides the exporter.
  No package refresh, distribution upgrade, recommendations, dependency cleanup,
  firewall changes, or unrelated service restarts are requested.

Review and staging
  Source: configs/palantir-node-exporter/install.py in homelab-operations.
  Status: prepared for code review; deployment requires separate authorization.
  No copy to Orthanc or Palantir and no installer invocation has been performed.
  Inspect the complete script and static-validation.json before authorizing use.
  Stage the reviewed script on Orthanc as /root/palantir-node-exporter.py using
  your trusted transfer procedure; keep it root-owned and not group/world writable.
  Compare its SHA-256 with static-validation.json / the reviewed local file.
  Do not fetch and execute unreviewed network content as root.

After separate deployment approval — exact commands ON ORTHANC
  Run from an existing root console/shell on Orthanc. This uses Proxmox's container
  execution path; it does not require codex sudo permissions inside Palantir.
  The Python source is streamed on stdin; no script file is stored in the guest.

    pct exec 110 -- python3 - install < /root/palantir-node-exporter.py

  A successful run prints the exact private recovery directory, for example:
    /var/backups/palantir-node-exporter/YYYYMMDDTHHMMSSZ-PID
  Retain that path. BACKUP_DIRECTORY below means that exact path printed by this
  run, not the literal example. Substitute it before executing verify/rollback:

    pct exec 110 -- python3 - verify BACKUP_DIRECTORY < /root/palantir-node-exporter.py

  There is deliberately no automatic install on an omitted action. An existing
  package, stale package state, existing override, unexpected OS/host/IP, occupied
  port, unhealthy protected service/DNS, or extra apt transaction stops execution.
  Do not bypass these checks or loosen sudo permissions to make installation work.

Backup and verification
  Before installation writes, creates a mode-700 root-owned timestamped directory
  under /var/backups/palantir-node-exporter. Its files are mode 600 and may contain
  sensitive Pi-hole/Unbound configuration. Keep them private and OUT OF GIT.
  Captures protected configuration tar.gz, service PIDs/restart counts, config
  hashes, interface addresses, routing, available iptables rule fingerprints,
  proposed override, and simulated package plan. New exporter paths must have
  been absent. Re-reads archive members and verifies SHA-256 before proceeding.
  Protected configuration archive is evidence/recovery material; the script NEVER
  automatically restores or overwrites DNS, networking, firewall, or SSH config.

  After installation checks:
    - unprivileged service active and exactly 10.10.20.10:9100 listening;
    - exactly CPU/meminfo/filesystem collectors report success, no ZFS metrics;
    - virtualized MemTotal matches /proc/meminfo, root size matches statvfs;
    - memory reading within 3 percentage points of /proc/meminfo and root usage
      within 0.1 points of statvfs; non-root filesystems excluded;
    - Pi-hole and Unbound answer normal queries over UDP AND TCP;
    - Pi-hole, Unbound, and SSH PIDs/restart counts, configuration, addresses,
      routes, and available iptables rules remain unchanged.
  Packet counters/export timestamps are normalized out of iptables fingerprints.
  Native nft-only policy is not fingerprinted when no iptables-save frontend is
  installed; no firewall tooling/rules are installed to improve that coverage.
  CPU counters are checked for presence, not validated as a CPU utilization rate.
  CPU-rate/cgroup semantics, Prometheus reachability, missing-data handling, and
  dashboard integration require the later monitoring phase. No endpoint restart
  or DNS settings change is attempted to work around a failed check.

Rollback — ON ORTHANC, after reviewing any drift
    pct exec 110 -- python3 - rollback BACKUP_DIRECTORY < /root/palantir-node-exporter.py

  Checks recovery integrity and ownership, expected package version and unchanged
  agent files, and rejects removal of other packages. Stops/disables ONLY the new
  exporter, purges ONLY prometheus-node-exporter (no autoremove), removes ONLY its
  reviewed drop-in, reloads systemd, and rechecks protected services/configuration.
  Retains the private recovery directory and standard package-manager history.
  A Debian-created prometheus system account may remain; never delete a possibly
  shared account automatically. Existing global apt/package state is not restored.

Failure handling and limitations
  On installation/verification failure, disables/stops ONLY the new exporter and
  prints the recovery directory. It never restarts Pi-hole/Unbound/SSH or restores
  protected configuration. Review the private install log before rollback.
  A partially configured or different package version requires manual package
  review; the rollback mode refuses speculative apt repair or force options.
  Run verify immediately: later legitimate service/config changes will fail the
  strict baseline comparison and require review, not automatic restoration.
  Root-run native package installation entails trusted repository maintainer
  scripts/hooks. The dry run and NEEDRESTART_MODE=l limit expected scope; the
  post-checks detect a protected-service restart rather than undoing it silently.
  Restrictive LXC cgroup policy or denied service startup may prevent deployment;
  the script stops instead of changing container privileges or security settings.
  Candidate drift/unavailability requires a reviewed version update to this
  script, not adding Ubuntu repositories or upgrading the system.
  The script has NOT been executed on any system. Validation is static review
  and syntax compilation only; service startup, rollback, and metric checks remain
  untested until separate deployment authorization.

Upstream/package references
  https://packages.debian.org/bookworm/prometheus-node-exporter
  https://sources.debian.org/src/prometheus-node-exporter/1.5.0-1/collector/filesystem_common.go
  https://github.com/prometheus/node_exporter#collectors
