# Native Dispatcharr hardening — final offline integration

Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.
Approved application/policy baseline `0b8ac7d326a89c9607654d426eb0270f65e41136`.
Production remains the separately deployed `227122d` release; this work did not
connect to Rivendell or change its files, containers, services or configuration.

**GO for the next separately authorized isolated image build, subject to fresh
source/base/capacity/isolation preflight. NO-GO for installation, deployment or
provider activation until that build and actual application tests pass.**
No image was built, no new digest exists, and no provider was authorized.

## Final architecture and compatibility

The application remains native Dispatcharr in the existing AirVPN namespace,
behind the existing Caddy gateway. The unprivileged DW English HLS relay, its six
bind mounts, tmpfs, request budget and image pin remain unchanged. No proxy,
daemon, timer, listener, Docker network or published port is added.

The root-private provider policy/credential boundary is preserved. AIO workers
read only the reviewed root-published authorization projection, with boot,
namespace, guard generation, anchor identity and five-minute lease checks.
The original source policy directory is never mounted into AIO. Neither systemd
nor the lifecycle publishes or renews provider authorization automatically.

Original three-service mode remains the base unit plus admission drop-in.
Existing four-service mode remains the base Compose file plus 30 drop-in.
Native mode is explicitly selected with compose.native.yaml and an additional
40-native-hardening.conf. The base Compose YAML is byte-identical to 0b8ac7d.
All modes use the new matched withdrawal/cleanup helpers. Never-initialized
provider state is a no-op for original services; partial/unsafe state refuses.

All **14 application output hashes and four inherited readiness hashes remain
identical to approved 0b8ac7d**. No native API, provider networking, scheduling,
request-budget or DW English application source behavior was changed here.
Changes are host lifecycle integration, source/image contracts, offline build
metadata, test fixture permissions, regression assertions and documentation.

## Lifecycle integration

`provider_control.py` is a root-only one-shot helper: revoke, assert-revoked or
prepare an empty stable anchor. It imports the installed reviewed publisher bundle
with an explicit package name. It creates no policy, credential or authorization.
The publisher supports package import as well as its existing direct CLI.

Managed prestart ordering is:

1. Withdraw provider assertions.
2. Withdraw existing public guard/grant and original private ready marker.
3. Verify matched source/unit/private configuration inputs. Native mode also
   requires an accepted immutable image binding before any Docker operation.
4. Run the unchanged resource-admission helper.
5. Reapply and semantically verify the existing nftables guard policy.
6. Prepare existing relay runtime and, in native mode, the empty public provider
   anchor; verify stopped-container contracts and remember the VPN-owner identity.
7. Start the preserved VPN owner, verify it and publish its trusted namespace grant.
8. Start AIO/relay. Native mode runs UID1000 source/mode verification, then existing
   PostgreSQL, Redis, uWSGI and Celery backend readiness.
9. Register/verify the owned DW English binding and stable exports; start gateway last.

Guard apply/revoke now attempts provider withdrawal **before even guard-directory
and lock validation**, including direct managed invocations. The existing guard
withdrawal body also attempts provider cleanup while continuing all guard-file
withdrawal/fsync actions on failure. No firewall rendering or semantic table
contract changed. Original root AIO/VPN ready-marker consumers remain intact.

The guard-unit drop-in, resource-admission 20 drop-in and permanent 30 drop-in
withdraw provider status before their existing checks. Their cleanup first attempts
provider withdrawal, then guard withdrawal and scoped stop, and verifies both
withdrawals. Every independent cleanup action is attempted after another fails.
The existing timeouts, unit dependencies, cgroup expectations and admission
thresholds are unchanged. No service was installed, reloaded or executed here.

40-native-hardening.conf resets only the required startup/check commands to native
mode, inheriting the established runtime directory and stop cleanup from 30.
Native stop deliberately does not resolve an image binding and uses base Compose
service names: a missing or corrupt future image binding must not prevent scoped
shutdown. Failure is reported with fixed safe messages, without automatic restart.

## Publisher and private-policy changes

The public directory stays root:root 0755, and its files root:root 0644. The
private directory remains root:root 0700 and private files 0600. Initialization
creates a new public anchor only; existing metadata/device/inode must match on
subsequent prepare operations. No populated directory is replaced or unexplained
anchor adopted. The new directory is deliberately not a systemd RuntimeDirectory
that could be removed/recreated across restarts; the trusted helper preserves it
until separately reviewed retirement. Public sources are root-owned 0755 directories
with 0644 files; installation must reject stale/unreviewed bundle contents.

