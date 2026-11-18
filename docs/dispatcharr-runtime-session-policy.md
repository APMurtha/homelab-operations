# Rivendell SSH session-policy verification

**GO for the approved transport under the inspected policy.** Recommend a
**separately authorized** isolated application test; none was launched here.
Ordinary SSH disconnect is expected to leave the detached supervisor/worker alive.
This is a read-only compatibility assessment, not an empirical disconnect result.

Baseline: `8f8d719242146fc1cea67bd15a2f0bfafa540b24`.
Observed `2026-11-18T04:32:28.472109+00:00` on Rivendell, systemd
`255.4-1ubuntu8.18`. NEST's pinned `andrew-media` / `media` profile verified SSH
account **murth, UID 1000**. Only normal foreground inspection commands were run.

## Effective policy and session evidence

| Item | Observed value |
| --- | --- |
| Live login1 Manager `KillUserProcesses` | **false** |
| Live `KillOnlyUsers` / `KillExcludeUsers` | Both empty arrays |
| Live `UserStopDelayUSec` | 10,000,000 (10 seconds) |
| Selected account | Static NSS files account; `/bin/bash` |
| User manager / linger | `user@1000.service`, active/running; **Linger=no** |
| Current SSH scope | `session-623.scope`, active/running; Service=sshd, Type=tty, Class=user |
| SSH command cgroup | `/user.slice/user-1000.slice/session-623.scope` |
| User-manager cgroup | `/user.slice/user-1000.slice/user@1000.service` |
| Scope runtime maximum / stop-when-unneeded | infinity / no |
| Scope KillMode / SendSIGHUP | control-group / yes |
| User-manager KillMode / stop timeout | mixed / 5 seconds |
| Parent user slice | active; StopWhenUnneeded=yes; TasksMax=20,748 |
| Session cgroup CPU / memory / PIDs | `max 100000` / `max` / `max` |
| Session cgroup OOM group kill | 0 |
| Inherited CPU-time / address-space / file-size limits | Unlimited |

The key kill settings above came from **live D-Bus properties**, not assumptions
from commented defaults. Merged configuration sources were `/etc/systemd/logind.conf`
and the vendor unattended-upgrades max-delay drop-in; no active inspected
kill/exclusion/stop-delay override appeared. Empty exclusion arrays are reported
as observed; no root-user default is assumed or needed for this non-root account.

No selected-account public `.user` override was found under `/etc/userdb`,
`/run/userdb` or `/usr/lib/userdb`. NSS order is `files systemd`; UID 1000 resolves
from files. homed and userdbd units are not found; only the DynamicUser
service endpoint exists. `userdbctl` is absent and was not installed. No per-user
kill override was found in those available sources; the user D-Bus object does not
export a separate kill-policy record.

## Why the policy is compatible

NEST invokes OpenSSH with `-T` (no pseudo-terminal); login1's Type=tty label
is its session classification, not proof of an allocated terminal.
The inspected command and its sshd ancestry are in the SSH session scope, a
**sibling** of the user-manager cgroup. The approved double fork/setsid code changes
POSIX session/process-group membership and detaches inherited streams; it does
**not** migrate the supervisor or worker out of that cgroup.

With `KillUserProcesses=false`, ordinary logout abandons the populated session
scope instead of requesting its termination. systemd 255 explicitly supports
waiting for remaining processes in a closing session. Its forced termination path
is separate. This is the relevant distinction despite the scope's
`KillMode=control-group` and `SendSIGHUP=yes`; those properties do not imply that
normal logout requests a stop. See the [255 logind policy](https://www.freedesktop.org/software/systemd/man/255/logind.conf.html#KillUserProcesses=)
and [session-stop implementation](https://github.com/systemd/systemd/blob/v255/src/login/logind-session.c#L765).

`Linger=no` permits later shutdown of the user manager; it does not place this
transport under that manager. The inspected SSH scope requires the parent slice
and has no BindsTo/PartOf relationship to `user@1000.service`. Its remaining processes
keep the scope populated. systemd's [user-stop implementation](https://github.com/systemd/systemd/blob/v255/src/login/logind-user.c#L438)
stops the user service and relies on dependency/StopWhenUnneeded handling for its
slice. The transport uses private `/tmp` receipts and the system Docker socket;
it does not depend on `/run/user/1000`, a user-service manager or a user bus.
No linger or other policy adjustment is needed for this design.

## SSH and cleanup checks

Effective sshd inspection succeeded. `UsePAM=yes`, `ForceCommand=none`,
`ChrootDirectory=none`, `ChannelTimeout=none`, `UnusedConnectionTimeout=none`,
`ClientAliveInterval=300`, `ClientAliveCountMax=2`, and `TCPKeepAlive=yes`.
Those keepalives govern the SSH connection, not an independent detached job.
`UseDNS=yes`, but the inspected configuration/include tree has **no Match blocks**,
so hostname-match ambiguity did not affect these settings. No custom SSHD_OPTS
were configured. `ssh.service` is active, KillMode=process, SendSIGHUP=no,
RuntimeMaxUSec=infinity.

PAM uses the normal session stack including `pam_systemd.so` with no extra options;
no pam_exec/custom session cleanup helper was present. The three configured
selected-account authorized-key entries had no forced-command or environment
options. AuthorizedKeysCommand=none and PermitUserEnvironment=no. No system or
user sshrc exists. The existing `.bash_logout` had no detected process-termination
command pattern; this noninteractive exec flow is not a login-shell logout flow.
No key material, client addresses, authentication secrets or raw environment values
are published.

## Remaining uncertainty and decision

**No inspected policy would kill the supervisor/worker solely because the normal
SSH connection closes.** Thus the session-policy prerequisite supports GO. This
does not guarantee survival of explicit `loginctl terminate-*`, direct scope/user
slice stops, administrative kills, OOM, reboot, policy changes or filesystem failure.

No detached canary, live disconnect, timeout, signal or background experiment was
performed. The actual on-host handoff, signal timing and abandoned-scope lifetime
remain empirically untested; prior local synthetic disconnect tests are separate
evidence. This assessment infers expected behavior from live settings, cgroup
placement and systemd semantics. Future preflight must stop if those facts change.

The approved transport/runner are byte-for-byte unchanged. There were **zero Docker
operations, transport/application launches, service restarts or configuration
changes**. No application/container health claim is made by this narrowly scoped
inspection. Preserve previous receipts, use a fresh exclusive ID, and obtain
separate authorization plus normal artifact/health/capacity preflight before one
isolated application attempt. Do not relaunch after a lost SSH response; monitor
the same attempt read-only.

Sanitized evidence: `configs/dispatcharr-iptv/hardened-image-integration/runtime-session-policy-results.json`
(SHA-256 `452af79c597d773896f1f719cc914438f891733b461712dac1e59d022a84b882`). It contains the live property values, unit/cgroup snapshots,
redacted SSH/PAM checks and inspection-source hashes. No runtime code, manifest,
policy or installed file was modified. **Stop after publication.**
