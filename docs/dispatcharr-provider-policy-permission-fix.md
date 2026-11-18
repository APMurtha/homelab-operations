# Offline provider-policy interface and packaging fix

Repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.
Baseline hardening `1124d9699097faa5a2b865ad8989da9f5743cfbf`;
failure evidence `d9fcad23e65b21fa3d0b548c78216a1cfd13d093`.

**Offline implementation PASS: 537 tests passed. Ready for source/security review.
No image was built or deployed.** The retained failed image
`sha256:26c93e71dd431127ef72c651bfe0ad3f7431cef7c135749002833f1fc1524c78`
is unchanged and remains NO-GO. This report supersedes the future-source blockers,
not that image's failed runtime evidence.

## Packaging correction

The build wrapper's umask 077 leaked into newly created code directories; Docker
COPY --chown=0:0 preserved their 0700 modes. The existing write_context correction
was reviewed and retained: transport context root 0700, application directories
0755, public code files 0644. Dockerfile still specifies COPY --chown=0:0.
The same mode normalization now applies to prepare_context.py, so either supported
preparation path works under private umask. An explicit public-source path
allowlist prevents accidentally including policies, keys or credential files.
The historical build_once.executed.py and failed-build receipt are unchanged.

Permission-faithful tests stage the overlay as mapped root on isolated tmpfs,
verify root:root ownership and every file/directory mode, then drop supplementary
groups/capabilities and run as actual UID/GID1000. They reproduce the old 0700
failure, verify private transport remains inaccessible, read and compile all 14
prepared Python outputs, and import the actual five stdlib-only hardened modules
(security, transport, policy, DNS and readiness) from the public code tree.
Private inputs are rejected before becoming image files. Both preparation paths
are tested under umask 077.

No Docker build/COPY was executed in this task. Root ownership was verified in
the isolated filesystem model; actual future image ownership and full Django
initialization still require a separately authorized build/integration test.
Compiling Django-dependent modules does not prove those application imports work.

All eight upstream input pins remain byte-identical to 1124d96. Eleven of the
original 13 hardened output hashes remain unchanged. Two change deliberately for
the new policy interface; one new module makes 14. Other source bytes were not
changed by packaging. The four existing readiness overlays and production image
pins are unchanged. New expected hashes never legitimize unrelated drift.

## Actual callers and trust boundary

The original policy was read twice: provider_security.policy() at job/resource,
status-contract and repeated I/O checks, and MetadataHTTPS.authorize() immediately
before DNS/route/TLS connection authorization. Fixing just the first reader would
leave the UID1000 failure in the second path.

Both server paths now consume the same trusted public reader. The transport's
root-private reader remains available to its existing separate users, but the
server passes an explicit authorization-reader callback and cannot fall back to
that private file. Native API routes, serializers, account ownership, background
job gates and database behavior are unchanged. The CLI requires the new
public_policy_lease feature and all 14 exact output hashes; its unconditional live
registration and native-removal gates remain disabled.

Trust remains with the host root operator, private policy and existing trusted
guard/grant producer. A Django administrator, compromised UID1000 worker, provider
response or CLI draft cannot publish approval. Root is trusted; this interface
cannot defend against a malicious host root or a privileged mount replacement.
No privileged worker, network proxy, listener, daemon, timer or new network exists.

## Implemented interface

Root retains `/run/dispatcharr-provider`, root:root 0700, and existing per-provider
policy files root:root 0600. Their schema/values and access permissions are not
relaxed. No private policy directory is mounted into UID1000 workers.

Candidate root publisher `native-provider-hardening/publish_policy.py` uses:

- A root-private single-link 0600 writer lock, nonblocking flock, and private
  `.status-anchor.json` with the approved public directory device/inode.
- A new, stable `/run/dispatcharr-provider-status`, root:root 0755. Explicit init
  refuses existing or unexplained directories; no adopt/reset/replacement command.
- One root:root 0644 single-link regular `<provider-key>.json` per authorization,
  max 64 providers, max 64 KiB per record. This is intended for a read-only
  **directory bind** into AIO at the same path; never a bind of individual files.

Initialization creates the anchor once. Publication takes the private lock and
verifies the anchor, then **withdraws the old record before private-policy or
namespace-grant validation**. It validates the exact private schema, writes a fresh
cryptographic generation via fsynced temporary file and atomic replacement, and
rechecks the guard snapshot. Any later failure attempts withdrawal again. Errors
are fixed safe messages; no policy, credentials or raw URLs enter arguments/logs.
A failed initial withdrawal aborts publication without extending the old lease.

