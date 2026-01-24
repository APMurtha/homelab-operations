# 2026-01-24 — AirVPN WireGuard NYC Endpoint Healthcheck Failures

## Summary
The VPN gateway container (`gluetun`) experienced repeated startup healthcheck failures when pinned to specific AirVPN WireGuard servers in the New York City region. The VPN tunnel established successfully, but DNS resolution failed during gluetun’s startup checks, preventing the container from reaching a healthy state.

## Impact
- VPN container remained in `health: starting` state
- Downstream services dependent on VPN egress were disrupted:
  - `seedboxapi` entered a restart loop
  - Tracker automation temporarily unavailable
- Manual intervention required to restore stable VPN connectivity

## Timeline
- **T0:** Gluetun configuration updated to pin NYC WireGuard servers (`Haedus`, `Iklil`, `Lich`)
- **T+Minutes:** VPN tunnel established, but container healthcheck failed
- **T+Minutes:** Health endpoint reported DNS lookup timeouts (`github.com`, `cloudflare.com`)
- **T+Minutes:** Multiple NYC servers tested with identical failure behavior
- **T+~1 hour:** Reverted to US auto-selection; health immediately restored
- **T+~1.5 hours:** Identified stable WireGuard server (`Fang`, Chicago) via active endpoint mapping
- **Recovery:** VPN pinned to known-good server and dependent services restored

## Detection
The issue was detected by:
- Docker reporting `gluetun` as `health: starting`
- Repeated healthcheck exit code 8
- Explicit `/health` endpoint returning DNS timeout errors
- Restart loop observed in `seedboxapi`

## Root Cause
Provider-side endpoint instability affecting DNS egress on specific AirVPN WireGuard servers in the New York City region. Although the WireGuard tunnel established correctly, outbound DNS resolution failed during gluetun’s startup health checks, preventing the container from becoming healthy.

The issue was isolated to specific pinned endpoints and did not occur when using automatic US server selection.

## Resolution
- Removed region-based server pinning
- Identified the active, stable WireGuard endpoint via connection logs
- Mapped endpoint IP to AirVPN `server_name` using gluetun server metadata
- Pinned VPN configuration to known-good server (`Fang`, Chicago)
- Recreated MAM session using ASN lock and Dynamic Seedbox API permissions
- Verified VPN health, IP stability, and downstream service functionality

## Preventive Actions
- Prefer pinning to **verified healthy server names** rather than geographic assumptions
- Use gluetun healthchecks as authoritative indicators of endpoint viability
- Document provider endpoint anomalies for future reference
- Retain ASN-based tracker sessions to tolerate minor IP changes

## Lessons Learned
- Geographic proximity does not guarantee endpoint reliability
- VPN tunnels can appear “up” while still failing functional health checks
- Healthcheck failures are often early indicators of upstream provider issues
- Server-name pinning based on observed behavior is more reliable than city-based selection

## Status
Resolved. Service stable with pinned WireGuard server. No recurrence observed.
