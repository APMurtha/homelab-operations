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
no changes to its installed plugin cache. This release supports only the
synthetic fixture count. Extending the allowlist requires reviewing local
source changes. Production work requires separate explicit authorization.
