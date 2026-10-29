# ADL — forge-* mechanics contracts

**Date:** 2026-10-29
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `plugins/gilberto-core/skills/mechanic-forge-{topic,template,type}`, `_lib/anatomy_io.py` (#42)

## Decision

- Topic registry: row appended to the table in `anatomy/topics.md` (`| Topic | Description |`); no table → one is created at EOF. Registry write is always last.
- Topic seed note: `anatomy/templates/<pillar>/topic/topic.md` when present (`{{SLUG}}`/`{{TITLE}}`/`{{DATE}}`), else built-in default (`type: <pillar>-topic`). Existing notes never overwritten; re-run heals missing seeds only.
- Template layout: `<name>/<name>.md` folder-note (vault-* ADL; consumed by `mechanic-vault-new` and forge-topic's `topic/topic.md`; supersedes AC3's `template.md`, review r0-1), frontmatter `type: <pillar>-<name>`, `topics: []` + template-only `scope`/`description` (stripped by vault-new), plus `files/note.md` placeholder; existing files kept.
- Type block parsing: YAML block lists (any indent), flow lists, quoted/unquoted items, `#` comments, optional blank line after heading; anything else (no fence, unknown key, no `required`, scalar, malformed list) → `INVALID_TYPE_BLOCK`, never an empty schema. Field names `[a-z_][a-z0-9_-]{0,63}`, else `INVALID_SCHEMA`.
- Schema consumption: `validate.frontmatter` (vault-new) enforces the `### <type>` block (missing required / unknown keys → `INVALID_FRONTMATTER` + diff); `Fields` column only when no block.
- Type registry: `### <scope-role>` + YAML fenced block (`required`, `optional` when non-empty) appended at the end of `## Types`, after any existing table; table rows and unrelated sections byte-stable. A table row alone does not count as a defined type.
- Type identity: schema sets compared order-insensitively. `--merge`: union, existing order kept, new appended; a key that becomes required leaves `optional`; diff logged on stderr (stdout JSON contract unchanged).
- Direct types `person`/`company`: no `--scope`.
- Extra error codes: `RESERVED_NAME`, `INVALID_PILLAR` (template), `INVALID_SCOPE`, `REGISTRY_NOT_FOUND`, `TYPE_CONFLICT` (carries `existing` + `supplied`), `INVALID_SCHEMA` (carries `reason` + `input`).

## References

- [vault-* contracts](2026-10-29-vault-mechanics-contracts.md) · [anatomy file map](2026-10-27-anatomy-file-map.md) · [ADR-0001](../tech/adr/0001-vault-self-sufficiency.md)
