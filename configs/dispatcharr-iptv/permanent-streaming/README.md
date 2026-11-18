# Permanent DW English candidate — matched trusted-guard transition, NOT INSTALLED

See [implementation report](../../../docs/dispatcharr-permanent-streaming-implementation.md)
and [artifact review](../../../docs/dispatcharr-permanent-streaming-artifact-review.md).
This directory is reviewable source, not authority to run a lifecycle action.

## Fixed architecture and pins

Jellyfin → existing LAN Caddy → patched Dispatcharr TS proxy/FFmpeg streamcopy →
loopback HLS relay → approved HTTPS broadcaster over the existing dedicated VPN.
AIO and relay use the retained local image
`local/dispatcharr-readiness@sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
It is already present on Rivendell; do not build or pull. VPN and Caddy image pins,
network, published port and nftables semantics are unchanged. `compose.yaml` is a
complete candidate derived from the accepted base plus restart=no, not a file to
merge with the historical trial's alternate ports/entrypoint/data.

`manifest.json` lists every candidate source/test file except itself and the
validation receipt. `base-input-pins.json` refuses drift in the accepted inputs.
`api-source-pins.json` identifies official release source checked against the
running AIO. `reference/trial_hls_relay.py` is the exact retained successful
until-stop relay, kept for semantic/provenance regression only; do not launch it.

## Operational policy

- Maximum 120 fetch attempts per trailing 60 monotonic seconds, including failed
  attempts. No internal retry, waiting queue or lifetime request exhaustion.
  Exceeding the window latches failure, shuts down the relay and requires operator
  recovery. It is not a trigger for an automatic restart loop.
- Four concurrent fetches; eight HTTP connection workers; eight accepted-socket
  backlog entries; 12-second client socket and total upstream fetch deadlines;
  existing 1 MiB manifest / 8 MiB segment caps and destination/DNS/TLS enforcement.
- Relay: UID/GID 1000, no capabilities, read-only root/source/config, 0.5 CPU,
  256 MiB RAM+swap ceiling, 64 PIDs, 16 MiB temporary filesystem. No new network,
  published port or host daemon. Source/fetch helpers are not new images.
- Telemetry: queue 1,024 records, each <=1 KiB; two rotating 8 MiB files. Queue
  loss, I/O failure or invalid export state fails health and stops the relay.
  Resource maps retain 4,096 entries; peer history retains the last 64 addresses.
  Per-fetch guard checks, DNS revalidation/IP pinning and verified TLS remain.

## Restart-safe registration

`lifecycle.py start` runs only under the future systemd drop-in: start/wait for
VPN+AIO+relay, run `backend.py`, register using supported HTTP APIs, correlate the
new relay instance and export generation, then start **gateway only**, with
`--no-deps`. No gateway is brought up before the binding is proven.

The registrar logs into the accepted AIO using fresh private credentials. It
reads profiles/settings/groups, chooses the unique locked active streamcopy
profile, requires an existing `Default Group`, and changes only its own one
stream and channel. Initial collisions refuse adoption. New channel profile
membership is explicitly empty; no default add-to-all-profiles side effect.
The channel stays hidden from generic application output; the explicit sanitized
M3U exposes only channel 9001. No provider account import, database write, profile
edit, CoreSettings write or historical trial ID/token is used.

A mode-0700 `/data/permanent-streaming` holds mode-0600 ownership and write-ahead
intent records. Each mutation is GET-verified. Ordinary confirmed failures roll
back only matching owned fields. A crash before the commit marker leaves a
pending transaction; a crash after the marker can finish the verified commit.
Unknown API outcomes and rollback conflicts **block subsequent startup**. The
release has no server-side idempotency key/CAS for these endpoints: require an
exclusive admin maintenance window; do not claim a client-side read guard is a
server transaction.

After confirming an uncertain request has finished, an explicitly authorized
operator can invoke `register.py --reconcile-pending
--confirm-no-inflight-requests` through the same AIO context/config. It reads the
journal and conditionally reverses matching effects; conflicts refuse. This is
not a startup retry. `--rollback-owned` is a separate destructive, scoped removal
for installation rollback. Its receipt blocks accidental recreation afterward.

### Hidden-channel rollback correction (offline candidate)

Known owned IDs are resolved through authenticated detail GET, including hidden
channels. Channel inventory uses the pinned admin API's
`visibility_filter=all&page=N` to detect hidden shared-stream references and
collisions. Collection omission never establishes deletion. Only a detail GET
404 establishes absence; 401/403, malformed responses and transport/server
failures refuse or remain uncertain. This relies on current verified level-10
credentials and the pinned API source; a restricted user's 404 is insufficient.

Explicit owned rollback compares both records against the full ownership ledger,
then durably records each DELETE intent. Channel deletion must return 204 and be
confirmed absent by detail GET before any stream DELETE. An unresolved DELETE
with a still-present record blocks a repeated DELETE; do not clear its receipt
or retry blindly. A later explicitly authorized invocation may reconcile an
already-absent record through GET and continue with the next owned record.
Pending registration/commit journals, changed fields, hidden sharing or invalid
receipts refuse. The completed receipt is durable before ownership retirement,
and continues to block automatic recreation. This changes candidate source only;
existing retained production records must not be removed without separate approval.

The exact `/tmp` specification remains mandatory in `HostConfig.Tmpfs` in stopped
and running contracts. Docker may omit `/tmp` from `Mounts` in either state;
when present its tmpfs type/access/source/options representation is also checked.
Six exact bind mounts and all namespace/resource restrictions remain mandatory.

## Exports and Jellyfin

`relay_main.py` sees the committed binding and publishes one generation containing
`dispatcharr.m3u` and `guide.xml`. A relative `current` symlink switches the pair
atomically; only two owned generations remain. The UUID is the registrar's actual
current channel UUID. Only the local canonical TS URL appears in M3U.

The existing relay state writer renews XMLTV on every UTC hour while healthy.
One 49-hour availability placeholder is explicitly labeled **not a broadcaster
programme schedule**. There are no invented show listings, remote EPG/logo
requests or extra host timer. Jellyfin's existing native RefreshGuide schedule
must be verified to run within 24 hours; it is not modified by this candidate.

`jellyfin.py` is a separate future authorized action, never a stack startup step.
It appends/idempotently checks only the owned tuner/provider, preserving all
unrelated entries and top-level settings. TunerCount=1, sharing=true, looping=false,
hardware transcoding=false, import-favorites=false. The guide enables only that
tuner. Files are `/config/iptv/permanent-dw/current/dispatcharr.m3u` and `guide.xml`.
The helper uses Jellyfin 12 MediaBrowser authorization, saves private before/after
intent, verifies allowed changes, and triggers the existing RefreshGuide task.
Rollback refuses concurrent unrelated edits. No library, user, playback-default
or DVR API is called. Live normalized responses still require installation
acceptance; a mismatch retains the receipt and fails closed.

## Coordinated installation — separate authorization required

This candidate now requires the matched trusted guard baseline. Follow
[the implementation report](../../../docs/dispatcharr-trusted-guard-implementation.md)
for the complete ordered file/pin transition and rollback. Do not install only
this directory over the accepted production guard or follow the old candidate’s
independent-install instructions.

1. Verify exclusive idle state, original nine hashes, source/image/private-input
   identities, exact ACL/group/profile/Jellyfin peer and existing matched recovery
   references. Compare the retained inactive `776f984` staged tree before editing.
2. Stage the entire reviewed release privately. Stop only the protected stack
   through its currently accepted unit before replacing protected runtime files.
3. Install the matched guard, minimal verifier/cleanup, guard-unit drop-in,
   resource-admission 20 drop-in and complete candidate. Preserve original base
   units, nftables template, policy, WireGuard, DNS, images, Docker and unrelated
   services. Verify every expected SHA; do not regenerate approvals on host.
4. Migrate private relay JSON `ready_file` to `guard_status_dir=/guard-status`;
   remove the obsolete key. Preserve source, ready_hash, 12-second deadlines and
   UID/GID 1000 mode 0400. Registration configuration and secrets do not change.
5. Before Docker creates stopped containers, prepare the new EMPTY public status
   directory root:root 0755 if absent. Refuse symlinks, an unexpected existing
   inode/metadata or any unexplained populated directory; never chmod the private
   guard. This staging directory authorizes nothing; the managed publisher alone
   initializes its anchor and records. Preserve the VPN owner/network; stage only
   AIO/relay/gateway stopped without
   build/pull/dependencies, then verify exact mounts/resources and source pins.
   The relay mounts only `/run/dispatcharr-guard-status` at `/guard-status`, read-only.
6. Install reviewed 30; native unit verification and effective-order/pin checks;
   daemon-reload and separately authorized single managed start. New guard apply
   creates/validates the stable empty status anchor if needed, never adopts a
   populated/unexplained directory. Guard service does not need a separate restart
   solely to create it. Future restarts preserve that inode with the new drop-in.
7. Start order is early withdrawal → inputs → unchanged admission → guard apply
   and semantic verification → stopped-owner capture → VPN-only start/verification
   → namespace grant → AIO+relay → backend/registration/exports → gateway → running
   security acceptance. No standalone publisher mutation or manual container start.
8. Only after backend acceptance may a separate future task modify Jellyfin or
   authorize broadcaster playback; neither is part of this release installation.

Use `diagnostic_inventory.py BEFORE.json AFTER.json` with the existing private
snapshot schema; it excludes exactly four dedicated services and preserves strict
identity/configuration comparisons for every genuinely unrelated container.

## Scoped rollback — restore the complete accepted baseline

Preserve pending API/guard transaction records. Unknown writes or conflicting
owned data block automatic rollback. When safe and separately authorized, use
existing owned-record rollback while the backend is ready, stop only the protected
stack and confirm public withdrawal through the OLD bound anchor. Remove only the
stopped relay; restore original AIO/gateway stopped from original immutable
base+minimal Compose inputs, preserving owner/network/data.

Restore accepted original guard AND verifier AND original 20 pin set, remove only
new 30 and guard-unit drop-ins, and restore original private schema as appropriate.
Native verify and daemon-reload only in that approved window, then one original
managed start through unchanged admission. Recreate legacy readiness only through
successful original guard apply. Never copy a prior marker, clear a latch to retry,
reset Redis/DB, delete volumes, flush firewall rules, restart Docker or modify
unrelated services. Retain failed private metadata for review; inactive new files
are not an authorization to run them.

An interrupted `applying`/`publishing`/`granting` transaction latches blocked=true
on withdrawal and refuses later apply. No automatic latch-reset command is shipped;
reconciliation or complete safe baseline rollback requires explicit review.

## Offline validation

Use `sh tests/run-offline.sh` with `CADDY_TEST_BINARY` pointing to the previously
SHA-verified Caddy executable (`a563843e…60cdf`). The runner also invokes the actual trusted-guard regression suite in isolated mapped UID/mount/network namespaces. It does not download,
build, pull or start containers. Network fixtures require unprivileged user/network
namespaces; they create only lo and a synthetic public address, with no external
interface/default route. Certificates, HTTP responses, API models, media packets
and credentials are synthetic. The pinned Caddy binary is deliberately excluded
from Git. See `validation-results.json` and the implementation report for results.

## Native provider hardening overlay (unbound offline candidate)

See `docs/dispatcharr-native-hardening-final-integration.md` in the repository.
The base four-service Compose file and relay image remain unchanged. Native mode
adds `compose.native.yaml` and `40-native-hardening.conf`; release-contract.json
currently has a null AIO image. Native verification/start refuses that state and
refuses the known failed image. Do not install the 40 drop-in or stage native
containers until a separately authorized image build and real application matrix
succeed and the complete matched pins are reviewed.

All managed modes now withdraw provider status before admission/guard application
and during cleanup, without publishing or renewing approval. Native prepare only
creates or validates an empty stable public anchor. Its root-private source policy
is never mounted into AIO. The three AIO overlay mounts are public guard status,
public provider status and the sanitized read-only source/contract bundle; the
relay's six existing binds and exact tmpfs are unchanged.

Stop and cleanup deliberately use the base service names without resolving a
native image binding, so an incomplete/missing image binding cannot prevent scoped
shutdown. Rollback integration first withdraws/verifies provider status and then
uses the existing conflict-checked owned-record rollback. Unknown API or policy
change outcomes block further mutation. Private-policy changes use root-only
replace-policy/reconcile-change with staged 0600 files and private receipts; no
automatic publication follows a change. Five-minute leases and the documented
asynchronous/check-to-use limitations remain.
