# Corrected hardened Dispatcharr image build

**PASS — GO for separately authorized isolated runtime-test review only.**
Exactly one build completed and read-only image verification passed. No application
acceptance, image binding, provider activation or deployment was performed.

| Identity | Value |
| --- | --- |
| Approved source commit | `8764cfdaff97b8d94102f03d9b367f1e1de6c317` |
| Immutable local base | `sha256:14c8373377b8a7244e9b49d65a364798d02e2ace405b04730dba7a149f7cad21` |
| New immutable image ID | `sha256:71eba6fe9e62b0fd1ec632a3ceeecdbc54f278058500e567dd2be6a9fc96b439` |
| Fresh review tag | `local/dispatcharr-native-hardening:corrected-8764cfd-b061c11e` |
| Preserved old image | `sha256:e37c7aacaacea0ce2d5b19fbc8b87b9e36b6731d7236799e40bac2fe1e64b4be` |
| Image creation UTC | `2026-11-18T06:50:26.991110821Z` |
| Logical image size | 4,249,036,311 bytes |
| Sanitized results SHA-256 | `2ed95e293499735a516a0ef8eb996411b485e7b4917c7f77cad83757273e9d5c` |

## Preflight and provenance

The checkout was clean at the exact approved commit before preparing the payload.
The approved changed-file inventory, source/release hashes and three user-specified
correction hashes matched. prepare.py verified all eight pinned upstream inputs,
reproduced all fourteen corrected outputs and reproduced server.patch exactly.
No source pin, application source, release contract, Dockerfile or existing build
recipe changed during execution.

NEST 2.1.0 verified the explicitly selected andrew / andrew-media profile, host
rivendell and SSH account murth (UID1000). Existing sudo -n was used only for the
root-private temporary build workspace and authorized daemon access. Before the
build all 33 production container and complete network/volume fingerprints matched
the prior accepted snapshot. Dispatcharr, its VPN/relay/gateway and Jellyfin were
healthy. The immutable base existed locally with no ONBUILD instructions or
image-declared volumes; the proposed review tag was unused. The old image's ID,
labels/config digest, layer list, tags and creation metadata were recorded.

The base's eight upstream source hashes and four readiness hashes were verified
by a streamed docker image save, with root ownership, source modes and all required
parent-directory modes checked. The export exited zero in
78.423 seconds. No source was
extracted into a probe container and no private policy contents were accessed.

| Capacity gate | Load 1m | Available RAM, bytes | Free /tmp filesystem, bytes |
| --- | ---: | ---: | ---: |
| Initial preflight | 0.38818359375 | 3,541,164,032 | 7,898,841,088 |
| Immediately before build | 0.23193359375 | 3,558,633,472 | 7,896,494,080 |

Both passed unchanged build thresholds: load <=2, RAM >=2 GiB and disk >=3 GiB.
After the expensive base export, at least 120 seconds were allowed to settle before
the fresh build gate; actual elapsed time was 247.763
seconds, including preparation and monitoring overhead. No repeated admission or
build retry occurred. The runtime runner and its separate policies were not invoked.

## Single build command and result

The reviewed recipe's COPY-only Dockerfile and context writer were reused unchanged.
The 16-file allowlisted context contained only Dockerfile, fourteen public Python
outputs and their generated source-hash manifest. Root-private orchestration
replaced the recipe's stopped-container probes with read-only image-layer scanning.
The exact executed orchestration is published as corrected_build_control.py;
its SHA-256 is `f6eabc9ecdb699bfa81a2a15580bf69248ba25ab2fe8b825d84a17aafa9c8068`.
The reviewed recipe SHA-256 is `009c0a70be6b41aadcb726de821feba8ec825d0b1be3c76fb266aee772c5d7d6`.

The Dockerfile has only FROM, LABEL and COPY, with COPY --chown=0:0. Its historical
revision label was overridden using the build command's label option to accurately
identify this approved correction; neither source bytes nor Dockerfile were edited.
The existing legacy builder was selected with DOCKER_BUILDKIT=0.

