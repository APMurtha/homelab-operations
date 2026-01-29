
---

# 3️⃣ Runbook: Telemetry retention policy

📁 **`runbooks/telemetry-retention-policy.md`**

```markdown
# Telemetry Retention Policy

## Scope

Defines retention limits for observability data produced by the homelab
telemetry stack running on `minas-tirith`.

This policy applies to:
- Prometheus metrics
- Loki logs

It explicitly does not cover future SIEM or security event storage.

## Design Goals

- Prevent silent disk exhaustion
- Maintain sufficient short-term visibility for troubleshooting
- Keep observability storage lightweight and disposable
- Prepare clean separation from future security logging

## Prometheus

### Configuration

- Storage path: `/prometheus`
- Retention time: 7 days
- Retention size: 2GB

### Rationale

Metrics are primarily used for:
- Trend awareness
- Short-term diagnostics
- Alert evaluation

Older data provides diminishing value in a homelab context.

## Loki

### Configuration

- Retention period: 7 days
- Compactor enabled
- Filesystem-backed deletion

### Rationale

Logs are used for:
- Recent troubleshooting
- Correlation with metrics and alerts

They are not treated as long-term records or evidence.

## SIEM Considerations

When a SIEM platform is introduced:
- Security logs will be duplicated or redirected
- Retention requirements will differ
- Telemetry retention should remain unchanged

## Review

Retention values should be revisited if:
- Disk capacity changes significantly
- Telemetry scope expands
- SIEM replaces parts of the current stack
