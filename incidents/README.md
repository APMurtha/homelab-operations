# 🚨 Incidents

This directory contains **incident reports** documenting unplanned outages,
service degradation, or instability events that required investigation and
corrective action.

Incidents are written to capture:
- what happened
- user and system impact
- root cause
- resolution
- preventive measures

The goal is **learning and prevention**, not blame.

---

## Scope

An incident is recorded when an event:
- caused loss of service or connectivity
- required manual intervention to recover
- revealed architectural or configuration weaknesses
- resulted in corrective or preventive changes

Planned changes belong in `changelog/`.  
Repeatable procedures derived from incidents may later be promoted to
`runbooks/`.

---

## Conventions

- **One incident per file**
- Filenames use the format:

  `YYYY-MM-DD-short-description.md`

- Incident reports should include, where applicable:
  - Summary
  - Impact
  - Timeline
  - Detection
  - Root Cause
  - Resolution
  - Preventive Actions
  - Lessons Learned
  - Status

Not all sections are required for every incident, but consistency is preferred.

---

## Philosophy

Incident documentation is treated as an **operational asset**.
Clear, honest reporting improves future stability and reduces time-to-recovery
for similar events.

## Relationship to Other Documentation

Incidents often occur as a result of intentional changes.

When applicable:
- The **initiating change** is documented in `changelog/`
- The **outage or instability** is documented here in `incidents/`
- The **repeatable recovery procedure** is captured in `runbooks/`

This separation ensures that:
- architectural intent
- operational impact
- and corrective actions

are each documented clearly and without duplication.
