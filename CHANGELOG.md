# Changelog

## v0.7.0 — Mission event timeline

- Added `GET /api/v1/mission/timeline?hours=24` to return chronological synthetic telemetry checkpoints and rule-based observations.
- Added a Mission Event Timeline panel to the dashboard.
- Added browser-local entries for simulated communication outages, queued packets, synchronization successes, and synchronization failures.
- Added local persistence for those demo actions and merged them with API-generated timeline events.
- Added backend tests for timeline sorting, invalid windows, and alert evidence.
- Preserved explicit provenance notes: API telemetry is synthetic and local communications entries are browser demo events, not real mission records.

## v0.6.0 — NASA OSDR metadata search

- Added read-only NASA OSDR study metadata search and research source links.
- Kept NASA study metadata separate from the synthetic telemetry and illustrative health rules.
