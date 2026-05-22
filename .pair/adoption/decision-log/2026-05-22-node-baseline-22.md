# ADL — Node.js ≥22 LTS as the runtime baseline

**Date:** 2026-05-22
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** repo-wide — `package.json` `engines`, CI runners, distribution test matrix

## Context

- Node 20 entered Maintenance LTS on 2025-10-21 and reached End-of-Life on 2026-04-30. After EOL, upstream security patches stop landing.
- Node 22 is Active LTS (since 2024-10-29; scheduled EOL 2027-04-30) and is the current default LTS line.
- Node 24 is Current (released 2025-04) and is the next LTS candidate (Active LTS expected 2025-10).
- gilberto is pre-v1, single-contributor, and currently has no shipped artifacts depending on any specific runtime API surface. The cost of bumping the baseline is near-zero today; the cost of carrying a past-EOL baseline grows as transitive dependencies drop Node 20 support.

## Decision

**The gilberto baseline is Node.js ≥22.12.0 LTS.**

### What this means in practice

- `package.json` `engines.node` = `">=22.12.0"`.
- CI runs `ubuntu-latest` + Node 22 (single job for v0.x; matrix deferred to Initiative #5 — see [story #35](https://github.com/rucka/gilberto/issues/35) Business Rules).
- The future distribution test matrix (Initiative #5 / `distribution-onboarding`) targets **macOS/Linux × Node 22/24** — drops Node 20, adds Node 24 to validate the next-LTS surface ahead of its LTS promotion.
- Workflow runners pin `actions/setup-node@v4` to `node-version: 22`.
- pnpm continues pinned via Corepack at `10.33.2`.

## Consequences

### Positive

- Aligned with the current Active LTS — upstream security and bugfix coverage guaranteed.
- Future dependency bumps (e.g. ESM-only packages, Node-built-in features such as the built-in test runner and glob) land without baseline contortions.
- Distribution matrix (Initiative #5) tests against the **next** LTS candidate (Node 24), keeping forward-compatibility visible.

### Negative

- Users still on Node 20 must upgrade before installing gilberto. Acceptable: Node 20 is past EOL upstream; staying on it is itself a security risk for any environment.
- A future bump (22 → 24) will require revisiting this ADL and the distribution matrix.

## When to revisit

- **Node 22 → Maintenance LTS (2025-10-21 transition is past — review at 2026-10).** No action required from a baseline POV; verify catalog versions of `@types/node` track 22.x.
- **Node 24 promoted to Maintenance LTS (~2027-04).** Consider bumping the baseline to ≥24 LTS and shifting the distribution matrix to Node 24/26.
- **Node 22 EOL (2027-04-30).** Must bump.
- **A dependency drops support for Node 22.** Re-evaluate sooner.

## References

- Story: [rucka/gilberto#35](https://github.com/rucka/gilberto/issues/35)
- PR: [rucka/gilberto#53](https://github.com/rucka/gilberto/pull/53)
- [`tech-stack.md`](../tech/tech-stack.md) §Languages, §Tooling
- [`PRD.md`](../product/PRD.md) §11 Risk Mitigation
- [`distribution-onboarding.md`](../product/subdomain/distribution-onboarding.md) §Complexity Assessment
- Node.js release schedule: <https://github.com/nodejs/release#release-schedule>
