# Dispatcharr unprivileged relay guard-interface review

2026-11-17 UTC. Andrew’s Rivendell (`10.10.20.30`), repository `APMurtha/homelab-operations`, branch `docs/udm-pro-max-migration-prep`.

**NO-GO: no deployable interface correction is implemented.** Permission-faithful offline tests confirm that the narrow file-bind/copy approaches cannot satisfy the requested failure, generation and revocation semantics with the protected guard lifecycle unchanged. Following the task’s explicit limitation/stop instruction, this change publishes the evidence and tests, leaves candidate `776f9843228148fe3d1fd744089f97fb0c82601e` unchanged, and stops. A separate review must authorize the protected publisher/lifecycle changes needed for a secure interface.

No server contact or production filesystem/configuration change occurred. The original three-container stack was left untouched; its last verified healthy state is recorded in deployment report commit `38855f7a5df337d5f1cf5386271c9ce264a8361a`. This offline task makes no new live-health claim.

## Confirmed failure and scope of inference

The [deployment report](dispatcharr-permanent-streaming-deployment.md), section 13 at `38855f7`, records actual guard directory ownership/mode root:root **0700**, readiness file root:root **0644**, and a real UID/GID 1000 `PermissionError` reading that file. The managed relay has UID/GID 1000, no elevated capabilities and a read-only directory bind at `/guard`. Directory traversal fails before the file’s public read bits can help. The corrected stopped-container verifier passed; the relay exited before API registration.

The production relay prints only a generic refusal. That message does not establish the exact caught exception. The confirmed access incompatibility is independently reproducible using the unchanged relay’s `check()` and full startup wrapper in isolated fixtures, where it raises `SecurityRejected('guard_not_ready')` before endpoint publication. No production traceback is inferred from the synthetic reproduction.

## Guard-read dependency inventory

| Component | Existing dependency |
|---|---|
| `hls_relay.Relay.__init__` | Takes `ready_file` and the expected policy digest from private configuration. |
| `Relay.check()` | Reads the marker pathname and compares its text to the expected digest; also enforces local fatal/expiry state. No inode/generation validation exists. |
| `relay_main.run()` | Calls `check()` before binding the listener/publishing endpoint; its existing state writer repeats checks every two seconds and closes on failure. |
| `Relay.resource()` | Checks before serving a manifest/segment request. |
| `Relay.fetch()` | Checks before DNS, after DNS before connection, and after body validation. Request budget/DNS/TLS restrictions remain separate. |
| Relay `/healthz` | Calls `check()` and returns 503 on failure. |
| `health.current()` | Reads current endpoint/stats and makes a non-media `/healthz` challenge; registration/binding verification depends on it. |
| `register.register()` | Requires current relay readiness before work and again before commit/binding publication. |
| `verify_binding.verify()` | Calls `health.current()` and correlates owned records, binding and exports. |
| `verify.py` / Compose / contracts | Require `/guard/ready`, the original read-only guard-directory bind and the existing host guard digest/table checks. |
| Root AIO/VPN startup gates | Independently read `/guard/ready`; these accepted original three-service consumers are outside this correction. |

`guard.py` publishes only the policy SHA-256 plus newline, not a generation identifier. It loads policy and validates private inputs/WireGuard compatibility **before** reaching `ready.unlink()`. After unlink it runs nft syntax/application transactions and creates a new marker using `mkstemp` + fsync + atomic replace. A late nft failure leaves the original marker absent. An early policy/WireGuard validation failure leaves the old marker entirely unchanged. Reapplication with identical policy creates a different inode with the same digest.

The guard oneshot unit uses `RemainAfterExit=yes`, UMask 0077 and has no ExecStop/revocation action. The stack binds to that unit and stops on its managed lifecycle changes, but that does not make an independent guard-helper invocation’s early validation failure observable in the marker. The candidate stack also invokes `guard.py apply` directly during prestart. No existing public, per-generation revocation record is available to the unprivileged relay.

## Interface evaluation and rejection

