# Native provider hardening — offline candidate

This bundle is **not installed** and does not enable live provider onboarding.
Production remains release `227122d`; the image base contract remains the verified
patched AIO `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
Original baseline: [hardening report](../../../docs/dispatcharr-native-provider-hardening.md).
Current offline revision: [policy/packaging fix](../../../docs/dispatcharr-provider-policy-permission-fix.md).

`server.patch` modifies eight exact upstream source files and adds six runtime
modules plus an image-local hash manifest. `source-pins.json` identifies the eight
inputs at Dispatcharr `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`.
`audit-source-pins.json` records additional source inspected for side effects.
`output-hashes.json` identifies the resulting 14 Python files. The hash manifest
excludes itself. Neither script builds, pulls, installs or deploys an image.

Prepare from an existing local checkout of that pinned source, with a **new**
output directory outside production:

```sh
python3 configs/dispatcharr-iptv/native-provider-hardening/prepare.py \
  /PATH/TO/PINNED/SOURCE /PATH/TO/NEW/OFFLINE/OUTPUT
```

All input hashes are checked before output is written. A mismatch stops; do not
update pins to accept unexplained differences. The reviewed patch is also tested
by applying it to a temporary copy and verifying all output hashes. AST edits were
generated using the test host's Python 3.14; use the committed patch/output hashes
as the artifact identity, and stop on generation differences on another runtime.
No source tree or runtime state from Rivendell is needed for these tests.

```sh
DISPATCHARR_PINNED_SOURCE=/PATH/TO/PINNED/SOURCE \
  python3 -B -m unittest discover -s configs/dispatcharr-iptv/native-provider-hardening/tests -v
sh configs/dispatcharr-iptv/native-provider-hardening/tests/run-isolated.sh
sh configs/dispatcharr-iptv/native-provider-hardening/tests/run-permissions.sh
python3 -B -m unittest discover -s tools/tests -v
```

The default retained source fixture path is
`/tmp/dispatcharr-native-hardening-input`; set the environment variable above for
another checkout. The isolated runner requires existing `unshare`, `ip`, `openssl`
and user/network namespace capability. It creates loopback-only TLS/DNS fixtures,
no external route, and no container, VPN, host DNS or firewall changes. TLS tests
stub authorization **only for the synthetic loopback server**; destination-policy
and DNS-rebinding tests independently exercise rejection. The production code has
no loopback-provider bypass. Synthetic certificates/keys are temporary and never
part of this bundle.

Future installation requires a separately reviewed immutable image, complete
protected image/source-contract transition and read-only mounts. The AIO needs
`/guard-status` and root-published authorization at `/run/dispatcharr-provider-status`;
never mount the root-private source policy into the application. Root keeps the
original `/run/dispatcharr-provider` private. Only `publish_policy.py` reads it;
the relay's current mounts and broadcaster allowlist remain unchanged. This task
provides no Compose, systemd or firewall change. Do not add mounts to production
without that coordinated review and deployment authorization.

`policy.example.json` is **invalid and expired**. It contains no provider, secret
or permission grant. A future approved policy must be root-owned 0600 under a
root-owned 0700 directory, bound to the real host boot, VPN namespace, distinct
host namespace, guard policy digest, provider key and exact XMLTV URL digest.
Allowed HTTPS hosts, paths and public A records need explicit approval. Private approvals expire within 24 hours and are never readable by AIO workers.
Explicit trusted publication creates a fresh, at-most-300-second assertion tied
to the existing guard generation. Public records contain no raw endpoint paths,
review text, provider credentials or credential-bearing URLs. Workers read the
public directory through a read-only directory bind and reopen the current file
on each authorization check. No automatic renewal exists; native work fails
closed after expiry. The provider CLI cannot publish assertions.
No trusted status record may be created manually. Policies do not authorize media.

Only HTTPS/443, approved public IPv4 destinations, bounded live XC metadata and
plain UTF-8 XMLTV are supported. HTTP, other ports, redirects, retries, compressed
XMLTV, DTD/entities, oversized/deep documents, VOD/series discovery and artwork
fetching refuse. The application checks current grant/guard state and tun0 routing;
the existing kernel/VPN enforcement remains essential. Readiness is not continuous
kernel or VPN-provider attestation, nor instantaneous cancellation of an in-flight
operation.

The native CLI now verifies the new server contract and explicit guide digest.
Simulations supply a marked mock contract; **live execution and removal remain
unconditionally disabled**. This is ready for source/security review, not a live
provider test. No new streaming destination is granted to the DW English relay or
exported to Jellyfin.

The root-only candidate publisher has explicit `init`, `publish KEY`, `revoke KEY`
and `revoke-all` actions. Keys are opaque hashes, never credentials/URLs.
`init` requires a new public directory and writes its inode identity privately;
existing unexplained anchors are refused. Serialized publication withdraws first,
validates the private policy and trusted grant, atomically writes the minimized
assertion, then rechecks the grant. Revocation unlinks current paths and fsyncs.
A failed withdrawal aborts publication; revoke-all attempts every known record.

No publisher is installed or invoked in production. Protected lifecycle hooks,
exact AIO mount/verifier pins, and explicit approval/publication before manual
native work still require coordinated review. Crash/revocation cleanup is not
instantaneous; leases bound retained records to 300 seconds under a trusted clock.
A stale directory bind cannot observe host-path replacement. Never replace the
public anchor while workers run; revoke via the original anchor, verify expiry
or shutdown, then coordinate retirement. No adoption/replacement command exists.

### Coordinated lifecycle integration

Current candidate integration is documented in
[the final integration report](../../../docs/dispatcharr-native-hardening-final-integration.md).
`release-contract.json` deliberately has `aio_image: null`. Its 14 runtime outputs
are unchanged from approved 0b8ac7d; no image identity is invented. The existing
three/four-service paths stay explicit; native Compose/drop-in selection is gated.

Host `provider_control.py` supplies idempotent revoke/assert/empty-anchor prepare.
The guard withdraw path, admission/drop-ins and scoped cleanup call it. No managed
hook calls publish or renew. Never silently create/adopt a replaced public anchor.

For a separately authorized private-policy edit, stage KEY.staged.json under the
existing root-private directory with exact 0600 permissions. Root-only
`replace-policy KEY` locks, withdraws first, validates identity/schema, retains
KEY.prior.json privately, and records intent before atomic replacement. A pending
KEY.change.json blocks publication. `reconcile-change KEY` accepts only the
recorded old/new digest and never publishes; conflicts remain blocked. These
operations do not change Dispatcharr API records and must not be confused with
native API ownership journals. Direct edits of an existing policy outside this
protocol are unsupported. No real policy is supplied or installed here.
