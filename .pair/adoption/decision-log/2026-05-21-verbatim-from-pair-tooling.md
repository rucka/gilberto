# ADL — Verbatim-from-pair as Source of Truth for `tools/*`

**Date:** 2026-05-21
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `tools/eslint-config`, `tools/prettier-config`, `tools/markdownlint-config`, `tools/ts-config`

## Context

`foomakers/pair` is the reference monorepo gilberto bootstraps from. Its `tools/*` packages already encode lint/format/typecheck conventions that have been battle-tested across pair workspaces. Re-deriving each preset risks drift and bikeshedding.

## Decision

`tools/*` configuration is **verbatim-copied** from `foomakers/pair/tools/*`, with the single mechanical adaptation of renaming the npm scope `@pair/` → `@gilberto/`. The pair source remains canonical: when pair updates a preset, gilberto pulls the change rather than diverging.

### Permitted deviations from verbatim

- **Namespace rename** (`@pair/*` → `@gilberto/*`) — required to publish in the gilberto org.
- **Language of in-code comments** — pair has Italian comments; gilberto enforces English-only artifacts (per memory + CLAUDE.md). Translation is required, not a deviation.
- **Documentation references** (READMEs, comments naming the project) — gilberto-specific text replaces pair-specific text.
- **Files unused under ESLint 9 flat-config** (e.g. `.eslintignore`) — may be dropped if functionally dead.

### Explicit deviation from story AC: `eslint-config-prettier` omitted

Story #32 §Edge Cases and §T-3 dependencies prescribe `eslint-config-prettier` to disable ESLint formatting rules conflicting with Prettier. Pair's `eslint.config.cjs` does not use it. Verbatim-from-pair wins.

Safety verification (2026-05-21): `grep -E "prefer-arrow|indent|quotes|semi|comma|space" tools/eslint-config/eslint.config.cjs` returns no matches. Pair's rule set is purely code-quality (`complexity`, `max-depth`, `max-lines-per-function`, `max-params`, `@typescript-eslint/no-explicit-any`, `prefer-const`, `no-var`, `no-throw-literal`) plus the `@typescript-eslint/recommended` and `eslint:recommended` rule packs. None of these enable stylistic rules that Prettier would override. Conflict surface = empty.

## Consequences

### Positive

- Zero drift between pair and gilberto for shared tooling.
- Updates propagate by `cp` from pair, not by re-design.
- Story AC-7's "self-validate" check can be expressed as a script in each `tools/*/package.json` referencing only the verbatim files.

### Negative

- Story AC-7 cannot be read literally: pair's `tools/*` do not ship `ts:check` scripts of the exact form the story specified. Mitigated by adding minimal `ts:check` scripts that load each config and assert it parses, without modifying the verbatim config content.
- Story §Edge Cases #2 (eslint-config-prettier) is overridden by this ADL. Any future ESLint rule additions that introduce stylistic rules must re-validate the conflict surface and reconsider `eslint-config-prettier`.
- Italian comments in pair's `eslint.config.cjs` must be translated. The translation is a one-time cost and not propagated back upstream.

## When to revisit

- Pair adds `eslint-config-prettier` (re-sync).
- Pair adds stylistic ESLint rules (re-validate conflict surface; consider adding `eslint-config-prettier` regardless of pair).
- gilberto needs a rule pair doesn't have (then the decision shifts from verbatim-from-pair to deliberate divergence per-rule).

## References

- Story: rucka/gilberto#32
- PR: rucka/gilberto#50
- Pair source: `foomakers/pair/tools/{eslint-config,prettier-config,markdownlint-config,ts-config}/`
- Guidelines re: eslint-config-prettier: `.pair/knowledge/guidelines/code-design/quality-standards/eslint.md` §Conflicting Rules; `.pair/knowledge/guidelines/code-design/quality-standards/prettier-formatting.md` §Conflict Resolution
