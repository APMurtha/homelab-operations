# Native provider hardening — offline candidate

This bundle is **not installed** and does not enable live provider onboarding.
Production remains release `227122d`; the image base contract remains the verified
patched AIO `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21`.
See [the review report](../../../docs/dispatcharr-native-provider-hardening.md).

`server.patch` modifies eight exact upstream source files and adds five runtime
modules plus an image-local hash manifest. `source-pins.json` identifies the eight
inputs at Dispatcharr `2fa13a6707bdf0dae87e0c494bcd3ca282cdeb3e`.
`audit-source-pins.json` records additional source inspected for side effects.
`output-hashes.json` identifies the resulting 13 Python files. The hash manifest
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
`/guard-status` and a root-private policy directory at `/run/dispatcharr-provider`;
the relay's current mounts and broadcaster allowlist remain unchanged. This task
provides no Compose, systemd or firewall change. Do not add mounts to production
without that coordinated review and deployment authorization.

`policy.example.json` is **invalid and expired**. It contains no provider, secret
or permission grant. A future approved policy must be root-owned 0600 under a
root-owned 0700 directory, bound to the real host boot, VPN namespace, distinct
host namespace, guard policy digest, provider key and exact XMLTV URL digest.
Allowed HTTPS hosts, paths and public A records need explicit approval. Policies
expire within 24 hours, are read-only in the AIO, and cannot be installed by the CLI.
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
