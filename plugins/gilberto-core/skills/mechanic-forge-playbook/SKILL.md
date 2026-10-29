---
name: mechanic-forge-playbook
description: Create a per-event playbook `anatomy/playbooks/<domain>/<event>.md` (core) or `<domain>/<event>/<contributor>.md` (contributor) with validated frontmatter (event, triggers, dispatch_to, silence_learned). Idempotent, atomic, no orphan dirs, deterministic; use when a process or capability needs a new playbook.
---

# mechanic-forge-playbook

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --event=<slug> --domain=<domain> --mode=core|contributor [--contributor=<slug>] --frontmatter='{"triggers":[...],"dispatch_to":[...],"silence_learned":[...]}'
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- `domain`: `ingest structure surface act reflect next` → else `INVALID_DOMAIN` (nothing written, no folder).
- Mode is explicit: `core` → `<domain>/<event>.md`; `contributor` → `<domain>/<event>/<contributor>.md` (`--contributor` required there, rejected in core). Other files of the event are never touched; merging core + contributor is the executor's job.
- Frontmatter object: `triggers` (list of single-key objects `cron|keyword|file|event` → string), `dispatch_to` (list of skill names), `silence_learned` (list of objects, may be empty). Missing/unknown keys or bad shape → `INVALID_FRONTMATTER`. `event` is set from `--event` (if given in the object it must match). Semantic checks (does the skill exist?) are the dispatcher's.
- Body is a placeholder. Existing target path → `skipped (idempotent)`, no write.
- Slugs (`event`, `contributor`): `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- Event folder created lazily; on failure (incl. SIGINT/SIGTERM) tmp files and newly created empty dirs are removed → `WRITE_FAILED`.
- Errors (exit 1, nothing written): the codes above + `INVALID_MODE`, `REGISTRY_NOT_FOUND`, `INVALID_PATH`, `INVALID_ARGS`.
- No network, no CLI, nothing outside `$GILBERTO_ROOT`.
