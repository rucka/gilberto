---
name: gilberto-capability-fetch
description: Pull external content for every registered source in `anatomy/playbooks/<pillar>/sources/*.md`. Routes each entry by `provider:` (else `type`) to a connector utility, passes `profile:`, falls back to MCP or a manual `_ingest/` hint, writes only `_ingest/` and `_state.json`; idempotent. Use when a process needs fresh external items.
---

# gilberto-capability-fetch

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" [--pillar=<pillar>] [--source=<contributor|url>]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr. Exit 1 when any source failed (others still ran).

- Loads every YAML entry (`"<url>"` JSON-decoded when quoted: {type, provider?, profile?, fallback?, ...}`) of `anatomy/playbooks/*/sources/*.md`. Missing/empty `sources/` → no-op success. Filters: `--pillar` = pillar, `--source` = contributor (file stem) or url.
- Route: `provider:` wins, else `type`. Utility = `utility-<key>-read` (`rss`/`atom` → `utility-fetch-rss`, `http` → `utility-download-html`), searched in this skills dir then `$GILBERTO_UTILITY_PATH` (`:`-separated skill dirs of installed connector plugins). No provider code in core.
- Call: `script.py --url=<url> [--profile=<profile>]` with `GILBERTO_ROOT` set. Entry `profile:` passed through; omitted → resolver of #60 (stub: no profile until it lands). Utility stdout: `{"items":[{"id","markdown"}]}`; on failure exit ≠ 0 and `{"errors":[{"code"}]}`.
- Utility unavailable → `fallback:` (entry, else integration frontmatter `anatomy/integrations/<provider>/<profile|default>.md`, flat `<provider>.md` as compat, default `none`): `mcp` → `skipped` entry `reason: mcp-fallback` (+ provider, profile, url, utility) — the assistant then reads via its MCP connector; `none` → `skipped` entry `reason: manual` with a hint to drop content into `_ingest/`.
- Items → `_ingest/<contributor>-<sha1(url,id)[:12]>.md`. State `anatomy/playbooks/<pillar>/sources/<contributor>/_state.json`: `{url: {fetched: [ids]}}`; fetched ids → `skipped` `reason: already-fetched`, nothing rewritten. Writes atomic; nothing outside `_ingest/` and `_state.json`.
- Status: `ok`; `skipped` (nothing new); `partial` (some errors); `error` (only errors).
- Per-source errors (exit 1, others continue): `MALFORMED_ENTRY`, `UNKNOWN_PROVIDER`, `UNKNOWN_TYPE`, `INVALID_FALLBACK`, `UTILITY_ERROR` (+ `utility`, `utility_code`), `STATE_CORRUPT`, `WRITE_FAILED`. Global (exit 1): `INVALID_ARGS`, `INVALID_PATH`.
- Never contacts a source itself; only utilities do.
