---
name: mechanic-forge-template
description: Create a template folder `anatomy/templates/<pillar>/<name>/{template.md, files/}` with `{{SLUG}}`/`{{TITLE}}`/`{{DATE}}` placeholders. Idempotent, atomic, deterministic; use when a process or capability needs a new entity template.
---

# mechanic-forge-template

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --name=<name> --pillar=<pillar> [--description=<text>]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Name: `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- Pillar: `me pulse projects intelligence journey network` → else `INVALID_PILLAR` + supplied value.
- Writes `template.md` (frontmatter `scope` + `description`) and `files/note.md` (placeholders); existing files are kept, missing ones created.
- Re-run with same inputs: `skipped (idempotent)`, no write.
- Writes are atomic (tmp + fsync + rename); failure rolls back → `WRITE_FAILED`.
- Errors (exit 1, nothing written): `INVALID_SLUG`, `INVALID_PILLAR`, `INVALID_PATH`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
