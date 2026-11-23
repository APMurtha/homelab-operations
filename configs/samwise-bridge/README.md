# Samwise–Codex bridge on Bag-End

Samwise submits a GitHub issue in `APMurtha/homelab-operations` with this exact body:

```text
samwise-task: fixture-count-v1
```

The issue must be created through a GitHub connection that attributes it to
APMurtha (account ID 57697374). Apply `samwise:ready` as APMurtha after reviewing
the body. The worker verifies the author and the latest ready-label actor using
GitHub IDs. If Samwise's connector attributes the issue to a different identity,
APMurtha must open the issue. Comments and titles are ignored. This repository
is public, so keep credentials, private topology and operational requests out
of issues.

## Running the worker

From the Bag-End checkout, manually process a single smoke issue:

```sh
python3 configs/samwise-bridge/worker.py --once --issue ISSUE_NUMBER
```

Use `--poll` to opt into foreground polling every 60 seconds. Stop it with
Ctrl+C. The worker scans up to 100 ready issues per poll and processes at most
one per cycle. An issue with 300 or more history events requires a fresh issue
for review. Cancel queued work by closing the issue or removing its ready
label before execution. A task already started can run for up to 90 seconds.

The repository needs four labels: `samwise:ready`, `samwise:running`,
`samwise:done` and `samwise:failed`. The worker uses the existing local
`gh` login and checks its account and the repository ID before every cycle.
It needs outbound GitHub and Codex inference access. Codex CLI 0.170.0 uses
the existing ChatGPT login, receives only a synthetic fixture, and runs
ephemerally from a temporary directory with the read-only sandbox, approvals
disabled, no user configuration or rules, and shell, web search, plugins,
hooks and apps disabled. The task itself needs no network or service access.
Hosted inference still requires connectivity.

The worker adds the running label before invoking Codex and publishes a
terminal label before removing ready and running. Private receipts under
`~/.local/state/samwise-codex/` contain only the issue number, timestamp,
result code and publication flag. Keep this state directory intact. A local
lock permits one worker, and a durable claim prevents re-execution across
restarts. Unfinished claims are recorded as interrupted and reported as
failed on recovery. Terminal publication is retried without rerunning Codex.
Use a newly reviewed issue to retry a failure. Leave existing terminal labels
in place as an additional replay guard.

NEST's upstream source is `erwich/nest`. Its explicit person/system bindings
and provider authorization still govern any separately reviewed household
work. The bridge does not invoke NEST or inherit its credentials, and needs
no changes to its installed plugin cache. The `worker.py` entry point supports the synthetic fixture count.

## Repository inventory v2

`worker_v2.py` is an opt-in successor that also handles the existing fixture
task. Both entry points use the same Bag-End host guard, lock and receipt
database. Run only one of them against that database. This PR is for code
review. Switching the running service and testing live jobs require separate
approval.

Submit an open issue in this repository with a body containing exactly the
versioned envelope. Substitute the full lowercase 40-character SHA of a commit
reachable from GitHub's `main` and present in the trusted worker checkout.

```text
samwise-task-v2: {"kind":"repo-inventory","revision":1,"commit":"<40-character SHA>"}
```

After reviewing the issue as APMurtha, apply `samwise:ready`. Read the numeric
ID of the resulting `labeled` record from the GitHub issue events API. Post a
new comment from APMurtha with that event ID and the SHA-256 of the exact
UTF-8 bytes of the body as returned by GitHub, including any whitespace.

```text
samwise-approve-v2: <ready-event-id> <64-character-digest>
```

The worker verifies the authenticated GitHub account and repository IDs,
issue author, latest ready-label actor, and approval-comment author. It rejects
edited or duplicate matching approvals and rechecks the same authorization
after claiming and immediately before execution. Remove ready, close the
issue, or delete the approval to cancel queued work. An approval is tied to
one ready event. Reapplying the label requires a new approval comment.
GitHub issue reads and local launch are separate operations. A cancellation
after the last successful check can arrive too late to stop the claimed job.

### Offline runtime and Bag-End acceptance

Follow [ACCEPTANCE.md](ACCEPTANCE.md) to stage the pinned Linux amd64 inputs,
build the image offline, run the isolation and inference probe, and test a
pair of fresh GitHub issues through an isolated acceptance instance.

Podman receives a bounded archive of the pinned Git tree over stdin. It uses
a private network namespace, a read-only image and a bounded temporary
filesystem. The job has no host checkout mounts, default secret mounts, OCI
hooks, or inherited worker credentials. The temporary checkout contains
regular files and directories. Paths that escape the checkout, links, and
special files cause refusal. Codex sees only aggregate category counts, uses
local inference over loopback, and returns a single category. Repository
instructions, file contents, model-generated commands, and arbitrary edits
are outside this task. The host validates the bounded result and creates only
`samwise-results/issue-N.json` on `samwise/results/issue-N`. It opens a draft PR
against `main` and links it from the issue. Review and merge are manual.
Resource limits include a 32 MiB archive, 10,000 files, 3.5 GiB memory with no swap, four CPUs,
128 processes, and a 175-second container deadline.

### Recovery and rollback

Keep the private state directory and SQLite database intact. The database
records the claim, digest, pinned source, approval identifiers, image ID and
terminal result. A restarted v2 worker treats a claimed job as interrupted,
retries terminal GitHub publication from its receipt, and never reruns that
issue. A deterministic result branch, exact commit, PR lookup, and receipt
comment let publication resume after a lost API response. A mismatched
result branch or PR stops publication for manual reconciliation. Preserve
the receipt and investigate the branch/PR before polling again.

Before rolling back to the fixture-only entry point, stop polling, let active
work finish, and confirm every v2 receipt is terminal and published. Preserve
the shared database and lock path so a past issue cannot become eligible again.
Rollback changes only the worker entry point after approval.

## Repository development v3

The opt-in development companion supports the reviewed addition of a small
Python helper. See [the task envelope, connector approval flow, execution
policy, and staging procedure](DEVELOPMENT.md).
