# Bag-End read-only Proxmox API client: verified access and resource findings

Report date: 2026-11-16

## Current status

Bag-End is the primary read-only Proxmox API client. Authenticated read requests succeeded with **HTTP 200 on all three cluster nodes**, with certificate-chain and endpoint-identity verification enabled. The issuing cluster CA is scoped to this client; the global trust store was not changed.

The effective grants checked were solely **Audit** permissions. The API denied access to the token's own exact expiry metadata with **HTTP 403**. Its expiry therefore remains unverified; no privileges were increased to obtain it.

The live credential and CA are retained locally in root-only storage. One-time transfer artifacts were removed after successful verification. Removal is not a claim of secure erasure. No secrets, token identities, encrypted transfer payloads, certificate fingerprints, or internal addresses are published here.

## Discovery and collection scope

Initial TCP reachability on port 8006 did not establish TLS or API authentication: default certificate verification initially stopped because the cluster CA was not trusted. That trust and credential setup is now complete for the bounded authenticated reads above.

Python and OpenSSL were already available; `curl` was absent and no package was installed. Aside from this dedicated client setup, no Proxmox, VM, or Dispatcharr configuration was changed. No migration, CPU reallocation, or service restart was performed as part of this investigation.

## Hardware and current running allocation

All three nodes report an Intel Core i7-4790S with **4 physical cores / 8 logical threads** and approximately **31.25 GiB RAM** each.

| Node / comparison | Current running CPU allocation | Current running memory allocation |
| --- | --- | --- |
| Orthanc | 12 VM vCPUs plus 1 container CPU | 20.5 GiB |
| Comparison node A | 6 VM vCPUs | 12 GiB |
| Comparison node B | 2 VM vCPUs | 4 GiB |

These are current allocation snapshots, not proof of the allocations at every point in the historical incident window. Allocated vCPUs are not equivalent to measured CPU consumption.

VM 130 is configured with **4 vCPUs and 8 GiB RAM**.

## Incident-window telemetry

The figures below are **60-second RRD AVERAGE** samples. Times are UTC.

| Time | Orthanc CPU utilization |
| --- | --- |
| 20:40 | 92.17% |
| 20:41–20:46 | 97.16–98.48% |
| 20:47 | 94.85% |
| 20:48 | 59.83% |

Additional observations:

- Orthanc load peaked at **10.674** on a host with 8 logical threads.
- I/O wait was at most **0.262%** and swap remained stable across the examined window.
- The other two nodes' incident-window CPU averages were approximately **2.24%** and **2.29%**.
- VM 130 used **71.04–79.63% of its allocated CPU capacity** during 20:40–20:46, declining to **25.48%** by 20:48. These guest percentages are normalized to its allocation, not the whole host.

## Interpretation and limits

The near-saturated Orthanc CPU samples, elevated load, low I/O wait, stable swap, and lightly utilized peers provide **strong evidence of host CPU contention coinciding with the guest gate**. They do not establish which process or guest caused the contention, or prove that the current allocation caused the incident.

One-minute averages cannot establish process-level attribution or resolve short spikes and ordering within a minute. No infrastructure change is recommended as an already-proven fix on this evidence alone. A next diagnostic pass should correlate the relevant guest/application logs with the same interval and verify the workload/allocation state before selecting a mitigation.

## Remaining verification

- Confirm exact credential expiry through an already authorized administrative view; the read-only token's metadata request returned 403. Do not broaden its permissions merely to resolve this documentation gap.
- Keep future collection bounded and read-only, with chain and identity validation enabled.
- Treat any capacity adjustment, guest migration, or application change as a separate decision requiring its own scope and validation.

Related pinned documentation: [homelab-operations commit 268dedb](https://github.com/APMurtha/homelab-operations/commit/268dedbfc19080340971093fe0d4e8815b93c420).
