# Samwise development tasks (v3)

The opt-in v3 companion opens a draft against `main` in
`APMurtha/homelab-operations`. Its first template adds `samwise_even.py`,
a standalone Python module with a typed `is_even` function. Each new
template needs source review for its path, input grammar, implementation
choices, and test. The v3 entry point uses its own private lock and SQLite
ledger in `~/.local/state/samwise-development-v3`. V2 continues to handle
inventory and fixtures using its existing service and state.

## Submit and approve

1. As the owner, select the current full commit SHA of this repository's
   `main`. Samwise can create an issue through the GitHub connector with this
   body, substituting the SHA. Use a fresh issue for corrections or retries.

   ```text
   samwise-task-v3: {"revision":1,"template":"add-parity-helper","commit":"<40-character SHA>","paths":["samwise_even.py"]}
   ```

2. Apply `samwise:ready` through the owner's connection. The worker checks
   the repository ID, authenticated account, issue author, and latest ready
   event actor. When polling, it posts a review comment with the proposed
   path, base, and an exact `samwise-approve-v3` line. The connector exposes
   issue creation, labeling, comment reads, and new comments. The worker
   retrieves the numeric event ID from GitHub REST.
3. After the owner approves this specific change, use the connector to post
   that line verbatim as a **new** owner comment. It binds the exact UTF-8
   issue body and the ready event. The worker's review comment alone cannot
   authorize execution. Both issue actions and approval must resolve to
   owner ID 57697374. The repository ID must be 1126036330.
4. To withdraw approval, close the issue, remove ready, or delete the
   approval before publication is committed to the local ledger. Reapplying
   ready requires a fresh approval. V3 rejects edited issues and edited
   approvals, including edit-and-restore, using GitHub GraphQL edit metadata.
   An issue edited before approval also requires a fresh submission.
5. Read the terminal issue comment and the linked draft. Its sole diff
   adds the allowlisted module. The PR body identifies the base, template,
   issue digest, ready event, approval comment, image, runner program digest,
   test identifier and proposed file digest.

## Execution and recovery

The host verifies that the pinned base equals GitHub's main tip and checks
the target's absence with `git ls-tree` against local Git objects. An
existing regular file, symlink, tree or submodule at the target blocks the
job. For this addition, the disposable checkout starts empty because the
allowlist contains only the absent target. No source blobs, issue strings,
Git configuration or repository test commands enter the container.

The host streams the reviewed `development_job.py` into Python in the pinned
v2 image. The job uses local Codex and Ollama with a fixed prompt and JSON
schema. Two reviewed integer expressions form the output grammar. The job
writes the validated function and tests the staged file with eight inputs
in a separate isolated Python process with a three-second deadline. The
host independently checks the complete output module and test identifier.
The existing Podman policy supplies a private network namespace, read-only
root, bounded tmpfs, CPU/memory/PID limits, and a 175-second lifetime.
The host caps output at 1 KiB.

V3 records a durable claim before inference and checks authorization after
claiming, before execution, and after the job. The final check precedes the
local transaction that authorizes publication. GitHub changes after that
check can arrive too late. Recovery completes an already committed
publication from SQLite. It marks an interrupted claim terminal and never
reruns its code. Keep the v3 state for replay protection. Draft reconciliation
requires the expected open draft, branch, commit, repository, and base.
If the branch or PR has changed unexpectedly, inspect its receipt before
retrying publication. A later rollback of the companion consists of stopping
its poller while preserving its ledger. V2 has an independent entry point
and rollback procedure in ACCEPTANCE.md.

## Staging and acceptance

Run from this directory on an independent, non-production Linux amd64 host
with the reviewed v2 image and rootless Podman resource gates in ACCEPTANCE.md.

```sh
python3 -m unittest discover -v
python3 -c 'import development; print(development.develop(development.IMAGE))'
```

The first command simulates GitHub and exercises authorization, publication,
recovery, replay, and rejection paths. The second launches the real offline
model and bounded test without GitHub writes. Confirm the output matches
one of the two accepted sources and Podman records container removal.

After independent staging, source review, and separate live authorization,
use the reviewed v3 checkout for a fresh connector-submitted issue. The
Bag-End entry point supports `python3 worker_v3.py --once --issue N` and
`python3 worker_v3.py --poll`. For unattended acceptance, verify owner
label and approval IDs, one execution and receipt, the one-file draft diff,
provenance, and Samwise's independent readback. Repeat one-shot for the
completed issue and verify exit 1 with no new job, PR or receipt. Preserve
the running v2 service and its existing lock, ledger and rollback artifacts.

### Independent staging results, 2026-11-23 UTC

Staging passed at reviewed commit `506ff9c1b41fdcbde71b536bb38a1269c228ceb7`.
The transferred Git archive of `configs/samwise-bridge` matched its local
SHA-256, `0c2859f35fc0ddd7088741e4130dc778552821b13c505939ecfd9da135aec206`.
The staging host ran Ubuntu 26.04 amd64, kernel 7.0.0-43-generic, Python
3.14.4, and rootless Podman 5.7.0 with systemd cgroup v2. Its local image ID
matched `sha256:db79c76fc71f354b20aa165d852eb70b9a0a6fbea568f2fa91f760a7b1302053`.
All 46 unit and security tests passed.

| Run | Available memory before run (KiB) | Elapsed (s) | Observed cgroup memory.peak (bytes) | OOM events |
| --- | ---: | ---: | ---: | ---: |
| Runtime probe, inventory inference | 6,919,404 | 69.7 | 3,523,829,760 | 0 |
| Development job 1 | 6,909,236 | 72.52 | 3,430,391,808 | 0 |
| Development job 2 | 6,927,964 | 72.75 | 3,344,805,888 | 0 |

Each development run started a fresh container and model process. Elapsed
time covers the host invocation through cleanup. A host observer sampled the
kernel peak counter and OOM events every 50 ms while the cgroup existed.
Both runs returned identical 59-byte modules using `return value % 2 == 0`.
Each passed the in-container test. A second isolated Python process checked
the returned file against explicit expected booleans for −3, −2, −1, 0, 1, 2,
3 and 2⁶⁴ after its bytes matched an approved implementation. File SHA-256
was `a7877448c9dd132e46ca2af9ed528d88d78c0806b5a327ecaf3adce807de95d7`.

The runtime probe confirmed working loopback, outbound network denial, private
namespaces, read-only root, bounded scratch space, and credential isolation.
Both development containers used network mode `none`, a four-CPU quota, a
128-PID limit, a 3,584 MiB memory limit, a 3,360 MiB reclaim threshold and
zero swap. Podman recorded removal of both development containers and all
three probe containers, including the deliberately timed-out probe. The final
container list was empty.

Staging retains the source archive, test log, probe log, measurement script,
per-run results and returned modules in `/var/tmp/samwise-v3-stage.NFSpkjAM`.
Independent staging passed without implementation fixes. The next gate is
separately authorized live GitHub acceptance and Samwise readback.