```sh
docker -H unix:///var/run/docker.sock build --pull=false --network=none --no-cache --memory=512m --memory-swap=512m --cpu-period=100000 --cpu-quota=50000 --label org.opencontainers.image.revision=8764cfdaff97b8d94102f03d9b367f1e1de6c317 --iidfile /tmp/dispatcharr-build-corrected-8764cfd-b061c11e/image.id -t local/dispatcharr-native-hardening:corrected-8764cfd-b061c11e /tmp/dispatcharr-build-corrected-8764cfd-b061c11e/context
```

Exit **0**, elapsed **145.220 seconds**, under the unchanged
180-second build watchdog. A root-private, exclusive build-intent receipt was
fsynced before the command. There was one invocation and no automatic retry.
Pull was disabled, build network was none, memory/swap limits were 512 MiB and
CPU period/quota requested 0.5 CPU. No Dockerfile RUN, package installation or
base upgrade occurred. Docker's legacy builder created/removed its own intermediate
metadata containers; no manual verification container or application process was
created or started. Postflight found only the original 33 containers.

The final image has the approved revision label and the original 30 base layers
unchanged as a prefix, plus one COPY layer. The review tag resolves to the recorded
immutable image ID. No production tag or old review tag was replaced.

## All eighteen installed source hashes

The new image was independently streamed and inspected without running it. Export
exit 0; elapsed 94.584 seconds. All eighteen hashes match
the corrected release contract:

| Image path below /app | Verified SHA-256 |
| --- | --- |
| `apps/epg/api_views.py` | `6fafed61eb78ebfdd669ab60745001948a63f708dd549175e8d4950a68ce0051` |
| `apps/epg/signals.py` | `a55f451c8af899edb79f201802e3533cf2139199c37abdb95fa4978a8dac2d8c` |
| `apps/epg/tasks.py` | `3d94f0c6aa4eed6520d584d97ad85b62760a9ae80efeac640a690eabacc427c6` |
| `apps/m3u/api_views.py` | `6c48c35abc821efbb428a74c832e7c8c018eef472d6f987505169cd83d902936` |
| `apps/m3u/signals.py` | `7b7b35c2931f401ef179b132648496749c49c07fabf0dd85d6c019e10dbacd92` |
| `apps/m3u/tasks.py` | `75a6eb9276ec96b0e5de2ae2b1274a63ffe47ef89cc8d6c1620a89e049467fb1` |
| `apps/proxy/live_proxy/input/buffer.py` | `17d77baba54923ef3414a7051eebed9c27a891eb1479dd9c68a299e0d5f89810` |
| `apps/proxy/live_proxy/input/manager.py` | `ce2400eb4bcdaec43ee571b7982f85ca2cd719eec9acb0282976edb3684245cf` |
| `apps/proxy/live_proxy/output/ts/generator.py` | `db9200e53419a9ca3acb19ad05df49d3a4c9c06567d3e659c26214cecf5e312b` |
| `apps/proxy/live_proxy/readiness.py` | `fb4882ba579b14b0a2f7aec7306c8f31e1c7bb5f6c3acacce1a40dc62de1143b` |
| `core/api_urls.py` | `8ba3069abff1d26ff9d0070fd83194097c8b6f565b0b0391f46f0709155de324` |
| `core/provider_dns.py` | `28c9564793e1285eb72bb9d91ab24a85ccc3ca2f3db80398445d380b53d9af3a` |
| `core/provider_policy.py` | `2691cc3eeed26f13869d7cdacc671f0e2eebcd46e54e944279ffe78dd0b82639` |
| `core/provider_readiness.py` | `5f137b756a1a988d4641ccd8a13b6bd4e13849bbdb2539c22026c88f4d8cf698` |
| `core/provider_security.py` | `8d3049e4dfb471f62a66c13a17e94da04e6cff3050e07121208327071c4ce004` |
| `core/provider_security_view.py` | `b3e77ccd704251b85cccdc8df9966ecc8d748a4a1542780512746886be31374b` |
| `core/provider_transport.py` | `4032865e09c82b5a755af99ef2a8b62e88aca46e346321565dd0af783cec0d39` |
| `core/xtream_codes.py` | `ed31daaf05ee812cfa7750b423c8b8840ab19bca48cc3ee560202857848133fa` |

