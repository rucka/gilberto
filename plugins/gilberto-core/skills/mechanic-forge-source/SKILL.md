---
name: mechanic-forge-source
description: Register an ingestion source (type, url, cadence, target pillar/topic) in `anatomy/playbooks/<pillar>/sources/<contributor>.md`. Idempotent by normalized url, file-per-contributor, atomic, deterministic; use when a process or capability needs a new source.
---

# mechanic-forge-source

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --type=<type> --url=<url> --cadence=<cadence> --target-pillar=<pillar> --target-topic=<slug> [--contributor=<slug>]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- `--contributor` defaults to `core`; a plugin passes its own name → its own file, `core.md` untouched.
- Appends a YAML fenced block keyed by url (`type`, `cadence`, `target_topic`) at the end of the file; creates file/dir when absent; existing content byte-stable.
- Dedup key: normalized url (lowercase scheme/host, lone trailing `/` stripped) → `skipped (idempotent)`, no write.
- `type`: `rss atom youtube medical oura withings google-calendar outlook-calendar icloud-calendar caldav gmail outlook-mail imap-mail apple-mail http` → else `INVALID_TYPE`.
- `cadence`: `realtime hourly daily weekly monthly` → else `INVALID_CADENCE`.
- `url`: absolute http/https, host required, no credentials/whitespace/`..` → else `INVALID_URL`.
- Slugs (`target-topic`, `contributor`): `^[a-z0-9][a-z0-9-]{0,63}$` → else `INVALID_SLUG`.
- `target-pillar`: `pulse intelligence journey`; other known pillar → `PILLAR_DOES_NOT_HOLD_SOURCES`; unknown/missing dir → `PILLAR_NOT_FOUND`.
- Writes are atomic (tmp + fsync + rename); failure rolls back → `WRITE_FAILED`.
- Errors (exit 1, nothing written): the codes above + `REGISTRY_NOT_FOUND`, `INVALID_PATH`, `INVALID_ARGS`.
- Registers only; never contacts the source. No network, no CLI, nothing outside `$GILBERTO_ROOT`.