Revoke unlinks the current record and fsyncs the directory. Revoke-all attempts
every known record even after an individual withdrawal failure and reports failure.
A crash releases the kernel lock; no API mutation or automatic retry is involved.
Unexplained partial files or anchor metadata are not silently reconciled/adopted.

### Minimal public assertion

The record envelope contains schema, fresh authorization generation, current guard
generation, issued time, the approved public anchor device/inode and a strictly
allowlisted policy projection. It contains
only authorization inputs: provider-key hash, contract/schema, AirVPN metadata-only
purpose, allowed operations, boot identity, approved VPN and distinct host namespace
identities, tun0 requirement, expected guard-policy digest, XMLTV URL digest,
expiry and exact allowed endpoint host/path-hash/public-IPv4 tuples.

Raw endpoint paths are replaced by canonical JSON SHA-256 hashes, so path tokens
are not published. Credentials, complete provider/EPG URLs and free-text private
review_reference are omitted. Unknown private fields are rejected rather than
copied. The reader synthesizes a fixed nonsecret review marker for the existing
transport checks. Hosts/IPs are necessarily visible authorization metadata; hashes
are not encryption and can reveal guessed low-entropy identifiers. Operators must
review that metadata exposure before granting a real provider.

Expiry is the earlier of private approval expiry and **300 seconds after
publication**. Private approvals still have their existing 24-hour maximum.
No automatic refresh occurs. An operator must explicitly republish before another
approved metadata operation; expiry can abort a long background import. New
publication changes generation and invalidates an already-running job rather than
silently extending it. This intentionally fails closed until reviewed operation
sequencing is installed.

### Unprivileged reader

provider_policy.Reader walks trusted ancestry with O_NOFOLLOW directory opens,
requires exact root:root ownership/modes, and pins the public directory device/inode
for the worker lifetime. Every record must match that device/inode even on first
use, so a new worker also rejects a record copied onto another directory.
Each check reopens the current filename relative to a
fresh directory FD; no pinned readiness-file inode or cached authorization is used.
A second current-path directory lookup detects replacement during the read.
Root-owned sticky /tmp ancestry is supported for isolated fixtures; the final
anchor still requires exact nonwritable 0755. Production path is under /run.

Files must be root:root 0644, regular, single-link, no-follow and bounded. Duplicate
JSON fields, nonfinite numbers, wrong fields/types, oversized or malformed records,
future/expired/overlong leases and unknown provider keys refuse. The reader checks
host boot, actual process network namespace, existing guard/grant schema and
matching current generation/policy digest. Returned policy includes authorization
and guard generations; existing job equality checks pin them for that job.

Destination checks retain exact HTTPS/443 host and path authorization (by digest),
public IPv4 allowlisting, DNS answer validation and connection IP pinning, tun0
route checks, TLS verification, redirect/retry denial, concurrency/budget/size and
I/O deadlines. Synchronous API requests, explicit Celery work and repeated fetch
checks use the same reader. Automatic remote tasks remain denied. Nothing
changes DW English, its broadcaster allowlist, media authorization or Jellyfin.

## Revocation and limitations

Successful unlink is visible at the next current-path authorization check,
including through a read-only directory bind. Guard/grant withdrawal or generation
change independently rejects the assertion. Generation replacement aborts active
jobs at their next check. Revocation does not atomically cancel a packet or undo
completed API/EPG work; existing check-to-use windows and bounded I/O waits remain.
Readiness asserts trusted application state, not continuous kernel or VPN-provider
attestation. DNS/route/TLS enforcement and the kernel/VPN boundary remain essential.

A publisher crash after publication or failed withdrawal can leave the old record
usable until its lease expires. A bind to an old directory cannot observe a
replacement host path. Tests demonstrate both facts instead of claiming immediate
revocation. A trusted clock and boot/generation checks limit such records to five
minutes; no copied policy is permanently valid. Clock integrity and host root
remain trusted. Publisher anchor mismatch refuses new publication. Worker current
path replacement refuses; a stale directory bind relies on expiry/guard withdrawal.