Explicit publication still requires the current trusted guard generation and its
matching verified VPN-owner namespace grant. The existing reader checks actual
worker namespace, current paths, strict ownership/modes/link counts and generation.
Directory-bind revocation works without exposing private policy, credentials,
free-text review notes or raw endpoint paths. Existing TLS, DNS/IP pinning, tun0,
redirect/retry and bounded-fetch controls remain unchanged.

For an explicitly authorized future edit, root stages KEY.staged.json in the
private directory, mode 0600, then uses `replace-policy KEY`. Under the same writer
lock it withdraws authorization before reading/validating old/new policy, preserves
KEY.prior.json privately, writes a pending digest receipt, atomically replaces and
reads back policy, and commits the receipt. Expired policies can be edited without
making them active. The new policy must validate; no publication follows.

A pending KEY.change.json blocks publication. `reconcile-change KEY` accepts only
the recorded old/new canonical digest and marks aborted/committed without publishing.
Unknown content or conflicting receipts remain blocked and retained. This is a
private filesystem transaction, not permission to retry Dispatcharr API mutations.
The existing native API journals/ownership protections remain unchanged. Direct
edits of an existing policy outside the locked protocol are unsupported.

These commands take opaque keys, not credentials or URLs. No real policy file or
provider credential was supplied, installed or modified in this task. Only
isolated synthetic test policies were used.

## Exact image/source and mount contracts

`native-provider-hardening/release-contract.json` contains `aio_image: null`, the
14 approved output hashes and four inherited readiness hashes. Null is not an
image identity. Native verification and startup refuse null, noncanonical IDs,
the old base and the known failed hardened image. The runtime harness also requires
an explicit new ID matching a verified build receipt and refuses the failed/base ID.

The permanent verifier now separates LEGACY_AIO and RELAY_IMAGE. Native mode
resolves only AIO from the external release binding and checks both Config.Image
and Docker's actual immutable Image field. Relay/VPN/gateway expectations remain
fixed. Tests use a clearly synthetic identity only; it never enters the release
contract or an image operation.

The native overlay changes only AIO image and adds three read-only binds:

| Host source | AIO destination |
|---|---|
| /run/dispatcharr-guard-status | /guard-status |
| /run/dispatcharr-provider-status | /run/dispatcharr-provider-status |
| /docker/dispatcharr-iptv/native-provider-hardening | /opt/native-provider-hardening |

The last directory is the sanitized installed source/contract bundle, not private
policy or state. All eight previous AIO binds remain. Native topology requires
exactly those 11 binds, correct writable data/runtime mounts, private propagation,
unchanged namespace/ports, original capabilities and 3 GiB/2 CPU/512 PID limits.
Missing, extra, duplicate, unsafe or writable protected binds refuse. Relay's six
binds and authoritative HostConfig.Tmpfs contract are unchanged.

UID1000 runtime verification checks all 14 code hashes, exact root ownership,
0644 code files, 0755 code directories, and inherited readiness hashes. This check
is prepared, not claimed executed in an image here. Host verifiers pin the new
publisher/control/runtime bundle, release metadata, actual unit drop-ins and
existing original inputs. The retired historical controller remains disabled
under its original pins.

The complete transition manifest now contains **80 installed file mappings**, all
with explicit source, SHA-256, root UID/GID and 0644 mode. It also records directory
requirements and marks 40 deferred until image acceptance. `deployment_ready` is
false. Original manifest source provenance was checked against 0b8ac7d before
updating reviewed changed-file hashes. No nftables table, security.py, WireGuard,
DNS, VPN-owner/gate source, base unit, base Compose or relay implementation pin
was changed to accommodate the integration.

## Offline tests and evidence

**570 PASS: the 537-test baseline plus 33 new regressions. Zero failures/errors/skips.**
Original test cases were retained; ordering/pin assertions were updated to expect
the reviewed provider withdrawal hook and expanded cleanup, not removed. Additional
native and original unit graphs pass native offline `systemd-analyze verify`.

| Suite | Passed |
|---|---:|
| Provider CLI/native/API contract | 139 |
| Hardening fixtures plus 25 new final-integration cases | 91 |
| Existing stack/security/admission/lifecycle/gateway | 210 |
| Historical persistence | 26 |
| Prior guard interface | 14 |
| Guard lifecycle design | 28 |
| Synthetic TLS/DNS/guard transport | 14 |
| UID1000 permissions/policy tests (32 retained + 8 new) | 40 |
| Image/context/packaging tests | 8 |

