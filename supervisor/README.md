# Samwise repository engineering supervisor

The user timer polls GitHub after logout and reboot. An approved issue supplies the goal, pinned base and editable files. Codex produces Python implementation and test changes. The supervisor runs the tests offline, returns the failing file and line to Codex when available, and opens a draft PR on success. A reviewer checks whether the implementation and tests actually satisfy the goal.

## Delegate from chat

1. Using the GitHub connector as APMurtha, read the current commit of `main` in `APMurtha/homelab-operations`. Create an issue with a descriptive title. Its entire body must be a JSON object in this form (substitute the real base and goal).

   ```json
   {
     "version": "engineering-v1",
     "base": "<40-character lowercase main commit>",
     "goal": "Build an offline checker for broken relative Markdown links. Ignore code fences and external links. Cover anchor-only, missing-file and nested-relative links with regression tests.",
     "paths": ["engineering/markdown_links.py", "engineering/test_markdown_links.py"],
     "suite": "python-unittest"
   }
   ```

2. Apply `samwise:engineering-v1-ready`. The supervisor replies with an approval line containing the issue number, label event ID, raw body SHA-256 and base SHA. After checking the goal and scope, Samwise posts that exact line as the owner through the connector. Neither the creation nor the approval step needs a terminal. This approval permits sending the scoped goal and file contents to the configured model.
3. The next poll starts the task. Find its draft PR through the issue cross-reference. Closing the issue, removing the label, or posting `cancel engineering-v1 #N` withdraws authority at the next check. An in-flight isolated call can finish. An edited issue or moved base needs a fresh issue and approval. A completed or escalated issue cannot be replayed by reapplying a label.

The initial scope is standalone standard-library Python tooling under `engineering/`, with 2–12 named regular files and at least one top-level `test_*.py`. Declare every local module the tests require. Up to 32,000 bytes per file are accepted. Proposals must change implementation and tests. Publishing uses Git objects and exact path checks. No repository checkout, issue-supplied command, repository build hook or production endpoint runs on the control host.

## Operation and recovery

The production entry point is `worker.py --state DIRECTORY`. An exclusive local lock spans reconciliation, work and publication. SQLite keeps the accepted authorization, goal, latest candidate, last result, phase, attempt count, commit and PR, with a transaction for each progress receipt. Keep this directory private and retain it across checkout upgrades. A timer tick resumes from the durable phase. At most three inference attempts, twelve control-plane failures and one hour of elapsed time are allowed per claimed task. A crash after starting inference consumes the attempt. A failed offline test permits a fresh proposal. Policy violations escalate immediately. Local receipt inspection reads only fixed event fields:

```sh
sqlite3 -readonly "$HOME/.local/state/samwise-engineering-v1/state.sqlite3" \
  'select issue,datetime(stamp,"unixepoch"),event,attempt from receipts order by rowid;'
```

Each approved proposal runs against the candidate tests and, where present, the original versions of approved existing tests. Each invocation uses a disposable rootless container with a read-only image, bounded tmpfs, one CPU, 768 MiB memory, PID limit and 170-second container lifetime. The host also bounds captured output. The test container has only loopback, the trusted entry point and the approved source snapshot. The separate Codex container gets a Unix socket to a three-request fixed-model Responses relay. The relay rebuilds requests from text, strips tools and remote file references, and attaches the API credential on the host. The CLI receives no host home, GitHub login, SSH agent or model key. Test output and model transcripts stay out of the journal and PR. A candidate can propose ineffective tests, so draft review remains part of acceptance.

The commit checkpoint precedes any ref or PR creation. A lost reply is reconciled against the deterministic branch, exact SHA and draft head/base. Divergent branches and closed or conflicting PRs escalate. The worker never force-pushes or merges. GitHub cannot atomically tie cancellation to an API write: checks immediately precede ref/PR creation. A previously created branch or PR remains available for owner review. A crash before a generated Git object is checkpointed may leave an unreachable object. Subsequent polls clean only this supervisor's labelled containers and private relay sockets.

## Bag-End deployment after review

Use a separate user checkout at `~/.local/share/samwise-engineering-v1/checkout`, detached at the reviewed commit. Install the two unit files from that checkout in the unprivileged account's user unit directory. Leave existing bridge checkouts, credentials, units and state directories alone. Verify the following before activation:

