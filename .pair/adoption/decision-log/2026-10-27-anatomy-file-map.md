# ADL — Anatomy file map

**Date:** 2026-10-27
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `packages/vault-bootstrap` seed, `mechanic-*` skills, bootstrap wizard (#45)

## Context

Issues #9, #10, #11, #42, #43 placed the same registries in different files (`anatomy/types.md` vs `anatomy.md > ## Types`, `preferences.md > Sources` vs `playbooks/<pillar>/sources/`, `registries.md`). One map is needed before seeding and mechanics.

## Decision

| Registry            | Location                                                     | Writer                      |
| ------------------- | ------------------------------------------------------------ | --------------------------- |
| Structure rules     | `anatomy/anatomy.md`                                         | manual, `mechanic-vault-*`  |
| Entity types        | `anatomy/anatomy.md > ## Types`                              | `mechanic-forge-type`       |
| Relationship levels | `anatomy/anatomy.md > ## Relationship levels`                | `mechanic-forge-relationship-level` |
| Topics              | `anatomy/topics.md`                                          | `mechanic-forge-topic`      |
| Plugins             | `anatomy/plugins.md`                                         | CLI `plugin *`, plugin install |
| Scopes              | `anatomy/scopes.md` (registry, private, storage mode, accounts) — [ADR-0004](../tech/adr/0004-scopes.md) | `mechanic-forge-scope` |
| Identity / system   | `anatomy/gilberto.md`                                        | bootstrap                   |
| Preferences         | `anatomy/preferences.md` (`## Silence`, `## Thresholds`, `## Cadences`, global `## Integrations` switches) | manual, reflect/evolve |
| Integrations        | `anatomy/integrations/<provider>.md` (non-secret config)     | connector setup             |
| Sources             | `anatomy/playbooks/<pillar>/sources/<contributor>.md`        | `mechanic-forge-source`     |
| Playbooks           | `anatomy/playbooks/<domain>/<event>.md`                      | `mechanic-forge-playbook`   |
| Templates           | `anatomy/templates/<pillar>/<name>/`                         | `mechanic-forge-template`   |

- No `registries.md`, no `types.md`. Section names in English.
- Secrets never in anatomy (ADR-0003).

## References

- [ADR-0001](../tech/adr/0001-vault-self-sufficiency.md) · [ADR-0003](../tech/adr/0003-connector-plugins.md)