| Approach | Access and revocation assessment | Decision |
|---|---|---|
| Existing read-only directory bind | Preserves live pathname lookup but UID 1000 cannot traverse root 0700. | Unusable without changing protection. |
| Bind only the existing `ready` file | UID 1000 can read only the approved file; no siblings exposed. A bind pins the inode: unlink/replacement does not make its old contents unreadable. | Plain digest check accepts stale authorization. |
| File bind plus inode/link-count checking | `st_nlink==0` detects unlink/replacement of the pinned inode in tested guard paths. Actual read-only remount prevents writes. Early validation failure leaves contents, inode and link count unchanged. | Still cannot meet guard-failure revocation requirements. |
| Minimal copied status file/directory published by candidate prepare | Could expose only a root-owned read-only digest/generation record. Original guard never updates/revokes that copy; it survives both late failure and successful generation replacement. | Rejected; copied readiness can outlive authorization. |
| Hard-link variant | Keeps the source inode linked after original unlink; defeats unlink-based revocation unless another publisher removes the extra link. | Rejected. |
| Short expiry or candidate-only prestart/cleanup wrapper | Bounds some stale intervals but permits authorization until expiry and observes only its own operations. Existing guard entrypoints do not revoke its status on every failure/replacement. | Does not establish current guard generation; not implemented. |
| Guard-published minimal status directory | Could provide restricted current-generation publication/revocation, but the trusted guard entrypoints must own and update it on all relevant paths. | Requires protected guard lifecycle modification; stop boundary. |

The decisive counterexample has two observable histories: (A) successful old guard application; (B) the same success followed by an early failed policy or WireGuard validation. For the bound marker, contents, inode and link count are identical in both histories. Any relay check based only on that unchanged interface must make the same decision, despite the requirement to revoke in B. A candidate-generated random identifier or timestamp cannot reveal an event the trusted publisher never records.

A directory mount/copy cannot repair that information gap. A background watcher, privileged relay, new service/socket, broader directory permissions or policy exposure would violate the requested boundary and is not introduced. Existing periodic relay checks help only when the observed state actually changes; this review adds no polling infrastructure.

**Chosen interface: none accepted.** No copy, file bind, inode-check proposal or stub is added to the candidate as an authorization path. The inode-aware function in the isolated test is explicitly a rejected hypothesis, tested to demonstrate its unsafe early-failure acceptance.

## Required publication/revocation semantics for a future scope

A secure public status interface requires a separately reviewed trusted-publisher contract: revoke before input parsing/validation and before reapplication, publish a distinct generation only after accepted rules/marker verification, invalidate on all failure/stop/replacement paths, and ensure old bound objects cannot retain valid authorization. The relay must correlate that current generation and reject missing, malformed, revoked or stale status without gaining policy access or privileges. Publisher crash/replacement and managed stop/restart ordering need explicit tests.

Those semantics cannot be asserted for the current unmodified guard. This report does not provide an untested implementation or authorize changing it. Keep root-private guard ownership/modes, original nftables/VPN enforcement and original consumers intact while a future scoped design is reviewed.

## Permission-faithful fixtures and regression results

Added tests are outside the deployed candidate, under `configs/dispatcharr-iptv/guard-interface-review/`. They execute in fresh user/mount/network namespaces, using a private temporary tmpfs. Namespace UID/GID 0 owns the 0700 guard fixture; child processes actually switch to namespace UID/GID **1000**, clear supplementary groups and assert zero effective capabilities. Linux subordinate-ID mappings provide those identities without host root; UID and permission checks are not mocked. No production guard path is read or modified.

Real bind mounts are remounted read-only. A file-owner write returns **EROFS**. Root-private traversal returns **PermissionError**; only the one bound marker is accessible and the synthetic protected sibling is not exposed. The original guard implementation runs with only its `/run` directory mapped to the fixture; actual policy and WireGuard parsing are exercised. nft subprocess calls are mocked, so no firewall command executes.

All **14 focused tests pass**:

1. Reproduce the original 0700 traversal failure through unchanged `Relay.check()`.
2. Read a valid current file bind without exposing protected siblings.
3. Enforce a real read-only bind against its file owner’s write attempt.
4. Reject missing readiness through the unchanged candidate check.
5. Reject invalid contents on an accessible interface.
6. Prove plain file-bind digest checking still accepts after source unlink (unsafe counterexample).
7. Reject the unlinked bound generation using the evaluated inode-aware hypothesis.
8. Detect successful source replacement with identical digest via inode/link change.
9. Prove copied status survives a late failed guard check (unsafe counterexample).
10. Prove early policy failure leaves the bound inode/content/link count unchanged and accepted (decisive unsafe counterexample).
11. Prove early WireGuard mismatch has the same unobservable-failure problem.
12. Prove copied status remains accepted across successful source generation replacement.
13. Reproduce full relay startup refusal before endpoint publication with the private-directory fixture.
14. Demonstrate that the evaluated accessible file bind permits synthetic non-media startup, health challenge and clean SIGTERM/endpoint removal. Fetch counter stays zero; this accessibility result does not make the interface safe.

The first synthetic successful-start harness run could not lazily import `bounded_server` after dropping UID, because the checkout’s private ancestor is not the deployed public read-only source mount. Preloading that unchanged module before dropping UID corrected only the harness boundary. Final focused execution is 14/14; no candidate behavior was altered to obtain that result.

