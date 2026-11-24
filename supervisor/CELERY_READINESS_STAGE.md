# Celery control-plane readiness: operational one-shot

This draft qualifies a least-privilege, fixed-scope Celery **readiness
observation**, not per-worker cryptographic identity. It does not install
a monitor, register a timer, mutate the application, or authorize production
execution. The local publication candidate must be reviewed and approved
separately before reaching the existing public PR.

## Security model and choice

Use the conventional [Celery remote-control ping](https://docs.celeryq.dev/en/stable/userguide/workers.html#remote-control)
inside an **operator-reviewed application trust boundary**. The pinned
[Kombu pidbox implementation](https://github.com/celery/kombu/blob/v5.6.2/kombu/pidbox.py)
defines how the bounded collection delivers its raw reply list. Two exact worker names must reply, the
enrolled host/guest process identities and the broker endpoint must be
consistent before and after, and a separate file-only observer must see
the result during the publisher lease. This shows that the expected
control-plane names responded in scope during this sample. It does not
measure task execution, queues, throughput, media quality, or the
cryptographic identity of the reply origin.

Redis pub/sub does not attach an authenticated publisher identity to a
Celery pong. A process allowed to publish on the relevant broker paths
can emit a name. Loopback, the selected Redis DB, the exchange, a matching
UID, and identical before/after process identities establish consistency,
not isolation from broker-capable peers. This design assumes **all**
principals that can publish on the selected control/reply paths are
trusted for this observation. Do not enroll the site on reachability
alone. Review actual shared-network members, host/namespace entry rights,
broker transport/ACLs or isolation and control publishing authority.
An unknown, unreviewed, or untrusted writer is a hard no-go; leave Celery
unavailable or separately design stronger isolation. Never enumerate or
test this on production by publishing messages.

Per-worker signing could assert an independent source only with controlled
per-worker keys and independently authenticated incarnation enrollment,
rotation and revocation. Privilege sharing, copied keys, or handing out
the same trust root undermine that advantage. That engineering and
operational cost is disproportionate for this trusted application
readiness observation. There is no signer, key, UID migration, or signed/
legacy fallback in the active producer.

## Acquisition and refusal

* A fresh, root-owned, hash-pinned one-shot permit binds the reviewed
  boundary inventory digest, source hashes, boot, backend incarnation,
  target namespace, exact names and reviewed broker scope. The private
  inventory itself is not stored in the receipt or Git. Record the
  authority and inspection that make each reachable principal trusted.
  Revalidate immediately before each one-shot: the digest binds the
  manual trust decision, not a live membership detector. An idle or
  same-UID entrant can be invisible to the runtime witness. The renderer
  hashes the record, it cannot approve it.
* A single transient, zero-capability systemd service joins only the
  pinned backend network namespace. The witness checks readable host
  procfs PID/start/command/cgroup/NSpid information, fresh backend health
  and its own Redis endpoint. It reads no foreign process FD directory
  and needs neither SYS_PTRACE nor DAC override.
* The child requires the exact boot, current network namespace, fixed
  service cgroup, boundary enrollment hash and monotonic cutoff before
  dialing. systemd restricts traffic to the fixed loopback address;
  native Landlock additionally restricts TCP port and app/runtime files;
  native seccomp denies other socket types, signal sends, subprocess and
  namespace changes. The reviewed implementation requires x86-64 Linux,
  Landlock TCP ABI 4+, functioning systemd cgroup v2 and cgroup IP policy,
  libseccomp, the pinned stdlib and immutable Celery/Kombu/Redis archive.
  The native child refuses if its own kernel guards cannot apply. An
  unsupported systemd can ignore cgroup address filtering: the property
  alone is not evidence. Verify effective kernel enforcement in a separate
  disposable local-only cgroup on the target before authorizing any live
  ping; refuse production rollout if it is unverified. The Python audit
  hook binds the reviewed client destination but is not a kernel IP filter.
* The helper makes one destination-scoped `ping` with an eight-second
  collection interval, no command from user data, no task execution and
  no retry. It checks the real transport database/control/reply exchange
  and serializer/key-prefix settings. It examines the raw list, with
  an explicit limit of three so an observed third reply cannot be hidden
  by Celery flattening or normal destination-count termination. Only
  exactly two unique expected `{"ok":"pong"}` replies qualify. This
  says nothing about replies outside the collection horizon.
* Missing, stopped, late or renamed workers, wrong scope, malformed,
  duplicate or unexpected observed replies, a contradictory witness, and
  stale/missing/dead receipt all read unavailable, not a confirmed outage.
  One healthy response is not both-ready. The fenced reader needs a
  current matching commit and the OFD publisher lock. Failed acquisition
  cannot resurrect a previous healthy receipt.
* One bounded wrapper (18 seconds), transient unit runtime (17 seconds),
  broker command budget (12 seconds) and one process timer bound execution.
  Both witness process and broker helper are in that same cgroup; no
  detached restart or separate service survives its cancellation. The
  test runner checks teardown without treating its emergency cleanup as
  a pass.

## Staging and reproducibility

The tested staging model has split host/guest PID views, a shared but
egress-free application network, and Redis plus two real Celery workers
under the same synthetic service UID. The actual launcher, witness,
broker adapter and UID/GID-restricted native seccomp observer are used.
No production addresses, keys, configs, media, or mounts enter the fixture.

Run offline tests from the commit's `supervisor/` directory:

```sh
python3 -B -m unittest discover -p 'test*.py'
```

On the explicitly approved disposable staging VM only, build a local bundle
of the files named by `stage_celery_operational_vm.py`, the previously
reviewed observer's native `launch.py`, disposable `redis-server`, and
the pinned runtime package directory `pkg/` (Celery 5.6.3, Kombu 5.6.2,
redis-py 6.4.0). Verify the code/version manifest and runtime checksums
before transfer; the renderer writes the hash of the actual staged ZIP.
For the media test, supply a user-approved dependency directory
`media-root/`, created by extracting official Ubuntu package files
without installing them. This run used FFmpeg 8.0.1-3ubuntu2 and its
extracted libraries. The harness checks the executable SHA-256,
generates a synthetic color/sine clip, and decodes only its own loopback
HTTP transport.

```sh
sudo timeout --signal=TERM 42 /usr/bin/python3 -IB   stage_celery_operational_vm.py "$BUNDLE"
```

The optional final argument names a synthetic fault; see the allowed
choices in the script. Verify the KVM guest and trusted SSH host key from
private inventory first. The harness refuses existing fixed paths/cgroups,
owns the temporary children/files it creates, and never loads AppArmor.
The native observer, policy patch, protocol, lease handoff code, paths and
format match the previously enforced reader test byte-for-byte. This
operational producer test does not reload the already qualified observer
profile and is not a new end-to-end AppArmor load. Requalification of new
reader/policy bytes would require separate approval.

The same native observer returned unavailable before the lease, both-ready
during it, and unavailable after closure. The positive run containing
the actual renderer and representative continuous playback took
**12.966 seconds**, sampled **1.521 CPU seconds** and a **45.43 MiB**
cgroup peak, and left the publisher cgroup absent. The service had zero
capabilities and Seccomp mode 2. All five synthetic legacy observations
and their hashes were unchanged. One HTTP MPEG-TS audio/video decoder
advanced **16 → 192 → 244 → 315 frames** before, during, after, and at
completion, with no decoder errors. This is not production media,
provider, user player, or SSH authentication validation.

Representative fault runs of the exact generated unit, no positive
receipt and cgroup absent:

| Synthetic fault | Observed wall time |
| --- | ---: |
| Either worker dead; Redis stopped/replaced; unexpected peer UID | 0.49–0.51 s |
| In-flight cancelled after both worker handlers got the ping | 1.77 s |
| Either worker slow; wrong exchange; malformed reply | 9.74–9.85 s |

The offline raw reply tests additionally validate third observed replies,
unexpected names, duplicates, bad transport options and partial replies.
The prior unchanged observer enforcement and kernel IP/port tests supply
separate layer evidence; they are not a new live production test.

## Production procedure (operator only, not pre-approved)

1. **First stop if the trust boundary cannot be established.** Compare the
   reviewed release and immutable payload manifest to the target. Obtain
   only read-only local metadata: host boot, exact process and backend
   incarnations, namespace, worker full names/queues, Redis endpoint and
   non-secret control configuration. Review every principal able to
   publish replies from the shared namespace, including how namespace
   access and sharing are controlled. Reject unknown participation,
   weaker/missing restrictions, unrelated broker sockets, unsupported
   kernel or missing fresh health. Write root-owned, private
   `witness-snapshot.json`, `backend-frame.json`, and an operator-reviewed
   `boundary-inventory` documenting the justification. Do not copy
   secrets, environment dumps, names/IDs or private addresses to Git.
2. **Build and independently review payloads** in a root-owned private
   staging directory. Use the tested x86-64 stdlib/native libraries, exact
   runtime ZIP, witness executable and pidbox adapter. Use these fixed names
   in `$PAYLOAD`:
   `witness` from `celery_operational_witness.py` (0755),
   `pidbox-ping` from `celery_site_pidbox.py` (0755),
   `celery_broker_guard.py` and `pidbox-runtime.zip` (0644).
   Verify each source/dependency hash against the reviewed manifest.
   Prepare the four records **offline** using `$NODE` as the exact existing
   production launcher node selector and epoch nanoseconds from the trusted
   target clock:
   ```sh
   python3 -B render_celery_operational_enrollment.py      --witness "$PRIVATE/witness-snapshot.json"      --health "$PRIVATE/backend-frame.json"      --boundary "$PRIVATE/boundary-inventory"      --payload "$PAYLOAD" --output "$NEW_PRIVATE_DIR"      --node "$NODE" --now-ns "$NOW_NS" --ttl-seconds 60
   ```
   The command refuses to overwrite an output and cannot install or run
   anything. Refresh if stale; never retry a consumed permit or edit a
   deployed enrollment in place.
3. **Separate approval before any install, profile change or live ping.**
   Snapshot existing observer/collector/loader bytes and modes and the
   entire policy inventory; stage the exact reviewed AppArmor file-only
   delta without applying it. Confirm baseline hash, policy SHA,
   interpreter paths, and how rollback restores only modified files.
   Check the existing observer account/group already match
   `OBSERVER_UID`/`OBSERVER_GID`; do not change accounts. Use only
   root-owned, non-writable ancestors. Under installation approval install
   precisely the reviewed launcher and its four flat dependency files
   (`celery_readiness.py`, `celery_handoff.py`, `dispatcharr_project.py`,
   `ops_protocol.py`, all 0644) plus `$PAYLOAD` to
   `/opt/samwise-celery-shadow` (0755). Install the three private enrollment
   records there mode 0600 and `backend-witness.json` mode 0600 in
   `/run/samwise-celery-shadow` (0700). Create only the Celery drop under
   the existing observation parent: root:existing observer group
   `/run/samwise-observations/celery-v1` (02750) with mode-0640
   `.celery-acquisition.lock` and no prior Celery data.
   If needed and separately approved, install only the reviewed compatible
   observer Python module/collector and exact file-only AppArmor change,
   without changing the native socket-deny launcher or five baseline
   paths. Dry compile with `apparmor_parser -Q -T -K`; do not replace an
   unknown incumbent. Verify baseline observations before any active check.
4. **Separately approved shadow only.** With the fresh permit in place,
   invoke these fixed commands on the approved target:
   ```sh
   sudo /usr/bin/python3 -IB /opt/samwise-celery-shadow/celery_shadow_launcher.py --plan-only
   sudo /usr/bin/python3 -IB /opt/samwise-celery-shadow/celery_shadow_launcher.py --launch
   ```
   The plan command makes no broker request; its success is not health or
   a production grant. Coordinate one sanitized read through the existing
   restricted observer during the live lease, triggered by the reviewed
   root-local update to `.celery-publication.json` in the Celery-only
   drop. Verify unavailable after exit, generated cgroup absent, and all
   five existing observations unchanged. A failed sample is not retried.
   Do not install a timer from this one-shot candidate. Recurring/live
   dashboard monitoring needs its own reviewed scheduling and freshness
   contract and separate approval.

## Rollback (operator only)

Stop only `samwise-celery-shadow-once.service` if it exists; verify that
its cgroup is absent before cleanup. Retain the consumed-permit marker
until verified withdrawal or reboot so a stale permit cannot be reused.
Remove only the root-owned reviewed Celery receipt/lease/drop and shadow
install/state files created by the approved rollout. Restore only changed
observer files and the original verified file-only profile captured
beforehand. Verify the baseline policy inventory, restricted user, native
socket denial and all five baseline observations. Never copy back a
previous healthy Celery receipt. Do not restart or reconfigure Redis,
workers, the relay, provider, media stack, or dashboards for a change
that only touched the monitor.
