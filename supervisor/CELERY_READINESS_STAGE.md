# Celery readiness acquisition: staging candidate, not deployable

Issue #40 did not enroll Celery. Issue #42 verified only relay, backend, gateway,
VPN-container and Jellyfin. The newest trustworthy Rivendell worker receipt
seen on Nov 23 at 23:23 UTC was the two-role pass from 04:11:39 UTC (root-owned
0600); it was historical, not current. The running Docker health feeds and
uWSGI Redis heartbeat do not prove Celery default/DVR broker responsiveness.
Leave the current production Celery observation unavailable.

## What was qualified

The acquisition core accepts owner-enrolled **full, distinct nodenames** with
the exact default/DVR roles, and one Celery 5.6.3 destination-scoped
`inspect ping --timeout=8 --json`. No task is invoked. The subprocess has a
12-second deadline, process-group cleanup on timeout/overflow, and a 16 KiB
limit per in-memory pipe. It accepts only complete, strict UTF-8 JSON with no
stderr, exit 0, unique keys at every depth, known exact destination names,
and exact pong objects. An empty capture, malformed or ambiguous structure,
broker failure, or transport timeout is unavailable. A completed valid reply
from exactly one enrolled destination is `readiness-failed` (one role lacks a
positive witness, not proof that this worker is down).

The trusted passive before/after witnesses must agree on producer boot UUID,
the full backend ID/PID/start-time tuple and both enrolled worker PID/start
ticks pairs. The engine row must be healthy in both witnesses. Duplicate PIDs,
wrong boot, restarts/name reuse, bad clocks and stale health fail closed.
Expiry is 60 seconds from the **earliest** bracket time or contributing engine
probe, not the publication time. A nonblocking lock allows only one scoped
acquisition and the prior projection is withdrawn before acquisition, including
while a subsequently failed probe is in flight. Publication atomically replaces
only the existing sanitized Celery observation, using the current wire format
and projector validation; there is no second raw receipt or new vocabulary
and no credential, broker URL, worker name or raw output in the projection.
The existing consumer can read the existing file format. A nonqualifying
or failed acquisition cannot keep the previous pass authoritative.

Two actual unprivileged Celery workers (separate PIDs/start ticks) and a
disposable Redis broker used a private Unix-domain socket on Bag-End with
TCP disabled, no persisted Redis data, no production credentials/network,
no task invocation and all processes cleaned up at exit. The backend
container metadata was **synthetic**; the pass proves the Celery CLI/Redis
behavior and consumption, not production Docker identity, namespace, broker
configuration or AppArmor. Local fixture wall time was about 1.08 s for
both-ready, 3.10 s for broker loss becoming unavailable. These are
fixture timings, not production CPU/load projections. The standalone
integration test is opt-in; normal tests never start it.

## Production opt-in gate (separate authorization, not included here)

- Review and authenticate full enrollment and provenance for both names,
  worker process identities (PID/start ticks with container PID namespace /
  cgroup membership) and exact broker endpoint/namespace. Prove passive
  before/after observations actually span the single capture and prevent a
  PID/name from another process or container satisfying the witness.
  Pidbox pong semantics show responsiveness **at acquisition**, not successful
  task execution or ongoing health. A restart after the final bracket cannot
  be observed until a new sample or expiry; do not make stronger claims.
  A broker peer that can impersonate an enrolled name or an upstream library
  that discards duplicate replies before serialization cannot be detected by
  this parser alone. Require a closed trusted broker/control namespace and
  verify uniqueness operationally; unresolved identity ambiguity blocks enrollment.
- Review the callable adapter boundary. The committed core has **no production
  entry point**, application/engine credentials, Docker exec/sock access,
  installed unit, timer, network rule, host-policy change or transport selector.
  The trusted before/after adapters must each have independently enforced
  short deadlines (budget 2 seconds total), exact name/host scope, and
  no general shell, environment dumps or raw output. The capture adapter
  should use only the approved executable/app, fixed broker and two exact
  destinations. Do not let an issue value choose a command, destination,
  app, endpoint, identity or output path. Run in a reviewed constrained
  producer or ask for separate approval if that constraint is not achievable.
  The restricted collector must remain read-only and unable to contact Docker,
  the broker, network or credentials.
- Integrate one exclusive owner of the Celery projection in the existing
  approved reader-visible directory and confinement model. The staged core
  requires a private 0700 output directory and runs with test ownership;
  do not point it at the shared production directory or run it next to the
  multi-observation projector. Review an exclusive publication handoff and
  reader/writer ownership/permissions before any installation. Verify other
  observations, four-container publisher, relay, V2/V3 and media services
  byte-for-byte or with known continuing health before and after.
- Start with an independently approved one-shot, not a production timer.
  If bounded execution, original probe timestamps, hardware cost, broker
  scope and all preservation gates pass, propose 15 seconds start-to-start,
  at most 12 seconds for capture + 2 for witnesses, no retries or overlap,
  60-second validity capped by the oldest contributing engine sample. With
  30-second stored Docker checks, 14 seconds max elapsed leaves at least
  16 seconds after a qualifying publish under that ideal max-age assumption;
  verify actual ages/schedule jitter. Missed windows must be unavailable/stale,
  not extended. Withdrawal intentionally allows a temporary unavailable
  window while the next check runs; acceptance must measure this impact.
- Abort on any scope/identity/config drift, unknown host, duplicate worker
  names, clock discontinuity, unhealthy/stale backend, over-budget broker
  activity, lost confinement or any media effects. Stop only the new
  authorized job, withdraw only its Celery projection, restore the verified
  pre-change ownership and compare the existing evidence/collector/timers.
  No worker restart, Docker/guard/VPN changes or rollback of unrelated state.

Run offline: `cd supervisor && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v`.
Run integration in the same directory with `SAMWISE_CELERY_STAGE=1`,
`SAMWISE_STAGE_REDIS` and `SAMWISE_STAGE_LIBRARIES` pointing to the independently
verified existing staging dependencies. It creates only disposable fixtures.
