---
name: mechanic-forge-topic
description: Register a topic in `anatomy/topics.md` and optionally seed folder-notes `<pillar>/<topic>/<topic>.md` (+ `pulse/<topic>/history/`). Idempotent, atomic, deterministic; use when a process or capability needs a new vault topic.
---

# mechanic-forge-topic

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --slug=<slug> [--seed=<pillar>[,<pillar>...]] [--description=<text>]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Slug: `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`; not a pillar name nor `anatomy` → else `RESERVED_NAME`.
- `--seed`: pillars from `me pulse projects intelligence journey network` (default none) → else `INVALID_SEED_PILLAR`; pillar folder missing → `PILLAR_NOT_FOUND`.
- Seed note from `anatomy/templates/<pillar>/topic/topic.md` (`{{SLUG}}`/`{{TITLE}}`/`{{DATE}}`) or a built-in default; existing notes are never overwritten.
- Registry row appended to the `anatomy/topics.md` table as the last write; other content byte-stable.
- Re-run with same inputs: `skipped (idempotent)`, no write.
- Writes are atomic (tmp + fsync + rename); failure or SIGINT rolls back (no registry entry, orphan note or tmp file) → `WRITE_FAILED`.
- Errors (exit 1, nothing written): `INVALID_SLUG`, `RESERVED_NAME`, `INVALID_SEED_PILLAR`, `PILLAR_NOT_FOUND`, `REGISTRY_NOT_FOUND`, `INVALID_PATH`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
