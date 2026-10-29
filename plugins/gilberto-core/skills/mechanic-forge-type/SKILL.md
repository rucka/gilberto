---
name: mechanic-forge-type
description: Define an entity type (`<scope>-<name>` or `person`/`company`) with a `required`/`optional` schema under `anatomy/anatomy.md > ## Types`. Idempotent, structured `--merge`, atomic, deterministic; use when a process or capability needs a new entity type.
---

# mechanic-forge-type

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --name=<name> [--scope=<scope>] --schema='{"required":[...],"optional":[...]}' [--merge]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose (incl. merge diff) is on stderr.

- Composite type `<scope>-<name>`; scope in `anatomy pillar me pulse projects project intelligence journey network` → else `INVALID_SCOPE`. `person`/`company` take no `--scope`.
- Name/scope slug: `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- Schema: JSON object; `required` mandatory array of strings, optional `optional` array, no other keys → else `INVALID_SCHEMA`.
- Appends `### <type>` + YAML fenced block at the end of `## Types`; existing content byte-stable.
- Existing type: identical schema → `skipped (idempotent)`; different without `--merge` → `TYPE_CONFLICT` (existing + supplied); with `--merge` → union of keys, existing order kept, new appended, a key now required leaves `optional`.
- Writes are atomic (tmp + fsync + rename); failure rolls back → `WRITE_FAILED`.
- Errors (exit 1, nothing written): `INVALID_SLUG`, `INVALID_SCOPE`, `INVALID_SCHEMA`, `TYPE_CONFLICT`, `REGISTRY_NOT_FOUND`, `INVALID_PATH`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
