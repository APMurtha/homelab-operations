# Permanent DW English candidate — NOT INSTALLED

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

## Future installation plan — requires separate authorization

1. Clear playback/recording activity and conflicting administrative work. Record
   current container/image/configuration, network, API/data and Live TV identities
   and matched rollback inputs. Revalidate the existing recovery reference in the
   authorized window; this candidate does not create or restore backups.
2. Verify all source hashes against this commit and the manifest. Verify the exact
   patched image is retained locally. Stop if an accepted base pin has drifted;
   do not regenerate a manifest to bless an unexplained change.
3. Install the candidate directory under
   `/docker/dispatcharr-iptv/permanent-streaming`, root:root, directories 0755 and
   files 0644. Leave original base Compose, Caddyfile, guard, minimal verifier,
   base unit and admission files untouched. The guard unit still verifies those
   original inputs before Docker; the new stack verifier additionally validates
   this candidate, its installed drop-in and the four-service contract.
4. Privately create `private/permanent-relay.json` and
   `private/permanent-registration.json` per the schemas: UID/GID 1000, mode 0400,
   beneath the existing root-private directory. Use the retained privately
   selected manifest, current guard digest, and current accepted-AIO credentials.
   Do not copy trial credentials or put source/credentials in command arguments.
   The registration ACL digest is SHA-256 of canonical sorted compact JSON for
   the reviewed `network_access.value`. STREAMS must be exactly loopback,
   Rivendell, bridge-gateway and observed Jellyfin peer /32s; M3U_EPG/XC_API remain
   loopback-only. If the current ACL does not satisfy this, obtain approval for
   that scoped application change; the registrar will not silently widen it.
5. Prepare only the new runtime/export directories (no recursive permission
   changes): `/run/dispatcharr-permanent/relay` mode 0700 UID/GID 1000, under a
   root-private parent, and `/docker/jellyfin/config/iptv/permanent-dw` mode 0750
   UID/GID 1000. Verify the existing Jellyfin bind can read those files. A different
   actual UID/GID is a reviewed compatibility change, not a reason to chmod broadly.
6. In the authorized window stop the existing protected systemd unit. Preserve the
   exact VPN owner. Using the candidate Compose project/file, stage **only** AIO,
   relay and gateway stopped with `up --no-start --no-deps --no-build --pull never
   --force-recreate dispatcharr relay gateway`. Verify CLI flags and all stopped
   identities before proceeding. Never use a direct start to bypass admission.
   The mount verifier validates the exact `/tmp` options through
   `HostConfig.Tmpfs`, separately from the six relay bind mounts. A newly created
   stopped relay omits `/tmp` from `Mounts`; a running relay must enumerate its
   safe tmpfs there. A stopped relay may retain that entry after a prior run.
   Duplicate, extra, missing or unsafe mount targets are refused in either state.

   For each deployment diagnostic snapshot comparison use
   `python3 -B diagnostic_inventory.py BEFORE.json AFTER.json` with the private
   baseline schema (`containers` records: `name`, `id`, `image`, `started`,
   `running`, `health`, `restart`, `restart_count`, `host_config_sha256`;
   top-level `network_ids`, `docker_process`, `dedicated_network`). Capture fresh
   snapshots read-only as in the prior deployment. This helper only reads JSON;
   it never contacts Docker or services, and prints no record values. It excludes
   exactly the four names in `contracts.NAMES`, including `rivendell-iptv-relay`,
   and strictly compares all listed fields of every genuinely unrelated service,
   plus Docker and network identities. Do not reuse the historical three-name
   diagnostic exclusion list or change the installed three-service verifier.
7. Install only `30-permanent-streaming.conf` into the existing stack unit's drop-in
   directory, after the unchanged `20-resource-admission.conf`; daemon-reload,
   inspect the effective order, and issue the separately authorized managed start.
   Original Type=oneshot, restart=no, 540/240-second unit timeouts and admission
   thresholds remain inherited. Failure invokes four-service scoped cleanup.
8. After backend/VPN/relay/gateway/security acceptance, separately authorize the
   Jellyfin helper with a fresh owner session and root-private receipt path. Verify
   channel/guide discovery, native renewal schedule, rollback, and owner playback.
   No playback or Jellyfin write is part of this implementation task.

## Future rollback

Preserve an uncertain journal; never repeatedly start, delete it to proceed, or
import the historical trial DB. Under explicit rollback authorization and no
active playback, restore Jellyfin's captured tuner/provider state with the helper.
While the AIO is still ready, `lifecycle.py rollback-integration` stops only
candidate gateway+relay and runs API-owned-record rollback. It refuses shared or
edited records and retains a private receipt. Stop the protected systemd unit,
remove only the stopped candidate relay, remove only the new 30 drop-in, and
stage AIO/gateway stopped using the original base+minimal Compose files and
original immutable image. Retain the VPN owner, all data, original guard/gates and
unrelated services. Daemon-reload and start through the original resource gate
only under the rollback authorization. Verify the original three-service contract.

Do not run `down -v`, prune images/volumes, flush rules, restore all of Jellyfin,
reset Redis/DB, or relax thresholds. Unexpected schema migration stops image-only
rollback and requires matched recovery authorization. Reinstallation after a
completed rollback requires explicit reconciliation of its private state; the
registrar does not auto-recreate removed integration records.

## Offline validation

Use `sh tests/run-offline.sh` with `CADDY_TEST_BINARY` pointing to the previously
SHA-verified Caddy executable (`a563843e…60cdf`). The runner does not download,
build, pull or start containers. Network fixtures require unprivileged user/network
namespaces; they create only lo and a synthetic public address, with no external
interface/default route. Certificates, HTTP responses, API models, media packets
and credentials are synthetic. The pinned Caddy binary is deliberately excluded
from Git. See `validation-results.json` and the implementation report for results.
