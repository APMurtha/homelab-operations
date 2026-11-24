# Celery readiness: staging candidate; production remains held

Issue #40 did not enroll Celery. Issue #42 covered only relay, backend, gateway,
VPN-container and Jellyfin. On November 23 the newest retained historical
Celery pass was at 04:11:39 UTC, well outside the 60-second validity limit.
Stored Docker health and the application's Redis-backed **uWSGI** heartbeats
are not evidence of Celery broker responsiveness. Keep live Celery unavailable.

## Read-only Rivendell source findings

The two passive bracket passes took 0.120 s and 0.114 s. They agreed on the
full backend container ID, PID/start tuple, worker-master PID/start ticks,
and cgroup and PID, network, mount and UTS namespaces. Both worker masters
are distinct and in the backend container's cgroup and namespaces; exclude
the shell wrappers and prefork children from the observation. Deployed
Celery's worker CLI expands its actual configured default/DVR nodename
templates against the backend hostname. The exact configured names were
verified privately; do not publish host-specific worker or runtime IDs.

Joining worker open socket inodes to the backend namespace's existing TCP
table independently found both workers connected to Redis on loopback
port 6379 inside the VPN-shared namespace. Stored backend creation settings
specify Redis DB 0 and no separate read/write override. These are passive
configured identity and kernel endpoint observations, not a proof of the
live logical DB, control namespace, worker reply authenticity, or
runtime readiness. No production ping, broker request, task execution,
payload capture, service/configuration change, or enrollment occurred.
A genuine before/after bracket spanning a real production capture remains
to be qualified under a separate grant.

## Acquisition and exclusive publication

- The staging core uses one Celery 5.6.3 destination-scoped
  `inspect ping --timeout=8 --json` with the two enrolled **full exact
  names**, no task, 12-second subprocess deadline, 16 KiB max per pipe in
  memory and no raw-output retention. It waits for leader exit without
  reaping, signals the original process group, then reaps; a child escaping
  that group requires the independent launcher/cgroup boundary.
- Exit 0, strict complete UTF-8 JSON, empty stderr, no duplicate keys at
  any depth, only enrolled exact names and exact pong values are
  required. A nonempty validated set of one role is `readiness-failed`
  (no positive witness for the other role, not a confirmed outage). An
  empty or malformed capture, broker/transport error, nonzero exit, clock
  discontinuity or timeout is unavailable.
- Two trusted bounded passive adapters must report the same producer
  boot, full backend container ID/PID/start time, both enrolled PID/start
  tick tuples and a fresh healthy backend. The fixture output timestamp
  remains the earliest of acquisition start and the input engine probe
  timestamps; publication never refreshes it. The unchanged wire format
  and vocabulary expire at that original time plus 60 seconds.
- A dedicated fixed `celery-v1/` subdirectory under the existing evidence
  directory holds the exclusive Celery path. The existing multi-observation
  projector no longer writes or unlinks Celery; the collector ignores the
  old top-level Celery file. A provisioned same-group 0640 anchor is
  used only for shared/exclusive nonblocking synchronization. A writer
  withdraws any previous commit before capturing and creates a new lease
  inode, never relocking an old one. An atomic receipt and fail-closed
  commit gate bind stable inode/owner/group/mode/size/time signatures of the
  drop, anchor, lease and receipt. Commit creation and its final contents
  happen while the writer holds the exclusive anchor, so a partial commit
  or crash can never serve a positive. The reader holds the shared anchor
  throughout the bounded file reads and verifies the exact signatures and
  liveness before and after reading.
- Linux open-file-description write locking requires an actually writable
  lease descriptor. The restricted reader only queries conflicts through a
  read-only descriptor and cannot assert liveness. No publisher, dead
  publisher, missing or replaced anchor, invalid owner or mode, malformed
  or incomplete commit, receipt replacement, unsafe directory, wrong
  group, or expired observation cannot return a current positive. The
  result is point-in-time during the active lease only; expiry still wins.
  An OFD lock follows its open file description, not a PID: the
  anchor and lease are CLOEXEC, the capture uses close_fds with no passed
  descriptors, and the pinned publisher must never fork an inheriting
  child or transfer the lease descriptor. Enforce whole-cgroup teardown.
  Read-time revalidation is not an assurance about a future operation or
  a restart after the final worker bracket. An unprivileged reader may
  contend for its read lock; this can withhold but cannot forge evidence.
  A malicious root/custodian is outside this trust boundary.
