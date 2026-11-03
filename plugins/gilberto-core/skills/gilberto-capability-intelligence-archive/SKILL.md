---
name: gilberto-capability-intelligence-archive
description: Archive an entity at `intelligence/<topic>/<source>/<entity>.md` from an entity template (frontmatter `type, topics, created, updated`, `tags?`). Composes `mechanic-vault-new` (`--path`); idempotent, never overwrites, unknown topic → `_uncategorized/`. Use to file intelligence content.
---

# gilberto-capability-intelligence-archive

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --topic=<topic> --source=<source> --entity=<entity> --template=<template> \
  [--frontmatter='<json>'] [--confirm-topic] [--confirm-source]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Slugs (topic, source, entity, template): `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- Template: `anatomy/templates/intelligence/<template>/<template>.md`. Frontmatter = template keys + `--frontmatter` (`tags` optional, `topics` defaults to `[<topic>]`) + `created`/`updated`; validated like `mechanic-vault-new` (`INVALID_FRONTMATTER`, `TEMPLATE_NOT_FOUND`). Index refresh out of scope.
- Same path + same content (frontmatter minus `created`/`updated`, body): `skipped (idempotent)`. Different content: `CONFLICT`, no overwrite.
- Topic registered in `anatomy/topics.md`? else:
  - interactive: ask the user; yes → re-run with `--confirm-topic` (uses the topic as given); no → re-run as is.
  - default (non-interactive, e.g. ingest): placed under `intelligence/_uncategorized/<source>/`, `topics: []`.
- Source known = `anatomy/playbooks/intelligence/sources/<source>.md` or existing `intelligence/<topic>/<source>/`. Unknown → `SOURCE_UNCONFIRMED`, nothing written; ask the user, re-run with `--confirm-source`. Never silent.
- Writes atomic, rolled back on failure → `WRITE_FAILED`. Errors: exit 1, nothing written.
- Dispatch: `gilberto-process-ingest` finds this skill as `gilberto-capability-intelligence-archive`; result JSON is the mechanic contract above.
