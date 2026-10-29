---
name: mechanic-forge-relationship-level
description: Register a people-relationship level (name + criteria) under `anatomy/anatomy.md > ## Relationship levels`. Idempotent by name, order-stable, atomic, deterministic; use when a process or capability needs a new relationship level.
---

# mechanic-forge-relationship-level

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --name=<slug> --criteria="<text>"
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Appends after the last level: `- <name> — <criteria>`; when the section holds a table (seed layout), a `| name | criteria |` row. Existing entries and other sections byte-stable.
- Dedup key: `name` → `skipped (idempotent)`, no write (criteria not updated).
- `name`: `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`; `criteria` non-empty → else `INVALID_CRITERIA`.
- Writes are atomic (tmp + fsync + rename); failure rolls back → `WRITE_FAILED`.
- Errors (exit 1, nothing written): the codes above + `REGISTRY_NOT_FOUND` (file or section missing), `INVALID_PATH`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
