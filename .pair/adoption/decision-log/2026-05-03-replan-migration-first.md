# ADL: Replan — Migration-First Ordering of Initiatives

- **Date**: 2026-05-03
- **Status**: Accepted
- **Type**: non-architectural
- **Source**: in-session re-prioritization (post `/pair-process-plan-initiatives`)

## Decision

The 4-initiative layer-first plan (created 2026-05-02) is replaced by a **5-initiative migration-first** sequence:

1. **#1 Foundation (slim)** — minimum viable monorepo + CLI + bootstrap + vault skeleton (lifecycle processes deferred to #5)
2. **#2 Intelligence Migration** — pillar `intelligence` operational + `my-intelligence` topic content migrated
3. **#3 Pulse + Ratko Integration** — plugin protocol + 2 plugins (`pulse-health-tracking`, `pulse-ratko`) + Ratko-app integration contract + `ratko-mvp` KB migration
4. **#4 Content Authoring Plugins** — `projects-venture` + `projects-editorial` plugins + `cm-*` / `publishing-*` migration; closes `my-intelligence` dismissal
5. **#5 Distribution + Lifecycle + Calendar/Mail** — original Phase-4 scope + lifecycle processes from former Phase 2

Each migration step (#2, #3, #4) closes a chunk of legacy repo. By end of #4 both `my-intelligence` and `ratko-mvp` KB are dismissed.

## Rationale

- **Reduces parallel-repo cost** — each migration step closes a legacy entry; no long tail of two parallel KB repos
- **Forces ergonomic validation** — framework dogfooded against real KB content from week ~4 onward, not at week 21+
- **Protects v1.0 timeline** — heavy lifting (plugin protocol + integrations) happens with concrete migration constraints, not abstract requirements
- **Defers polish appropriately** — distribution surface, brand, lifecycle robustness move to the end where they are most valuable and least churn-prone

## Implications

- **PRD §10** updated: 4 phases → 5 phases (~22-30 weeks total)
- **PRD §8 Constraints**: time budget revised 200-240 → 220-260 dev-days
- **GitHub Initiatives** rewritten: `#2` retitled "Intelligence Migration", `#3` "Pulse + Ratko Integration", `#4` "Content Authoring Plugins", `#5` created "Distribution + Lifecycle + Calendar/Mail"
- **Plugin protocol** is no longer a dedicated initiative — introduced in #3 (first plugin = `pulse-ratko`)
- **Lifecycle processes** (`vault-upgrade`, `vault-migrate`, `vault-export`, `vault-archive`) moved from #2 to #5
- **Calendar/Mail integration** stays in #5 (no change)
- **Ratko-app integration contract** is an Epic of Initiative #3 (not committed adoption), with draft spec in `_docs/specs/ratko-app-contract.md` (working dir, gitignored). Ratko-app modifications (HTTP API + skill conversion from filesystem writes) tracked in `ratko-mvp` repo, coordinated with this Initiative.

## Alternatives Considered

- **Keep 4-initiative layered order**: rejected — defers migration too late; prolongs parallel-repo cost
- **Single migration initiative covering all three legacy clusters**: rejected — too coarse; blocks incremental dogfooding and risks delaying content-authoring work behind pulse work
- **Migrate before introducing plugin protocol**: rejected — `pulse-ratko` is a plugin by design; migrating without protocol means double work

## References

- [`../product/PRD.md`](../product/PRD.md) §10
- Initiatives: [#1](https://github.com/rucka/gilberto/issues/1), [#2](https://github.com/rucka/gilberto/issues/2), [#3](https://github.com/rucka/gilberto/issues/3), [#4](https://github.com/rucka/gilberto/issues/4), [#5](https://github.com/rucka/gilberto/issues/5)
- [`../tech/way-of-working.md`](../tech/way-of-working.md) §Hierarchy
