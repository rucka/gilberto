---
name: utility-download-html
description: Download a web article by URL and write its main content as clean Markdown (no nav/chrome/footer/ads) to `$GILBERTO_ROOT/_ingest/<slug>.md` with canonical frontmatter. Idempotent, atomic; use when a process needs a web page captured into the ingest inbox.
---

# utility-download-html

Run, never reimplement:

```bash
python3 "$(dirname "$0")/script.py" --url=<http(s) url> [--force]
```

Vault root: `$GILBERTO_ROOT`. Surface the stdout JSON `{status, written, skipped, errors}` as-is; prose is on stderr.

- Requires `trafilatura` (`pip install -r plugins/gilberto-core/requirements.txt`). Static HTML only: no browser/JS rendering.
- URL checked with `_lib/url_validate` before any network call; hosts resolving to private/loopback/link-local/reserved addresses (also via redirects) → `INVALID_URL`.
- Fetch: 15 s timeout, 5 MB cap, 2xx and `text/html`/`application/xhtml+xml` only.
- Output `_ingest/<slug>.md`: frontmatter `type` (`intelligence-source`), `topics` (`[]`), `source` (URL), `title`, `created`, `updated`; body = extracted Markdown. Picked up by `gilberto-process-ingest`.
- Slug: title (ASCII-folded) else URL host+path, `^[a-z0-9][a-z0-9-]{0,63}$`. Same slug, different `source` → `-2`, `-3`, …
- Same URL again: `skipped (idempotent)`, no write. `--force`: rewrites the file (`created` kept).
- Writes are atomic (tmp + fsync + rename); only inside `_ingest/`.
- Errors (exit 1, nothing written): `INVALID_URL`, `FETCH_FAILED` (DNS/timeout/non-2xx), `UNSUPPORTED_CONTENT`, `NO_CONTENT`, `PATH_NOT_FOUND` (`_ingest/` missing), `INVALID_PATH` (`GILBERTO_ROOT` unset), `WRITE_FAILED`, `INVALID_ARGS`.
- Nothing outside `$GILBERTO_ROOT/_ingest/`; no secrets.
