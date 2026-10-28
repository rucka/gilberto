---
name: mechanic-vault-promote
description: Promote a file entity to a folder-note entity in the gilberto vault (`<pillar>/<name>.md` → `<pillar>/<name>/<name>.md`), name preserved so wikilinks keep resolving. Idempotent, atomic, deterministic; use when a note needs sub-content.
---

# mechanic-vault-promote

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --path=<pillar>/<name>.md
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Moves the note into `<name>/<name>.md`; content and frontmatter unchanged except `updated` (today). Wikilinks and other files are never touched (no backlink rewrite).
- Already promoted: `already promoted`, no write, exit 0.
- Every path component must match `^[a-z0-9][a-z0-9-]{0,63}$` (`.md` on the last) → else `INVALID_SLUG`; first component must be a pillar → `PILLAR_NOT_FOUND`; real path escaping the vault → `INVALID_PATH`.
- `ENTITY_NOT_FOUND`: neither file nor folder-note exists. `CONFLICT`: both exist (nothing written).
- Atomic (tmp + fsync + rename); failure rolls back the created folder → `WRITE_FAILED`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
