# Bag-End acceptance

## Build and prove the runtime

Use a non-root Linux amd64 account with local Podman 5.4.2 or newer and a
working cgroup v2 setup with delegated CPU, memory and PID controllers. Build
and smoke-test on a staging host first. Run the same probe on Bag-End as the
account that will run the bridge. The current Bag-End fixture worker can stay
active throughout these steps.

The Containerfile pins the platform manifests for Python 3.12.12 slim
Bookworm and Ollama 0.34.0. The staging script pins the Codex 0.170.0 release
archive and the Qwen3 4B Instruct 2507 Q4_K_M manifest with SHA-256. It verifies
each model blob against that manifest and copies only the named native Codex
binary out of the verified archive. The build uses no package manager or
network and copies only the files in its temporary context. The pins record
which upstream bytes to use. Review the upstream releases and the local
build inputs before trusting the resulting image.

```sh
cd configs/samwise-bridge
umask 077
# Run on a disk-backed volume as the rootless build user.
build_dir=$(mktemp -d /var/tmp/samwise-build.XXXXXXXX)
python3 stage_runtime.py "$build_dir/context"

# Connected staging only. Pull the exact OCI manifests from the Containerfile.
awk '/^FROM / { print $2 }' Containerfile | while IFS= read -r ref; do
  podman pull --platform=linux/amd64 "$ref" || exit 1
done

# Offline build. Keep the context and staged base images for reproduction.
podman build --platform=linux/amd64 --network=none --pull=never --no-cache \
  --timestamp 0 -t localhost/samwise-offline:reviewed \
  -f "$build_dir/context/Containerfile" "$build_dir/context"
image=$(podman image inspect --format '{{.Id}}' localhost/samwise-offline:reviewed)
python3 smoke_runtime.py "$image"
```

Record the image ID, Podman version, kernel, peak memory, cold inference time
and probe output. The probe uses the same flags as the worker and checks the
actual namespaces, mount table, absence of synthetic credentials, outbound
network denial, loopback access, UID, capabilities and cgroup limits. It checks
automatic removal after a successful run and a killed job, then processes a
one-file synthetic archive with real Ollama and Codex. Stop if any check fails.
The local process tests can also be run with
`python3 -m unittest discover -s . -v`.

If staging and Bag-End use different image stores, export with
`podman save --format oci-archive -o samwise-offline.tar "$image"`, record
`sha256sum samwise-offline.tar`, transfer the archive and verify its checksum
on Bag-End, then `podman load -i samwise-offline.tar`. Pass the recorded full
image ID to the Bag-End probe. A tag alone is insufficient.

### Bag-End resource gate

On 2026-11-19 Bag-End reported 7.18 GiB total RAM, about 4.60–4.63 GiB
available and 4.00 GiB swap. The user slice exposed CPU, memory and PID
controllers. The existing fixture unit reported `Delegate=no`. These
observations do not establish enforcement inside a rootless container. Podman
was absent from the host, so actual inference peak and latency are pending.
The verified model weights are 2.50 GB on disk. A single 4,096-token context
under the 3.5 GiB no-swap ceiling is plausible, with little host headroom.

Before each cold run, check `awk '/MemAvailable/ {print $2}' /proc/meminfo`.
Require at least 4,718,592 KiB available (4.5 GiB) to leave 1 GiB above the
job limit. Use the probe's actual cgroup peak and timings to judge fit. Both
cold runs must complete with no cgroup OOM, peak below 3.5 GiB and elapsed
time below 145 seconds. If either host cannot meet those gates, stop before
creating an issue and rerun after addressing the resource shortfall. The
existing unit's systemd configuration stays untouched during acceptance.

## Run controlled GitHub acceptance

After separate approval for live GitHub writes, run from a trusted checkout
at the reviewed PR head as the same owner account. Verify
`gh api user --jq .id` returns `57697374` and
`gh api repos/APMurtha/homelab-operations --jq .id` returns `1126036330`.
Fetch the current main tip into this checkout with
`git fetch origin refs/heads/main` and save `commit=$(git rev-parse FETCH_HEAD)`.
Confirm the fixture worker reports active with
`systemctl --user is-active samwise-codex.service`. The v2 acceptance instance
uses a new private lock and database and processes only the designated issue in
either mode. Its issues use v2 syntax, which the live fixture worker rejects.