The supported replacement protocol is: revoke through the original anchor,
verify withdrawal through existing consumers, stop/reconcile authorized work (or
establish expiry), then retire the empty directory and initialize a new runtime
anchor only in a separately reviewed transition. Never replace a populated anchor,
restore its old inode metadata, clear drift just to proceed or assume a copied
file was revoked. The publisher deliberately supplies no force-replacement tool.
If revocation fails, stop approving jobs and preserve evidence; do not retry API
mutations or claim successful revocation. Compensating managed cleanup and finite
leases are necessary protections, not instantaneous guarantees.

## Tests and evidence

**537 PASS, zero failures/errors/skips: existing 504 plus 33 new regressions.**
The six original policy-contract test cases were adapted to exercise the new
shared validator/reader instead of the obsolete private server-file reader;
permission behavior is additionally exercised with real UID1000 filesystem tests.
All original test cases/counts are retained. Source patch application and exact
hash reproduction pass against the unchanged pinned upstream fixture.

| Suite | Passed |
|---|---:|
| Provider CLI/native/API contract | 139 |
| Hardened source/policy/application fixtures | 66 |
| Synthetic TLS/DNS/guard transport | 14 |
| Existing stack/security/admission/lifecycle/gateway | 210 |
| Historical persistence | 26 |
| Prior guard interface | 14 |
| Guard lifecycle design | 28 |
| Image-input/packaging tests (7 retained + 1 new private-input rejection) | 8 |
| New permission/interface/crash/bind tests | 32 |

The new namespace suite tests valid publication, actual UID/GID1000 reads and
zero effective capabilities, private traversal denial, write/publisher refusal,
missing/malformed/duplicate/oversized status, ownership/modes, links/FIFO, leases,
boot/namespace/provider/policy mismatches, guard generation/revocation, active job
replacement/revocation, atomic publication failures, actual publisher exits before
and after publication, lock/anchor substitution, unknown anchor refusal, cleanup
partial failures, read-only bind enforcement and the honest stale-bind bound.
The destination test proves the public callback never invokes private_read and
still rejects altered host/path/protocol. Network transport remains separately
covered by existing synthetic TLS/DNS fixtures, including DNS rebinding.

Fixtures use isolated user, mount and network namespaces with private tmpfs.
The fixture creates its own root-owned /tmp inside its namespace, without relaxing
production ancestry checks. No host mount, systemd/Docker service or real firewall,
VPN/DNS setting is changed. Existing Caddy fixtures made 91 isolated synthetic
requests. No real provider or production endpoint was contacted. No image,
container, production database or credentials were accessed. No new fresh
production-health/kernel attestation is claimed from this offline task.

Exact suite/log hashes and changed runtime outputs are recorded in
`configs/dispatcharr-iptv/native-provider-hardening/permission-fix-results.json`.
All source and tests are sanitized; no raw runtime policy, credentials or archive
is committed.

## Required coordinated installation work — not performed

This is an implemented offline interface, not a deployable matched release.
A future reviewed transition must address these exact components:

1. Build a separately authorized image with the corrected context and 14 pinned
   outputs. Re-run actual Django migrations/initialization, Celery workers and
   native API/XMLTV integration. Full application import/registration compatibility
   is still unproved; no new image identity is offered here.
2. Review/install the root publisher and its source pins; initialize a new empty
   public runtime directory and private anchor metadata. Keep the original policy
   files/private directory inaccessible. Never migrate them by chmod/chown.
3. Update permanent-streaming/compose.yaml, verify.py and manifest.json for exact
   AIO public-policy and existing guard-status read-only directory mounts and the
   newly accepted AIO image/source pins. Do not change the relay image/mounts.
4. Review managed sequencing in permanent-streaming/lifecycle.py and
   30-permanent-streaming.conf, boot-admission-phase6b3k/20-resource-admission.conf,
   minimal-phase6b3d/cleanup.py and guard-unit 20-trusted-readiness.conf: withdraw
   provider assertions before admission, private-policy changes, stop/failure or
   guard reapplication; attempt all cleanup even if another action fails. Publish
   only after the existing trusted guard and verified VPN namespace grant exist,
   and before an explicitly authorized manual native job. No automatic renewal.
   Coordinate serialization with private-policy edits; direct edits are unsupported.
5. Review exact source/unit/verifier pins and trusted-guard-tests/transition-manifest.json
   together. The existing guard.py/kernel policy, namespace-grant producer,
   admission limits/timeouts and original three-service behavior need no semantic
   change. No protected unit, cleanup helper or transition manifest was changed
   in this task; their future coordinated hooks/pins are a deployment prerequisite.