- The service account can run rootless Podman with user namespaces and cgroup v2 limits. Its local store must contain image ID `sha256:9cb180cb36bd45dc786105b834d3cb5f3b1d69a6a63c79ca10fc64f108aa649a`. The runner uses pull-never.
- Pin the native Linux x86-64 Codex executable, version 0.171.0 as staged, at an absolute trusted path. Its SHA-256 is `b76a027d6b210f9a8da7aaf321dd235c700f0ef7a794d4a5314b9af6c134f0f0`. Put `SAMWISE_CODEX_BINARY` and `SAMWISE_CODEX_SHA256` in `~/.config/samwise-engineering-v1/service.env`. An optional `SAMWISE_MODEL` overrides the default `gpt-5.4`.
- Provide a project-scoped OpenAI API key with Responses access for the selected model in `~/.config/samwise-engineering-v1/openai.key` (mode 0600, parent 0700). The unit uses systemd credentials. Bag-End's interactive ChatGPT subscription login does not supply this API credential. Verify project authorization and spending limits privately.
- Verify GitHub CLI identity 57697374, repository 1126036330, main-branch reads, issue/label event and GraphQL access, issue comments, repository contents writes and draft PR writes. Prefer a repository-scoped token. The owner connector must create issues, apply the dedicated ready label and comment as the same owner. Provision the dedicated label once.
- Verify user-manager lingering for unattended operation. Run `systemd-analyze --user verify` on the installed units, reload the user manager, then enable and start **only** `samwise-engineering-v1.timer`. Check timer scheduling and the first service result. For rollback disable and stop that timer, stop its oneshot, and preserve the private SQLite state. Remove only this supervisor's containers if the expiration/cleanup sweep has not finished.

For live acceptance delegate a real bounded repository improvement from chat. Have the reviewer independently rerun tests against the draft head and check the actual goal. Rehearse a controlled failure before publication using a supervisor-only interruption, verify resumption from its receipt and the absence of a duplicate draft. Activation and this live proof require owner review and approval under issue #30.

## Authentication decision for PR #31

On November 23, 2026, Bag-End's pinned Codex CLI 0.171.0 reported a ChatGPT login. A one-shot, ephemeral, read-only invocation used an empty temporary working directory, a minimal environment, ignored user configuration and rules, disabled plugins, and supplied only a fixed benign prompt. The service's default model `gpt-5.4` was rejected for this login. An account-listed model, `gpt-6.2-sol`, returned the exact expected marker through the supported CLI. These probes used the existing login in place. No session credential was inspected, copied or sent to staging.

Two checks determined the transport decision:

- GitHub reports this repository's visibility as `public`. OpenAI's noninteractive guide expressly excludes public and open-source repositories from its ChatGPT-managed CI/CD workflow. Keeping login material on Bag-End addresses credential distribution, but the proposed adapter would still automate tasks from this public repository under that account. [OpenAI noninteractive authentication guidance](https://developers.openai.com/codex/noninteractive)
- A separate credential-free probe pointed the same binary at a loopback Responses recorder that returned HTTP 400 before inference. With approvals set to never, read-only sandboxing, web search disabled and shell, unified exec, apps, plugins, hooks and multi-agent features disabled, the request still contained an `additional_tools` input with `functions.exec` and collaboration definitions. It selected tools automatically and omitted `max_output_tokens`. A benign live challenge did **not** recover a random temporary-file canary. Tool advertisement alone does not prove host file access. It does show that these switches fail to reproduce the existing relay's tool-free request and 16,000-token generation ceiling. Structured final output constrains the answer format. A process timeout limits elapsed time. Neither enforces that upstream token ceiling. OpenAI also documents incomplete hook coverage and fail-open hook errors. [Noninteractive output controls](https://developers.openai.com/codex/noninteractive) · [Hook coverage](https://developers.openai.com/codex/hooks)

The API-key transport remains an explicit deployment choice. To enable a real-model staging test, the owner must provision an OpenAI API project with billing and Responses access for the selected model, create a project-scoped restricted key permitting Responses creation, and place it **on Bag-End only** at the credential path above. Create the private directory with mode 0700 and the file with mode 0600 before entering the key through a private local credential mechanism. Keep the key out of chat, shell arguments, GitHub, and staging. Configure the project's allowed model and rate limits. Project budget alerts are separate from runtime caps. Existing relay logic supplies the key from the host-side systemd credential. A bounded one-shot staging inference through that relay can be authorized and tested independently of production timer activation.

## Reproducing staging

Run `python3 -m unittest discover -s supervisor -v`. For the container tests set `SAMWISE_ISOLATION_TEST=1`, `SAMWISE_CODEX_BINARY` and the reviewed `SAMWISE_CODEX_SHA256` in a credential-free account with the pinned image. The upstream Responses stream and GitHub transport are deterministic doubles. The CLI binary, socket bridge, Linux isolation, offline Python execution, state transitions and publication checks are real.

For an unattended timer rehearsal in a disposable staging user's home, place the staging checkout's supervisor directory under `~/accept/`. Override only the staging service's working directory and ExecStart to run `/usr/bin/python3 %h/accept/supervisor/stage_tick.py`. Install a dummy systemd credential, configure the binary pin and shorten the staging timer to a one-second initial trigger and three seconds between ticks. Start the timer once. Check for two model calls, one failed first test, a lost response after draft creation, and one verified draft. The adapter writes synthetic remote state in `~/accept/timer-state/`. Stop the staging timer after the verdict. This override belongs exclusively to the independent test account.
