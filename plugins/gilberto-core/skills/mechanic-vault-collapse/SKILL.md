---
name: mechanic-vault-collapse
description: Collapse a folder-note entity back to a file entity in the gilberto vault (`<pillar>/<name>/<name>.md` → `<pillar>/<name>.md`); refuses when the folder has other children. Idempotent, atomic, deterministic.
---

# mechanic-vault-collapse

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --path=<pillar>/<name>
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Only the folder-note (plus its `.<name>.json` sidecar, removed) inside → moves it to `<name>.md` (`updated` bumped), removes the folder. Wikilinks untouched.
- Any other child, hidden included → exit 1 `{code: "HAS_CHILDREN", children: [...]}`, nothing written (D-11).
- Already collapsed: `already collapsed`, no write, exit 0.
- Path components must match `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`; first must be a pillar → `PILLAR_NOT_FOUND`; escape → `INVALID_PATH`; `ENTITY_NOT_FOUND`; `CONFLICT` (file and folder-note both exist).
- Atomic (write new, then remove old; note restored on failure) → `WRITE_FAILED`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
