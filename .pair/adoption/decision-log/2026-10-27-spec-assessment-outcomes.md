# ADL — Spec assessment outcomes (grilling 2026-10-27)

**Date:** 2026-10-27
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** backlog (issues #1–#48), M1 bootstrap, skill testing

## Decisions

1. **CLI scope strict** (ADR-0001): only `install`, `update`, `status`, `plugin`. `surface`, `next`, `migrate` run via skills; migrations are one-off scripts in `tools/migrations/`.
2. **npm name**: CLI package `name: "gilberto"`.
3. **Skill paths**: `plugins/<plugin>/skills/<name>/` (ADR-0002); no `dataset/`, no changesets for plugins.
4. **Skill tests**: colocated `plugins/*/skills/*/tests/` (pytest); workspace `tools/skill-tests` exposes turbo `test` → runs in `quality-gate`; tests excluded from marketplace package.
5. **Bootstrap writes skeleton natively** (TS + `@gilberto/vault-bootstrap` templates); no dependency on Python mechanics.
6. **Schedules in M1**: plists written but not loaded; each process skill activates its job on install; `gilberto status` reports inactive jobs; hook dispatcher exits 0 with `skill not installed` when target missing.
7. **Alpha publish in M1**: `gilberto@0.x` + `@gilberto/vault-bootstrap@0.x` on npm tag `next`, enabling path A (#48) before #28.
8. **Connectors**: ADR-0003; v1 = google, media, slack.
9. **Capability coverage**: `gilberto-capability-anatomy-{topics,playbooks,preferences}` superseded by `mechanic-forge-*`; `evolution-check` in #13. Per-pillar core capabilities: #12 (`refresh-index`, `split-index`, `promote-*`, `archive-source`), #13 (`*-summarize`, `daily-link-day`, `refresh-state`), #26 (`me-update`, `network-*`, `projects-status`).
10. **Node**: matrix macOS/Linux × Node 22/24 everywhere (ADL node-baseline-22).

## References

- [ADR-0001](../tech/adr/0001-vault-self-sufficiency.md) · [ADR-0002](../tech/adr/0002-distribution-and-dual-entry-bootstrap.md) · [ADR-0003](../tech/adr/0003-connector-plugins.md)
- [anatomy file map](2026-10-27-anatomy-file-map.md)
