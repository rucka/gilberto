# ADL: Project Categorization — Type A (Pet / Proof of Concept)

- **Date**: 2026-05-02
- **Status**: Accepted
- **Type**: non-architectural
- **Source**: `/pair-process-bootstrap` Phase 1

## Decision

Project is categorized as **Type A — Pet Project / Proof of Concept** per the bootstrap-checklist taxonomy.

## Evidence (PRD)

- Single contributor (Gianluca Carucci); 200-240 dev-days budget to v1.0
- Zero paid services for v1.0 (free tiers / user-owned tooling only)
- Single-user / single-vault; max ~10K markdown files; no multi-tenant
- No compliance scope (GDPR/SOC2/HIPAA out of scope)
- Local-first deployment, no cloud backend
- Pivot criteria at 6 months post-v1.0 (PRD §13)

## Implications

- Architecture: **modular monolith** (single CLI deployable, modular via plugin protocol)
- Methodology: **Kanban** (continuous flow, no fixed sprints)
- Quality gates: minimal standard pipeline (type-check + lint + test + format)
- Release cadence: on-demand via tags + Changesets
- Risk management: lightweight (P0/P1/P2 prioritization, single-developer focus)

## References

- `.pair/knowledge/assets/bootstrap-checklist.md#project-categorization`
- `.pair/adoption/product/PRD.md` §4, §5, §8, §13
