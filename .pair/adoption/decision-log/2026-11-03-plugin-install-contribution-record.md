# ADL — Plugin install contribution record

**Date:** 2026-11-03
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `gilberto plugin install|remove` (#100)

## Decision

- Install writes `anatomy/.plugins/<name>.json` = `{ files: { <vault-rel path>: sha256 } }`; `remove` deletes exactly those files, keeps ones whose hash changed (unless `--purge`).
- `plugins.md` row: `name | manifest version (default 0.0.0) | install date (YYYY-MM-DD)`.
- Templates need `gilberto.pillar`; each template path is a dir installed to `anatomy/templates/<pillar>/<basename>/`.
- Bundled root = repo `plugins/` resolved from the CLI module; override with env `GILBERTO_PLUGINS_DIR`.
- Symlinks in contributions and unsafe names/keys are refused.

## Consequences

- Published CLI `files` does not yet ship `plugins/`: bundled install works from a repo checkout only (follow-up: packaging).