```sh
cd "$(git rev-parse --show-toplevel)"
repo=APMurtha/homelab-operations
umask 077
acceptance_state=$(mktemp -d /var/tmp/samwise-acceptance.XXXXXXXX)
export SAMWISE_RUNNER_IMAGE="$image"
export SAMWISE_ACCEPTANCE_STATE="$acceptance_state"
printf 'Acceptance receipts: %s\n' "$acceptance_state"

new_inventory_issue() {
  issue_url=$(gh issue create -R "$repo" --title "Samwise v2 acceptance ($1)" \
    --body "samwise-task-v2: {\"kind\":\"repo-inventory\",\"revision\":1,\"commit\":\"$commit\"}") || return
  issue=${issue_url##*/}
  gh issue edit "$issue" -R "$repo" --add-label samwise:ready >/dev/null || return
  event=$(gh api --paginate "repos/$repo/issues/$issue/events?per_page=100" \
    --jq '.[] | select(.event == "labeled" and .label.name == "samwise:ready" and .actor.id == 57697374) | .id' |
    tail -n 1)
  [ -n "$event" ] || return 1
  digest=$(gh api "repos/$repo/issues/$issue" |
    python3 -c 'import hashlib,json,sys; print(hashlib.sha256(json.load(sys.stdin)["body"].encode()).hexdigest())')
  [ -n "$digest" ] || return 1
  gh issue comment "$issue" -R "$repo" --body "samwise-approve-v2: $event $digest"
}

accept_one() {
  PYTHONPATH=configs/samwise-bridge python3 - "$issue" "$1" <<'PYTHON'
import os
from pathlib import Path
import sys
import worker
import worker_v2

issue, mode = int(sys.argv[1]), sys.argv[2]
worker.STATE = Path(os.environ["SAMWISE_ACCEPTANCE_STATE"])
sys.argv = ["samwise-acceptance", "--once", "--issue", str(issue)] if mode == "once" else [
    "samwise-acceptance", "--poll"
]
def accept_cycle(db, _):
    if mode == "poll":
        candidates = worker.gh(f"{worker.REPO}/issues?state=open&labels={worker.READY}&per_page=100")
        if not any(candidate["number"] == issue for candidate in candidates):
            return False
    return worker_v2.cycle(db, issue, image=os.environ["SAMWISE_RUNNER_IMAGE"])

raise SystemExit(worker.main(accept_cycle))
PYTHON
}

new_inventory_issue once && accept_one once
# Inspect this issue and draft before creating the next issue.
new_inventory_issue poll && accept_one poll
# After the terminal label and result PR appear, stop foreground polling with Ctrl+C.
```

For each issue, require `samwise:done`, absence of `samwise:ready` and
`samwise:running`, a single receipt comment, and one draft PR to `main`
with a single changed file at `samwise-results/issue-N.json`. Compare the
report issue number, source commit, digest, approval and runner image to
the recorded inputs. Ask Samwise to read back the issue result and PR.
Confirm the initial fixture service PID and active state again. Repeat
`accept_one once` for the completed polling issue and require exit status 1,
with no new comment or draft PR. For a retry after failure, create a fresh
issue and keep the old receipt.

## Roll back or promote after acceptance

Stop the foreground acceptance instance after it reaches a terminal result.
For a failed or abandoned run, remove `samwise:ready` from the specific test
issue and close it. Wait up to the 175-second container deadline, then check
rootless Podman for any named acceptance container still present. If needed,
run `podman rm --force --ignore EXACT_CONTAINER_NAME` for that container.
Close only the corresponding draft result PR and delete only its
`samwise/results/issue-N` branch if cleanup is approved. Preserve the
acceptance database for reconciliation. The fixture unit needs no restart.

A later separately approved service switch should use the reviewed checkout,
the verified image ID, and a dedicated systemd drop-in. Wait until the fixture
worker is idle and all receipts are published, then stop the fixture unit and
take a SQLite backup with Python's `sqlite3.Connection.backup` while it is
stopped. Keep the private live state directory, lock and database in place.
Use a drop-in with `ExecStart=` followed by the absolute Python and
`worker_v2.py --poll` command, `Environment=SAMWISE_RUNNER_IMAGE=sha256:…`,
and `Delegate=yes`. Reload the user manager, start the unit and verify its
effective ExecStart, image and state.

To revert a switched unit, wait for v2 to become idle and verify all v2
receipts are terminal and published. Stop the unit, remove only the v2 drop-in,
run `systemctl --user daemon-reload` and
`systemctl --user start samwise-codex.service`. Verify the original
`worker.py --poll` command and an active unit. Keep the current live database
so its replay protection includes work already accepted. The backup is for
database recovery and requires reconciliation against GitHub before use.