New coverage includes effective prestart/cleanup ordering, provider withdrawal
before corrupt guard-lock/directory validation, actual guard/provider revocation
bridge, publisher failure compensation, empty/stable anchors, original three/four
service compatibility, image/source separation, null/failed-ID refusal, exact AIO
mounts and privileges/resources, unchanged relay authority, rollback-before-deletion
gates, controlled policy edits, preserved private prior values, pending/conflicting
receipt handling, UID1000 denial/read access and future build/harness metadata.

Fixtures use private user/mount/network namespaces and temporary tmpfs. Actual
UID/GID1000 access, no effective capabilities, no-follow/read-only bind semantics,
revocation and guard generation changes are exercised. Existing synthetic Caddy
fixtures made 91 isolated requests. No real provider/broadcaster, Docker daemon,
production database or systemd manager was operated. Unit analysis checks syntax
and graph only; real cgroup/process execution is not inferred. The first native
unit-analysis invocation hit sandbox socket restrictions; it passed outside that
sandbox without changing a unit or contacting a service manager.

Sanitized exact suite counts, log hashes and changed-file hashes are in
`native-provider-hardening/final-integration-results.json`. Raw private policy,
credentials, URLs, operation contents and archives are not published.

## Next corrected build and actual application matrix

After separate owner authorization, verify the exact reviewed commit, eight
upstream inputs, patch bytes, all 14 output hashes, inherited readiness overlays,
local base sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21,
fresh disk/memory/CPU capacity and isolated daemon/container boundary. Stop on drift.

The COPY-only build recipe retains private transport, public code 0755/0644 and
root ownership via COPY --chown=0:0. No pull, RUN, package upgrade or production tag
replacement. Future tag is `local/dispatcharr-native-hardening:policy-lifecycle-review-v2`;
Dockerfile revision identifies the unchanged approved application sources at 0b8ac7d.
The enclosing candidate commit identifies the coordinated host changes separately.
The single-shot recipe/receipt and no-blind-retry rules remain. No build ran here.

Use only the new actual image ID in a fresh, separately authorized network-none
runtime environment. The public synthetic fixture's directories are now normalized
to 0755 within a private transport parent; no production credential enters it.
Its later application test bodies remain unvalidated. Required real-runtime work:

1. UID1000 Django initialization and migrations against disposable PostgreSQL,
   authenticated disposable Redis, actual routes/serializers and 14-source readback.
2. Real Celery worker/task registration and execution, default/periodic remote-job
   denial, account-creation side effects and explicit bounded metadata operations.
3. Synthetic-only group/stream resolution, bounded selected channel import, ownership,
   XMLTV parsing/programmes, exact EPG IDs/mappings, interrupted mutations/recovery.
4. Actual public reader/contract endpoint and private-file denial in installed image;
   real guard/policy withdrawal and synthetic namespace failure cases. Label any
   loopback authorization stubs honestly; never fabricate a production AirVPN grant.
5. Existing readiness/backend worker and local/custom DW English semantics;
   no live playback. No production network, database, volume, socket or credentials.
6. Exact temporary resource cleanup and unchanged production identity observations
   through the separately authorized read-only boundary. No real provider contact.

Only after build/application PASS may a reviewed commit bind the actual AIO ID
in release-contract.json and update its affected verifier/manifest hashes together.
No image binaries or fabricated digest belong in Git.

## Installation and scoped rollback plan — not executed

Before any future production stop, obtain separate deployment authorization and
verify working-stack health/idle state, exclusive administration, exact old/new
sources, accepted guard/VPN/network protections, credentials, ownership journals,
all installed mappings and current recovery checkpoints. Reconcile previously
staged files against the complete manifest; reject unreviewed extras/cache files.

During the one approved scoped window: withdraw/verify provider and guard public
readiness through existing anchors; stop only the protected stack using its
accepted unit. Preserve VPN owner/network, data and unrelated services. Install
all matched guard/control/publisher/verifier/unit files as one set, with public
source directories root:root 0755 and files 0644. Preserve private directories.
Initialize/verify the empty provider anchor before stopped native container staging;
never generate real policy or authorization as part of installation.

