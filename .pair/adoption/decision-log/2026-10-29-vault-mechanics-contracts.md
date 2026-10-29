# ADL — vault-* mechanics contracts

**Date:** 2026-10-29
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `plugins/gilberto-core/skills/mechanic-vault-*`, `_lib` (#41; reused by #42, #43)

## Decision

- Template location: `anatomy/templates/<pillar>/<template>/<template>.md` (folder-note pattern); missing → `TEMPLATE_NOT_FOUND`.
- Entity types: `type` scope accepts the seeded plural (`projects-index`) and the singular `project-index` used in the story AC1 example.
- Anatomy schema: `### <type>` YAML block (forge-type, see forge ADL) wins; else optional `Fields` column in `anatomy/anatomy.md > ## Types`; when a registered type has it, frontmatter must be exactly mandatory keys + those fields, else `INVALID_FRONTMATTER` + `{missing, unknown}`. No column / unregistered type / no `anatomy.md` → no schema check.
- Sidecar `.<slug>.json` (`{slug, pillar, template}`) belongs to the entity: it is not a child for `collapse` and is removed with the folder; any other child (hidden included) → `HAS_CHILDREN`.
- Extra error codes: `ENTITY_NOT_FOUND`, `CONFLICT` (file and folder-note both exist), `TEMPLATE_NOT_FOUND`, `INVALID_ARGS`, `WRITE_FAILED`.
- Tests run in-process (coverage) plus one subprocess smoke per mechanic; shared fixtures in `skills/conftest.py`.

## References

- [anatomy file map](2026-10-27-anatomy-file-map.md) · [ADR-0001](../tech/adr/0001-vault-self-sufficiency.md)