| Existing offline suite | Tests | Result |
|---|---:|---|
| Policy / registration / exports / Jellyfin / lifecycle | 39 | PASS |
| Four-service mount/security contract | 16 | PASS |
| Diagnostic inventory | 7 | PASS |
| Provenance and complete candidate manifest | 3 | PASS |
| Minimal persistence | 12 | PASS |
| Boot admission | 28 | PASS |
| Isolated TLS/DNS/lifecycle/resources | 11 | PASS |
| Pinned Caddy groups | 15 | PASS |
| Historical persistence controller | 26 | PASS |
| **Existing subtotal** | **157** | **PASS** |
| **Focused feasibility tests** | **14** | **PASS: counterexamples demonstrated** |
| **Total** | **171** | **0 final failures/errors/skips** |

Native systemd syntax/dependency verification passed on temporary fixtures without executing services. Pinned Caddy made 91 synthetic fixture requests with external networking unavailable. The existing multiprocessing test emits its previously known fork deprecation warning; it completed successfully. Full results do not represent a working guard-interface fix: the new suite intentionally proves why the considered proposals must be rejected.

Reproduce:

```sh
sh configs/dispatcharr-iptv/guard-interface-review/run-offline.sh
CADDY_TEST_BINARY=/path/to/verified/caddy sh configs/dispatcharr-iptv/permanent-streaming/tests/run-offline.sh
python3 -B -m unittest discover -s configs/dispatcharr-iptv/persistence-phase6b3/tests
```

Requires unprivileged namespace support, subordinate UID/GID mappings with `newuidmap`/`newgidmap`, mount/ip tools and the previously SHA-verified Caddy binary. No image download/build/pull or service lifecycle operation is part of these commands.

## Exact changed-file inventory and integrity

Only these new non-deployed evidence files and this new report are added. This report’s own hash is not self-embedded.

| Added file | SHA-256 |
|---|---|
| `configs/dispatcharr-iptv/guard-interface-review/test_feasibility.py` | `44ac972b175e896673d297caffead43775e8e7c6bba254ec1c779b9ea1437329` |
| `configs/dispatcharr-iptv/guard-interface-review/run-offline.sh` | `c4d883bbde19f6f68c9948f510d82f0914c3958a743fce61ad9f5660b1d8cbdb` |
| `configs/dispatcharr-iptv/guard-interface-review/validation-results.json` | `f7765036a43c6133f98d5f4cfa739e2f3740dc7ddf092de397381a9a2b61024d` |

No candidate file or manifest changed. Every candidate byte remains identical to `776f9843228148fe3d1fd744089f97fb0c82601e`, including all image pins, UID/GID/capability/resource limits, Compose mounts, guard logic, relay request budget, lifecycle, registrar API behavior, gateway routing, exports/Jellyfin helpers and source manifest. No protected guard/base-unit/admission source changed either.

Relevant unchanged evidence hashes:

| File | SHA-256 |
|---|---|
| `configs/dispatcharr-iptv/guard.py` | `df53629a537e66fcbdf664076b9fa58de47d590e4a0f0d0128fd15f46f3088bd` |
| `configs/dispatcharr-iptv/security.py` | `e7a92e7753e666a6f8cafd1b0292cec5e65f1431b09fc92ba10678c26e5ef8e2` |
| Candidate `manifest.json` | `3d5ae000603fc8d3bf7796deb996c39f863ab877f45160edd22ebf9a65648ae4` |
| Candidate `compose.yaml` | `7587c2badc7c06b2bac59408964216d00f366b17109a6417caa38ba64399e51c` |
| Candidate `hls_relay.py` | `5eb958dbcf1ef6d2b92fa47ba4fb737511042486601969b955f7940241fb4b36` |
| Candidate `lifecycle.py` | `2e2c7664cf7ea9fc6d2d547f1b8248b3a6734f32a332c12fcf7f9af4e2e6a7ed` |
| Original guard unit | `bde5207014fa24781d8cd1275a54dac056684299e498f4773fca2ed2e98cc174` |

## Decision and remaining prerequisites

**NO-GO for candidate deployment, Jellyfin integration or playback.** The stated fail-closed requirement needs changes to the protected guard publisher/lifecycle, which is the task’s explicit stop boundary. No secure deployable candidate is presented for approval.

A future scope must review and authorize that publisher/revocation contract before implementation, update affected protected pins/verifiers deliberately, and repeat permission-faithful generation/failure/crash tests. Deployment would then require a separately approved corrected commit, the full fresh preflight, retained recovery references and another explicit bounded deployment window. None of that authority is inferred here.

The existing protected three-container deployment remains untouched. Stop after publishing this report and evidence; no infrastructure investigation, production correction or further deployment is undertaken.
