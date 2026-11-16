# Bag-End read-only Proxmox API client: setup status

Date: 2026-11-16

## Purpose and current state

Bag-End is designated as the primary read-only Proxmox API client. Setup is incomplete: authenticated API access and resource metrics have **not** been verified or collected.

This status records the bounded discovery and preparation performed on Bag-End. It does not authorize changes to the Proxmox cluster, its guests, or application services.

## Verified preparation

- All three cluster nodes are reachable on TCP port 8006.
- Default HTTPS certificate verification stops on all three nodes because the issuing cluster CA is not trusted by the client. Reachability is not successful TLS or API authentication.
- `/etc/codex-proxmox` was created with `root:root` ownership and mode `0700`, then verified empty.
- Python and OpenSSL are available. `curl` is absent; no package was installed.
- No existing approved authenticated transfer path was available for the required trust material and token provisioning.
- No credentials were read. No Proxmox, VM, or Dispatcharr configuration was changed.

## Remaining steps

1. Obtain the **public cluster CA PEM** through an already trusted console or another approved out-of-band channel. Verify its fingerprint against that trusted source before using it. Do not bootstrap trust from an unverified HTTPS connection.
2. Configure that CA only for the dedicated Proxmox client. Do not change the system-wide CA trust store or disable certificate validation.
3. Provision the already-issued API token into a root-only local credential store with mode `0600`, using hidden terminal input. Keep the token identity and secret out of chat, documentation, command-line arguments, logs, and source control.
4. Verify certificate chain and hostname validation for each node, then perform a bounded set of read-only API GET requests per node. Stop on any trust or authentication failure rather than bypassing it.
5. Check the token's effective read-only permissions and expiry before relying on it for ongoing collection.
6. Once authenticated reads are verified, collect node CPU information, allocation and resource details, including VM 130. Record verified findings separately; do not infer or claim metrics before collection succeeds.

## Scope and disclosure boundary

This public document deliberately excludes internal addresses, certificate fingerprints, token identities, secrets, and private command output. The empty root-only directory is preparation only, not evidence that authentication is configured.

Related pinned documentation: [homelab-operations commit 268dedb](https://github.com/APMurtha/homelab-operations/commit/268dedbfc19080340971093fe0d4e8815b93c420).
