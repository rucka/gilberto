---
name: mechanic-vault-new
description: Create a folder-note entity (`<pillar>/<slug>/<slug>.md` + `.<slug>.json` sidecar) in the gilberto vault from `anatomy/templates/<pillar>/<template>/<template>.md`. Idempotent, atomic, deterministic; use when a process or capability needs a new vault entity.
---

# mechanic-vault-new

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --pillar=<pillar> --template=<template> --slug=<slug> \
  --frontmatter='<json>' [--force]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Pillars: `me pulse projects intelligence journey network`.
- Slug/template: `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- Frontmatter: template keys + `--frontmatter`, plus `created`/`updated` (today, ISO). Mandatory `type`, `topics`; `type` = `<scope>-<role>` or `person`/`company`; types with a `### <type>` YAML schema block (`mechanic-forge-type`) or a `Fields` column in `anatomy/anatomy.md > ## Types` are checked → `INVALID_FRONTMATTER` + diff.
- Re-run with same inputs: `skipped (idempotent)`, no write. `--force`: rewrites frontmatter only (body and `created` kept).
- Writes are atomic (tmp + fsync + rename); failure rolls back → `WRITE_FAILED`.
- Errors (exit 1, nothing written): `INVALID_SLUG`, `PILLAR_NOT_FOUND`, `INVALID_PATH`, `INVALID_FRONTMATTER`, `TEMPLATE_NOT_FOUND`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