Stage only reviewed native containers stopped using base Compose plus the native
overlay with its accepted image binding; run stopped contracts. Install 40 only
after image acceptance, verify effective ordering/native syntax, reload systemd
and issue the separately authorized single managed start. Accept backend, source,
namespace, guard/grant, relay, owned registration, exports, gateway and unchanged
unrelated services. Do not publish provider authorization automatically.

On failure, preserve native API journals, guard transactions and private policy
receipts. Attempt all scoped cleanup without bypassing checks. Public assertions
must be absent and protected containers stopped. Known API outcomes and no pending
or uncertain provider work are rollback prerequisites. Pending policy changes
require conflict-checked reconciliation; native API intents require their own
reviewed reconciliation. Never force deletion, clear a latch or purge shared queues.

Restore the complete accepted 0b8ac7d-era host/unit/source set and matching working
image/Compose contracts, not just an image. Remove 40/native overlay selection,
restore reviewed 20/30/guard/cleanup/verifier pins together and verify native sources
and schedules cannot run under an unhardened image. Preserve kernel protection,
VPN owner, persistent data, relay/gateway, Jellyfin and unrelated services. Use only
a separately authorized managed restoration start. If any precondition is unknown,
leave the protected stopped state for review instead of forcing rollback.

## Security limits and decision

The existing five-minute assertion leases, guard generation binding and current
path reader remain. A failed unlink or crashed publisher can leave a valid record
until expiry; old directory binds cannot observe host-path replacement. Root is
trusted; clock integrity and the supported no-replacement protocol remain required.
Revocation is checked at existing bounded I/O points, not atomic with network use.
Neither status records nor offline tests prove continuous VPN/kernel enforcement.
These limitations are unchanged and are not described as instantaneous guarantees.

All offline integration work requested here is implemented and tested. **GO for
one separately authorized corrected isolated build and real application matrix.**
**NO-GO for production installation or real-provider authorization at this point.**
Stop after publication; no build, container action, service reload or live test is
performed automatically.

## Changed files and SHA-256

The exact 80-target mapping is in trusted-guard-tests/transition-manifest.json.
The table below identifies every changed implementation/test/document artifact.
This report is identified by its enclosing Git commit, avoiding a self-hash cycle.