The three corrected hashes match the explicit authorization. The other eleven
hardened outputs and all four readiness hashes match the retained-image contract.
No source hashes were regenerated to accept drift. The derived in-image source
manifest was generated from the approved fourteen-output inventory in the context.

## Ownership, modes and private-state boundary

All eighteen selected source files are **root:root 0644**, regular files, with no
ACL metadata. Their ten required application directories are **root:root 0755**,
including /app, /app/apps and /app/core. This establishes ordinary UID1000 read /
traversal access through Unix DAC. No application import or UID1000 application
process was run; that remains an isolated-runtime acceptance check.

The host transport and context roots are root:root 0700 and their private receipts
are 0600. Public application subdirectories in the context are root-owned 0755;
public source files are root-owned 0644. An actual temporary host child dropped
supplementary groups and switched to UID/GID1000: traversal of the private build
workspace was denied, both before and after building. It did not execute application
code or inspect production policy paths.

Image-layer inspection found no /run/dispatcharr-provider or
/run/dispatcharr-provider-status runtime state baked into either image inspected.
The context whitelist excluded policies, credentials and private runtime files.
No real policy was read, installed or mounted. Actual UID1000 refusal of a future
private-policy runtime mount and live public-authorization consumption still belong
to separately authorized isolated application acceptance; image metadata alone is
not presented as that runtime proof. No disposable verification containers were needed.

## Production and old-image preservation

Before/after snapshots compare exactly across all 33 original container IDs,
immutable images, start times, restart counts, status/health and SHA-256 digests
of full Config, HostConfig and Mounts. Complete Docker network and volume inventory
fingerprints are unchanged. The four Dispatcharr services and Jellyfin remain
healthy. No Compose, systemd, daemon, firewall, VPN, DNS, Jellyfin or provider
configuration was modified. No production container was stopped or recreated.

The old immutable image remains present with identical tags, layers and metadata;
it was not used as this build's base, overwritten or retagged. Historical receipts
were not cleared or reused. The new image, root-private build receipt/log, source
and verification receipts remain retained under `/tmp/dispatcharr-build-corrected-8764cfd-b061c11e`.

## Evidence and next boundary

Sanitized source/input/context hashes, all eighteen file metadata records, directory
metadata, exact build command, capacity measurements, old-image evidence, full
before/after production fingerprints and eight private-receipt hashes are published
in corrected-image-build-results.json. Its recorded build-log hash identifies the
private log without publishing host-private data.

Nine synthetic tar inspection tests pass: valid modes, wrong owner, inaccessible
application directories, private source modes, accidental policy state, source
hash drift, symlinks, whiteouts/opaque removals and final layer ordering. The complete
harness suite passes **125 tests**, including the existing 116 tests. No Docker
operation occurs in these tests. The prior approved 704-test application-source
offline baseline is retained; this build task did not rerun Django/Celery or any
application runtime matrix.

**GO for isolated runtime-test review only.** A separate authorization must approve
binding this new image and its exact eighteen hashes to the isolated harness, with
fresh capacity/production checks, reviewed synthetic fixtures, network-none limits,
strict socket audit, detached one-shot transport, durable receipts and scoped
cleanup. Real Django migrations, Redis-backed Celery results, native inactive group
discovery/ownership, partial failure, selected channel import, XMLTV/EPG mapping,
UID1000 runtime policy boundaries and DW/backend compatibility remain unaccepted.

The source release still has no image binding; no deployment contract was changed.
No provider request, real credential/policy access, playback or application runtime
attempt occurred. Stop after this build evidence publication.
