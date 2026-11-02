# ADL — Release process aligned with pair

**Date:** 2026-11-02
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `.changeset/`, `.github/workflows/{version,release}.yml`, `scripts/{release-plan,publish,release-check}.js`, plugin manifests, bootstrap skill `requires`

## Context

The alpha pipeline used Changesets pre mode (`next`) and a push-triggered `version.yml` opening a version PR on any `.changeset/**` change. foomakers/pair releases dispatch-only with `pre` / `rc` / `final` channels. The bootstrap skill requires `gilberto@>=0.1.0 <2`, which strict SemVer does not satisfy with a prerelease (`0.1.0-next.0`).

## Decision

- **A merge never releases.** `version.yml` and `release.yml` are `workflow_dispatch`-only. `version.yml` (channel `pre|rc|final`, optional base `version`) runs `changeset version`, computes the version with `scripts/release-plan.js`, commits, tags, then dispatches `release.yml` with the tag (two runs, shared `release` concurrency).
- **Changesets pre mode exited** (`pre.json` removed; `release-check.js` fails if it returns). Suffix `-<channel>.N` is derived from git tags. Channels forward-only (`pre` → `rc` → `final`), skippable; base must be above the last final.
- **pre/rc**: ephemeral commit, tag-only push, npm dist-tag `next`, GitHub prerelease; must not move an existing `latest`. **final**: version commit + CHANGELOG on `main`, tag, npm `latest`, GitHub latest release.
- **Every user-facing PR carries a changeset**; changesets accumulate on `main` until a final consumes them.
- **Plugin manifests carry no `version`** (pair's marketplace ADL): Claude Code falls back to the commit SHA, so a hand-kept number never strands users.
- **Skill range `>=0.1.0-0 <2`**: admits the `0.1.0` pre/rc ladder in strict SemVer, matching the skill's parser (compares `X.Y.Z`, ignores suffix). The npx fallback and upgrade use the same range as spec (`gilberto@>=0.1.0-0 <2`), not `@latest`: npm picks `latest` when it satisfies, else the newest matching pre/rc on `next` — one source of truth for channel and requirement.

### Adapted from pair, not copied

- pre/rc go to npm `next`, not GitHub Packages: `gilberto` is unscoped and cannot live on GitHub Packages; a single registry also keeps `npx gilberto@next` public.
- No cleanup job (deleting pre/rc tags/package versions): npm forbids unpublish-reuse; prereleases stay.
- No TS release state module / `pnpm release` CLI: one ~40-line pure planner, tested in `release-contract.test.ts`.
- No manual ZIP / KB artifacts, no website deploy (none exists yet).

## Alternatives Considered

- **Keep pre mode `next`**: rejected — suffix `next.N` has no rc stage, version PR noise on every changeset.
- **Keep range `>=0.1.0 <2`**: rejected — strict SemVer rejects the very prereleases used to test the skill end to end.

## Consequences

- First release ever: npm sets `latest` on first publish whatever the tag, so a first `pre` lands on `latest` too (accepted; the next `final` moves it).
- Final version commit is pushed by `github-actions[bot]`; future `main` protection needs a bot bypass.

## References

- foomakers/pair `RELEASE.md`, ADL `2026-10-14-release-is-dispatched-with-a-changeset-per-pr`, ADL `2026-07-28-marketplace-plugin-packaging` (Decision 4)
- [ADL npm scope foomakers](2026-10-29-npm-scope-foomakers.md)
