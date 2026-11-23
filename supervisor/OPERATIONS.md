# Read-only Dispatcharr observations (operations-v1)

## Authority and data flow

The existing supervisor retains its timer, process lock and engineering workflow. Operations polling is off by default. A future reviewed opt-in adds a second label and separate SQLite directory under the same lock. The operations path never invokes Codex, the engineering runner, or a repository command. GitHub issue comments carry the sanitized report; no repository contents permission is needed for this task type.

An operations issue specifies the version, immutable main commit, fixed target, OpenSSH SHA256 host-key fingerprint, ordered observation IDs, total reply-byte and wall-clock budgets, and UTC expiry (Unix seconds, at most one hour ahead). No free-form goal, host, URL, arguments, command or filename is accepted. The owner applies the operations label and replies to the challenge from the same GitHub identity. The challenge binds the raw body digest, ready event and base. The worker verifies the repository and owner numeric IDs, event actor, unedited issue and approval, label, cancellation, base, expiry and installed host pin before collection and again before publication. Removing the label, closing the issue or commenting `cancel operations-v1 #N` revokes remaining work. A read in flight may finish within its deadline. A withdrawn, expired or superseded grant cannot authorize a subsequent publication.

Bag-End connects only to the fixed private target and account, with no agent, forwarding, multiplexing, interactive authentication or user SSH config. A dedicated key and a single exact Ed25519 host-key entry are mandatory. A separate live grant must provision these; never borrow an existing SSH login. The collector checks the exact forced-command protocol tag, accepts bounded JSON on stdin, and reads only named files beneath a trusted local directory. On both sides, exact schemas and closed result vocabularies exclude strings sourced from logs, channel titles, program details, tokens and provider URLs. The host timestamp in the public report is the collector request completion time on Bag-End. Snapshot evidence describes the most recent locally available evidence within the freshness window.

## Remote permission boundary

Use a dedicated unprivileged account and key restricted to the orchestration source address. Enforce a root-owned sshd Match block with ForceCommand pointing to a root-owned launcher for the isolated Python collector; also disable forwarding, PTY, user rc/environment and password/interactive authentication. Disable all other keys and shell/subsystem paths for that account. Use `restrict,from="..."` on the sole authorized key. Install only the collector and its protocol module in an administrator-owned directory. The launcher executes `python3 -I` and adds only that trusted module directory to sys.path. Give the account no privileged groups, sudo, Docker socket, journals, provider config, home-service credentials or outbound network access. Administrative SSH authentication/forced-command audit records and supervisor receipts are sufficient; never log stdin or evidence contents.

Provision a root-owned, non-group/world-writable /run/samwise-observations directory under trusted parents. Its fixed filenames are read-only regular files owned by root and non-writable by the observation account. Use narrowly projected evidence from existing local monitoring. File creation/refresh belongs to its existing authorized custodian, never the collector. Missing, old or invalid evidence returns an explicit unavailable state. Inventory exports must describe DW English 9001 specifically. No service polling, control commands, playback, stream access or privilege escalation is used to fill gaps.

## Observation inputs and interpretation

Each filename is the observation ID. Inputs larger than 64 KiB, special files and symlinks are refused. Files older than 300 seconds or dated in the future yield `stale`. Refresh projections atomically from fresh source evidence; never touch an old receipt to make it appear current.

| IDs | Local input | Published result |
| --- | --- | --- |
| backend, gateway, relay, vpn-container, jellyfin | Fixed container's health/status projection | running, stopped or unhealthy |
| guard, vpn | Local verifier's protection or tunnel assertion | verified, withdrawn or failed |
| celery | Projection of the latest structured readiness record: boolean output_complete, reply_output_valid, default_present, dvr_present | both-ready only if all four are true; otherwise readiness-failed |
| logs | Bounded sample of Dispatcharr severity labels, one per line | warning-or-error or no-warning-in-sample |
| playlist | Local M3U metadata, including EXTINF lines; omit URL lines when exporting | present or absent for dw-english-permanent |
| jellyfin-channel | Complete inventory projection with TotalRecordCount and Items containing only Number and Name | DW English number 9001 present or absent |
| jellyfin-guide | TotalRecordCount from a current-time program query scoped to that same channel | current or empty |

Absence of a fresh valid source is a reportable observation, never a positive readiness assertion. Logs describe only the sampled interval. Celery describes a past validated probe; no live ping is sent. Guide and inventory describe a previously captured query. No viewer/session/recording data belongs in these projections.

## Approval and separate live gate

After separate deployment approval, provision a root-owned single-entry Ed25519 file at `/etc/samwise/operations-v1/known_hosts` for 10.10.20.30 with a fingerprint verified out of band. Provision only the new dedicated identity as a second systemd credential named `ops-ssh.key`. Enabling this capability requires explicit `SAMWISE_OPERATIONS_V1=enabled` and the label `samwise:operations-v1-ready`. This PR installs none of them. Keep the operations label off engineering issues. The existing unit needs no change for offline development. Verify the restricted account's effective sshd policy and individual file ACLs before any live exercise; a successful staging run does not authorize one.

Example issue body (substitute current main, verified fingerprint and an integer future UTC expiry):

```json
{"version":"operations-v1","target":"rivendell-dispatcharr","host_key":"SHA256:<verified>","base":"<40 hex>","observations":["backend","celery","guard"],"seconds":10,"bytes":512,"attempts":1,"expires":0}
```

The version fixes the only permitted SSH command to `samwise-observe-v1`. Limits are 1–20 seconds, 256–4096 reply bytes per attempt, 1–2 attempts and a one-hour absolute grant lifetime. A crash consumes the current attempt. SQLite checkpoints each claim, read attempt, validated result and report intent. If a comment POST outcome is uncertain, subsequent polls search for the exact unedited owner-authored report and never issue a second POST. Six dependency failures, an exhausted read budget or expiry escalate. An unconfirmed report intent can require owner reconciliation. Removing enrollment or disabling operations stops future access; retain the private state directory. As with engineering publication, GitHub cannot atomically bind label withdrawal to a concurrent API write.

Final acceptance requires a new owner-authored issue and exact approval after the live gate, then verification of the comment and its private receipt. No SSH login or production acceptance is part of this development PR.

The exact ForceCommand can be `/usr/bin/python3 -IB /opt/samwise-observe/ops_collector.py` with `ops_protocol.py` alongside it. The client always transmits the fixed protocol tag rather than this executable path. Pin each file by digest at deployment review. For regression testing use `python3 -m unittest discover -s supervisor -v`. Setting `SAMWISE_TEST_SSH=1` under a disposable unprivileged staging account additionally exercises the installed OpenSSH client and a one-connection sshd on loopback, using ephemeral keys/config. It checks mismatched server and client identities and rejected requests without touching any installed service or production host.

Candidate sshd policy for future owner review (no installation in gate 1):

```text
Match User samwise-observe
    AuthenticationMethods publickey
    AuthorizedKeysFile /etc/ssh/samwise-observe.authorized_keys
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    DisableForwarding yes
    PermitTunnel no
    PermitTTY no
    PermitUserRC no
    ForceCommand /usr/bin/python3 -IB /opt/samwise-observe/ops_collector.py
```

Verify the server-wide `PermitUserEnvironment no` setting separately (it is not a Match directive). Keep the account home, launcher, module directory and sole authorized-key file under administrative control. Before activation inspect the **effective** sshd policy for this user/source, including trusted CAs/other authorized-key providers; the dedicated key must be its only effective principal. Verify outbound denial and absence of privileged group/socket access locally under a separate grant. Do not change firewall/guard policy to make these checks pass.