- Acquisition is not launched by untrusted issue content. The caller,
  executable, app, full names, broker binding, and passive adapters must
  be fixed in a separately reviewed launcher/enrollment. This branch adds
  no production launcher, root privileged callable dispatcher, Docker
  socket allowance, lease-holder service, timer, credential or policy
  installation. Production drop must be boot-local under /run, root-owned,
  with the enrolled read-only observer group; no inherited old boot state.

## Qualification and remaining enforcement gate

Opt-in Bag-End tests used two real unprivileged Celery workers and disposable
Redis with TCP disabled, no persistence and a private Unix-domain socket;
container metadata was synthetic. In the staged leased path, obtaining
both pongs and publishing took approximately 1.04 s and losing the broker
became unavailable in approximately 3.05 s. The reader returned both-ready
only while the live lease existed. The separate transient user-cgroup test
used a fixed fixture with independently bounded witness subprocesses,
NoNewPrivileges, zero capabilities, seccomp, bubblewrap-private
filesystem/PID/network views, and observed an actual setsid descendant for
each path. Both clean and forced runtime-limit runs left empty cgroups;
startup and runtime tests took approximately 0.8 and 2.2 seconds. An
additional isolated run at the production candidate's exact 17-second
configured limit left an independent one-second margin for launch/teardown
and the fixture asserts wall time below 18 seconds with cgroup empty; it did not run the host-facing adapter. The
cgroup test did not access a real runtime backend or use a broker.
A separate real loopback SSH forced-command fixture, using disposable keys,
actually read `both-ready` only while the candidate's OFD lease was live and
returned unavailable following its closure. The staged allowlist mounted
only the fixture code/evidence read-only; native cBPF mirrored the installed
socket-related deny list. AF_UNIX/INET/INET6 creation was actually refused;
host credential and Redis/Docker socket paths were hidden, and the reader
could not reopen or lock the lease as writer. The fixture deliberately
substituted its unprivileged owner for the production root/observer-group
binding; it is not a test of the installed Rivendell AppArmor profile.
Offline regressions cover lock/receipt corruption, missing/dead publisher,
live contention, kill before withdrawal and after commit, interrupted commit,
restore-mode non-revival, lease forgery, TTL, and fresh recovery. The existing
relay/four-container readers and unrelated media were not changed on production.

Rivendell's existing AppArmor policy names the old top-level Celery projection
and does not allow the new directory/module. Its native seccomp deny list blocks
socket and related syscalls, and does not deny fcntl. The exact file-only
review delta is `celery-observer.apparmor.patch`: one read-only Python module,
one read-only fixed directory, two specific read/lock paths and two specific
read-only files; remove the superseded top-level access. No network, write,
credential or Docker access is added. The existing profile and candidate
were reviewed and the candidate compiled with `apparmor_parser -Q -T -K`
(no kernel load or cache writes); this is not a production policy test.
Pin a host-specific active-profile test to verify lock syscall mediation,
drop traversal and denied access on the exact dedicated account before
ever enabling a real producer. Do not infer deployment authorization
from an unprivileged test or installed capability.

Run default offline tests:
`cd supervisor && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v`.
Run the independent broker fixture in that directory with
`SAMWISE_CELERY_STAGE=1`, `SAMWISE_STAGE_REDIS`, and
`SAMWISE_STAGE_LIBRARIES` pointing to independently verified existing
staging dependencies. `SAMWISE_CELERY_CGROUP_STAGE=1` enables the disposable
Bag-End user systemd/bubblewrap tests; with `SAMWISE_TEST_SSH=1` it also
runs the scoped real SSH reader fixture. No command installs dependencies,
changes a persistent system setting, or touches Rivendell.

## Fixed host-facing launcher candidate and passive follow-up

`celery_shadow_launcher.py` defines the exact host-side transient wrapper and
worker entry, without installing or invoking it on Rivendell. It accepts no
issue-provided parameters, validates a root-owned one-time expiring permit for
the canonical Rivendell target and current boot, pins backend full ID/PID/start,
network namespace inode, full enrolled names, endpoint and privately established
broker/control scope, and pins both site-adapter SHA-256 values. It launches
one fixed unit only, independently rechecks the approved permit digest in its
worker, verifies cgroup/namespace, and consumes its nonce once before
any observation. A positive local worker phase is not returned as readiness:
only the separate read-only observer can read a live leased sample. The fixed
path supports one witness subprocess before and one after, each independently
limited to one second; an eight-second reply request with a 12-second process
cap; and up to three seconds for the separate lease reader. systemd owns an
independent 17-second service budget, no restart, unconditional cgroup-wide
kill, reserving one second for outer startup/teardown against the 18-second
operational cap. The worker refuses launch beyond that one-second startup
margin on the same boot monotonic clock and clamps the lease to the outer
deadline. Unbounded host scheduling delay is still an abort gate. The
producer uses a closed environment and fixed executables, never sends commands
to the collector, and has no direct Docker access. A local IPv4 allowlist is
not port filtering: the pinned, reviewed broker adapter must additionally
enforce the exact port and authenticate its scope before enrollment.
Adapter binaries, their permit and an active integration are **not** enrolled
or distributed by this draft. No shadow attempt may occur with missing or
unqualified adapters.

