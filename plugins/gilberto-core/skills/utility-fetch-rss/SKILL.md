---
name: utility-fetch-rss
description: Fetch an RSS/Atom feed by URL and write one Markdown file per new item to `$GILBERTO_ROOT/_ingest/intelligence/` with canonical frontmatter. Incremental (`_state.json`), idempotent, atomic; use when a process needs feed items captured into the ingest inbox.
---

# utility-fetch-rss

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --url=<http(s) feed url> [--profile=<provider>:<profile>]
```

Vault root: `$GILBERTO_ROOT`. stdout JSON `{items:[{id,path}]}` (new items only; files already written, `path` vault-relative; `gilberto-capability-fetch` accepts `{id,path}` and does not rewrite them) or `{errors:[{code}]}` (exit 1); prose on stderr. Reference implementation of the ADR-0003 utility contract (`_lib/connector`).

- Requires `feedparser` (`pip install -r plugins/gilberto-core/requirements.txt`).
- URL checked with `_lib/url_validate` before any network call.
- Fetch: 15 s timeout, retry + backoff (`_lib/connector.retry`). HTTP 404/410 → `not-found`, 429 → `rate-limit`, other failures → `provider`. Malformed feed with zero entries → `provider`; with entries → proceeds.
- Item id: feed `guid`, else link, else hash of title+summary. Date: published/updated, else today (UTC).
- Output `_ingest/intelligence/<date>-<slug(title)>-<hash8(id)>.md` (slug falls back to link, then `item`). Never overwrites an existing file.
- Frontmatter: `type` (`intelligence-source`), `source` (item link, else feed URL), `created` (item date), `title`, `source_profile` only when `--profile` is given. Body: `# title`, item HTML reduced to Markdown (links kept), `[Source](link)`.
- State: `_ingest/intelligence/.fetch-rss/_state.json` (`{url: {fetched: [ids]}}`). Re-run writes only unseen ids. State is saved only after every file write succeeds; a write failure removes the files it created. Missing/corrupt state → empty, logged.
- Errors (exit 1, nothing written): `INVALID_URL`, `INVALID_ARGS`, `INVALID_PATH` (`GILBERTO_ROOT` unset), `not-found`, `rate-limit`, `provider`.
- Writes only inside `$GILBERTO_ROOT/_ingest/intelligence/`; no secrets.
- `gilberto-process-ingest` scans `_ingest/` and `_ingest/intelligence/` (names `intelligence/<file>`), so output is accepted unchanged.
- `--profile` (when given, even empty) is validated before any fetch: invalid → exit 1 `provider`.
