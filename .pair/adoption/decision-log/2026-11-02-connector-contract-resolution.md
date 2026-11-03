# ADL — connector contract helpers, profile resolver, unattended-write guard

**Date:** 2026-11-02
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `plugins/gilberto-core/skills/_lib/{connector,integrations}.py`, `gilberto-capability-fetch`

## Context

Story #60 implements the ADR-0003 utility contract and profile amendment. ADR/ADL leave open: error-code spelling, folder-note discovery, task-line format, guard shape.

## Decision

- **Codes**: utilities emit lowercase `auth|rate-limit|not-found|provider|profile-unresolved` (`ConnectorError`); capability-fetch keeps its uppercase per-source codes and maps `profile-unresolved` → `PROFILE_UNRESOLVED`.
- **Folder note**: `<dir>/<dir>.md` only (folder-note convention), `connectors:` flow `{p: x}` or nested block; no `connectors:` for the provider → keep walking; vault root is the stop (the root itself has no folder note).
- **Fetch target**: start path = entry `target`, else its pillar.
- **Global default**: `preferences.md > ## Integrations`, line `<provider>: <profile>` (optional `-`).
- **Guard**: `guard_write` → `allow|confirm|pending`; `send` never allowlisted (validation rejects `send` segment in `auto_write`); unattended = `GILBERTO_UNATTENDED=1`.
- **Pending task**: `- [ ] pending confirmation: <provider>:<profile> <action> — <summary>` appended idempotently to `journey/tasks.md`; D-48 registry spec absent from the repo — amend if it differs.
- **Corrupt `_state.json`**: lib helpers treat as empty; capability-fetch keeps its own `STATE_CORRUPT` per-source error (US-71 behaviour, not changed).

## Consequences

- `provider:` entries with no resolvable profile now fail `PROFILE_UNRESOLVED` (stub removed).
- Reference validation against `utility-fetch-rss` pending its merge (#72).