6. Preserve native CLI live gates until separate provider/destination approval,
   private publication procedure and one bounded metadata test are authorized.
   Plan explicit lease renewal for later manual work; no timer/daemon is proposed.

For a future rollback, first withdraw assertions and prove no active/pending or
uncertain native API/worker job remains. Reconcile ownership journals and disable
relevant remote schedules/sources before restoring an unhardened AIO. Restore the
complete previous image/source/mount/verifier/unit set through its approved
managed lifecycle, preserving data, VPN owner, kernel guard, relay/gateway and
unrelated services. Do not delete records or clear uncertain jobs to force a
rollback. Nothing was installed here, so no production rollback was needed.

**GO for review of the offline correction. NO-GO for build, installation, live
onboarding or deployment without separate authorization and the matched transition
work above.** No further build is started automatically.

## Changed-file inventory and SHA-256

Two runtime files change and one is added; the eight upstream patch transformations
and eleven existing output hashes remain unchanged. server.patch, output-hashes
and CLI expectations change only to describe that reviewed source set. Packaging
and tests/docs account for the remaining changes below. The historical failed
image evidence is retained, not regenerated. This report's enclosing Git commit
identifies the report itself, avoiding a self-hash cycle.

| File | SHA-256 |
|---|---|
| configs/dispatcharr-iptv/hardened-image-integration/README.md | 1597a886fc5efa655b86e91cbb7d0ce0a11539c4505428cc2b651871ecb4e57b |
| configs/dispatcharr-iptv/hardened-image-integration/build_once.py | 178bfe6524fd7bcec480e206e4db53698ab7df431459c9055d547f46b6a6c5da |
| configs/dispatcharr-iptv/hardened-image-integration/prepare_context.py | c3ef08b8ca0d8c12f8daf0c23be2b0edf4f366a18c5afd1c23b1eea1014119da |
| configs/dispatcharr-iptv/hardened-image-integration/test_build_modes.py | 46c99220fa5d1e9ca044904f5e702113f18b67bdac4a1972e3af809da95a8e5a |
| configs/dispatcharr-iptv/native-provider-hardening/README.md | 1d3a062633b99d602363424d30c7deab541905ba54f6b4f6b0ddb09c6a47caa9 |
| configs/dispatcharr-iptv/native-provider-hardening/output-hashes.json | 6f4731afe4fb93b490d0699372526289fc55480f88128915569283d6518cd36d |
| configs/dispatcharr-iptv/native-provider-hardening/publish_policy.py | d272bcaa04a2c04570b3e56828857c8fe75ee68b22f93e3fa23eed06ab8ec1a2 |
| configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_policy.py | 2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639 |
| configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_security.py | b63d7c4af215d7b135110667c1b37166ddc9b19c3456a4c6703618042d30af16 |
| configs/dispatcharr-iptv/native-provider-hardening/runtime/provider_transport.py | 4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39 |
| configs/dispatcharr-iptv/native-provider-hardening/server.patch | 4c0ebba29aa8b1e728c4cf4b1ca65617199c0f411031c6cd04261694cb01b753 |
| configs/dispatcharr-iptv/native-provider-hardening/tests/permission_fixture.py | 5fb62e1fbff176e7b9320a32e1e0fa37d737316df497e45112ceb78b5177055e |
| configs/dispatcharr-iptv/native-provider-hardening/tests/run-permissions.sh | 74a36a5f4bb5a5e80de63bbacd2aa4fad070436c626b0de540234990f01e58e9 |
| configs/dispatcharr-iptv/native-provider-hardening/tests/test_hardening.py | 65268386407873b6fd3687e84be2a505f6ab67e5c5c333825d4d34b1786a665f |
| tools/dispatcharr_provider/api-contract.json | 20c2423d6ce16ca835f27c739843195e4bb5732f0b7a202184cc78c7f2b7662c |
| tools/dispatcharr_provider/server-contract.json | ab805deac2bd8f0620ddd05b853944ae61331c1cc7aba8fe031af742b8fc27e3 |
| configs/dispatcharr-iptv/native-provider-hardening/permission-fix-results.json | 367fc8fdbe2bda1a613556f728e15c6a8ed366658a3221d078f570bc567d1961 |