| File | SHA-256 |
|---|---|
| configs/dispatcharr-iptv/boot-admission-phase6b3k/20-resource-admission.conf | e639eab69f150f9f9ab833def8353c38f33bdbf00e3cb23e5ad0dfc595edd964 |
| configs/dispatcharr-iptv/boot-admission-phase6b3k/README.md | ed5063ad6c53479a1e481e0fac9ca649d9d205c8709d2a4de7be4d36fe0af1fc |
| configs/dispatcharr-iptv/boot-admission-phase6b3k/artifact-hashes.json | 7f34075462c2f3a2d49a916431778de19475f65c0115735299fe92ec5dc02111 |
| configs/dispatcharr-iptv/boot-admission-phase6b3k/tests/test_admit.py | 89f2b16eb9f45402e899415db94662435dd0832c3e5659ab95d97ba943e033f6 |
| configs/dispatcharr-iptv/guard.py | 147cb62b0fa19e90d391b5583bde7e342f71bfca748e068f730ba3dd56e91f8a |
| configs/dispatcharr-iptv/hardened-image-integration/Dockerfile | 42dfee8640d31b41bca3db95009f8acd25f97c4909c0f707448c413a00a4dc25 |
| configs/dispatcharr-iptv/hardened-image-integration/README.md | 0025ed1468fcab8cbb65114b87755f471d99b035ac7bd352ddaa4408707c5549 |
| configs/dispatcharr-iptv/hardened-image-integration/build_once.py | 009c0a70be6b41aadcb726de821feba8ec825d0b1be3c76fb266aee772c5d7d6 |
| configs/dispatcharr-iptv/hardened-image-integration/run_runtime.py | 1cafc87802fc6558d105e9860809a42e24be20cc933a928079efd7fe07e95c64 |
| configs/dispatcharr-iptv/minimal-phase6b3d/README.md | 04e556e2e9d8a72a595ac9d259dc7f30890535dd275f703cb76cc65ed1b9fe9c |
| configs/dispatcharr-iptv/minimal-phase6b3d/artifact-hashes.json | 7a0952ae77f122a9b5b6d0993a1458c55581cb2e34c47cd82b60b1c1292e0857 |
| configs/dispatcharr-iptv/minimal-phase6b3d/cleanup.py | 0007aafcc865746e2186e3d491a9c913958985453e8ea66f7523e690dc5406f2 |
| configs/dispatcharr-iptv/minimal-phase6b3d/tests/test_minimal.py | 87f11a6e49728302ed2cb12af0a6209ece26764c0b2efc88a26cb853d26673ad |
| configs/dispatcharr-iptv/minimal-phase6b3d/units/dispatcharr-egress-guard.service.d/20-trusted-readiness.conf | 37226a0e1d77a14d2f0c0e16254f0f6699e7e0c543afcebfd24630cde0249a34 |
| configs/dispatcharr-iptv/minimal-phase6b3d/verify.py | 3133c228bcad182454e3fa03e0af9ae26e39dbf23f616cc39c47d8a44e07f89c |
| configs/dispatcharr-iptv/native-provider-hardening/README.md | 3513518b0237df00258c05b8d3762f7231c969a4d8f5f7d7930ad3840f7be74f |
| configs/dispatcharr-iptv/native-provider-hardening/publish_policy.py | 0e0a36dffeed12b092e97025ce0ec857dd1b470009321d677b3fd25796baa4e8 |
| configs/dispatcharr-iptv/native-provider-hardening/release-contract.json | d1c1d2b72b70beecd8a8f67a9c071317fab04bc00133a9b2d0377a9fd07d3eab |
| configs/dispatcharr-iptv/native-provider-hardening/tests/permission_fixture.py | a61b2e6b1a4bbfb5c5c8bb149983dcbc77062c88faa6dab82cea6c2c998c18bc |
| configs/dispatcharr-iptv/native-provider-hardening/tests/test_final_integration.py | c6b1d18ef089b513ab4671aa3a5f1dc2e0609ccf238146229814a1a87a7789ac |
| configs/dispatcharr-iptv/permanent-streaming/30-permanent-streaming.conf | 8889cad7cf511579487a4472aac8deb89e23d9617e5b302b872732b8a7f44e86 |
| configs/dispatcharr-iptv/permanent-streaming/40-native-hardening.conf | c0688992469db9c181faa9be16530db14fe734d5939de3b988c5ab8c90d6dd64 |
| configs/dispatcharr-iptv/permanent-streaming/README.md | fe2744059edfbfa364f1efc837ebef844784e84810f255b213423acb3c6c45ff |
| configs/dispatcharr-iptv/permanent-streaming/base-input-pins.json | cfe0d81ad95dd3daa73b8740a002474c8e8de7d94c2f219c29a1ac1663195ccf |
| configs/dispatcharr-iptv/permanent-streaming/compose.native.yaml | 02666b070ee6ff6ef32471cf8573cb471f0106504ba2e86a094b70143d28677d |
| configs/dispatcharr-iptv/permanent-streaming/contracts.py | 570fea676d9d816667126db90e6dbcff5e5de7e1d08970eecf356d15a67b7cc3 |
| configs/dispatcharr-iptv/permanent-streaming/lifecycle.py | 680a863d45216c272b9a2ac41df0723b0fe780ba19704a1976b6568b8f437649 |
| configs/dispatcharr-iptv/permanent-streaming/manifest.json | 67b6fd25803944c721c6b85f41badb14da79d1f612c6a2d574098ce67ad4a051 |
| configs/dispatcharr-iptv/permanent-streaming/native_contract.py | ce2d906d47285d4d9b09488c3e7e92bcaec5f0f195572a54e081dc7c46e356f9 |
| configs/dispatcharr-iptv/permanent-streaming/tests/verify_units.py | f863b1e09792617e6ae356bead33284d74d0c4abd36fc11c122af4a7737976a5 |
| configs/dispatcharr-iptv/permanent-streaming/verify.py | 6f8e6fa2a3c222a575206b352debaa30ef9ac1b6e8b6fef839c9472c143c27e4 |
| configs/dispatcharr-iptv/provider_control.py | 33fd56fc7a461ad9e416ba10f0bbdea175b2382e461e192bcb213a77e5844d24 |
| configs/dispatcharr-iptv/trusted-guard-tests/test_implementation.py | b65d951b07426ac716cc06dac528a52eaaec6f943109700184d86a46f62caa95 |
| configs/dispatcharr-iptv/trusted-guard-tests/transition-manifest.json | ce54e1d847724b50d469305f700ba66a0c847a5ae41364fbb1492dcc1181ecd3 |
| configs/dispatcharr-iptv/native-provider-hardening/final-integration-results.json | 613191071ae4d06bad1facceb15364d8326ef733c78bad53791524c95f11f7ed |