Passive follow-up corroborated that the two actual worker masters do not
inherit the Docker-creation CELERY_BROKER_URL as a direct override. Their
startup fallback inputs resolve to loopback Redis port 6379, DB 0, with no
separate read/write override. The deployed Django/Celery/Kombu configuration
also resolves the default celery.pidbox exchange, DB-prefixed fanout, no
global broker key prefix. Exactly two matching role masters were seen in
the backend, but the existing passive sources did not expose live in-memory
effective control settings or broker-wide exclusive subscriptions. No
credentials, raw env, worker outputs or private identities were recorded
here. Startup configuration plus open TCP sockets is **not** live broker
attestation or readiness.

The existing restricted SSH account is UID 999, primary GID 985 and has no
supplementary or Docker group membership. The installed observer mode is
root-owned evidence directory 0750 with group 985, the fixed SSH ForceCommand,
key-only admission with source restriction, no forwarding, PTY, interactive
auth or environment, an enforcing baseline `samwise-observe-v1` profile and
a kernel seccomp socket-deny launcher. The installed profile does not permit
the candidate module/drop. The candidate exact file-only diff compiles
offline, but its active profile has not been loaded on any host: staging
inventory contains no equivalent already-authorized loaded disposable
profile. Staging proved the confinement mechanisms and real disposable
SSH equivalent, not production root/group/AppArmor mediation or the exact
site broker adapter.

Exact-profile activation requires separate action-time authorization,
preferably on a disposable replica only. Scope that grant to loading only the
named, hash-verified candidate profile in the disposable replica, staging
the exact UID/GID and synthetic evidence, and verifying open/lock mediation
on the four fixed files, failure on missing/dead lease, and that writes,
sockets, broker/Docker data, credentials and all unrelated reads remain
denied. No production login, network request, key or permissions expansion
is needed. Keep the installed Rivendell baseline independent, unchanged,
and preserve the working relay and four-container paths.

## Proposed separately authorized one-shot, not part of this draft

1. First review and stage the exact production fixed launcher and file-only
   profile on an isolated unprivileged fixture. Configure only independently
   verified full roles, broker/control namespace and container binding;
   recheck PIDs/start ticks plus same cgroups/namespaces against the confirmed
   backend incarnation. Verify the actual production AppArmor/seccomp
   confinement and exact account behavior using a separately approved
   isolated validation. No access expansion to the observer. Abort if any
   source, identity, role, boot, UID/group/mode, path or clock drifts.
2. After an explicit one-shot owner grant only, take passive snapshots
   before/after exactly one fixed ping (8 s reply timeout, 12 s maximum
   execution). Reserve two seconds total for independent witness enforcement,
   plus up to three seconds for one read of the sanitized result while that
   exact lease remains live. Cap service runtime at 17 seconds and treat
   18 seconds as the outer wall budget including cgroup teardown,
   deny any extra broker destination and use cgroup-wide teardown, including
   escaped groups, on success and timeout. No retries, task, playback,
   restarts, scheduling, or production rollout. The source timestamp is
   the actual oldest contributing UTC witness, not time of reporting.
3. Compare one sanitized result and original sample time with the private
   authorized bracket. Record time, resource cost and cleanup. Report
   unavailable on an ambiguous or missing result, not healthy. Keep the
   existing 60-second TTL only as an upper bound; the live lease can end
   much earlier. A future continuous schedule requires a separate design
   and permission; one-shot passing does not qualify a daemon/timer.
4. Before any separately authorized policy/collector action, capture
   byte hashes, UID/GID/mode/link count, active enforce state, fixed SSH and
   seccomp fingerprints and the relay/four-container modules, outputs and
   timers. Keep verified private backups. Abort/rollback by stopping only
   the candidate's cgroup, confirming it empty, closing its lease and
   withdrawing only its shadow files. If profile/module changes were made,
   atomically restore only the confirmed original files, ownership and
   original policy under explicit approval; verify the same profile is
   enforcing, files and relay/four-container checks match, and Celery is
   unavailable. Never restore an old Celery receipt or restart media/workers.
