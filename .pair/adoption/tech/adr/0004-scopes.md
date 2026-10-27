# ADR-0004: Scopes — One Person, Vertical Scopes, Horizontal Topics

## Status

Accepted

## Date

2026-10-27

## Context

- The user is one person with several contexts: work (e.g. an employer), side ventures, personal life. Work sources of truth live in external systems (Notion, Slack, Google Workspace) reached via connectors (ADR-0003).
- Information must be segregable by **scope** (vertical: a context with its projects, knowledge, notes) and by **topic** (horizontal: "ai" spans several scopes), while the person stays singular (one identity, one network, one health record, one day).
- Putting every pillar at root mixes contexts; separate vaults or full per-scope realms duplicate the person (people, days, health).

## Options Considered

### Option 1: Separate vaults per context

- **Cons**: duplicates the person; cross-vault links fragile; breaks single-vault constraint.

### Option 2: Full realms (every pillar under `realms/<realm>/`)

- **Cons**: splits people, days and health across realms although they belong to one person.

### Option 3: Frontmatter-only scope, flat pillars

- **Cons**: root crowded; no clean export/archive; easy leakage.

### Option 4: Hybrid — person-level at root, optional per-scope segregation, topics global

- **Pros**: person singular; segregation opt-in per scope (folder or tag); topics cut across scopes; per-scope archive/export.
- **Cons**: scope-aware paths in skills; topic views aggregate across folders.

## Decision

**Chosen: Option 4.**

### Layout

```text
$GILBERTO_ROOT/
├── me/                           person (single)
├── network/{people,companies}/   single entity per person; frontmatter scope: [...]
├── pulse/                        health (person-level)
├── journey/YYYY/MM/YYYY-MM-DD.md one day; per-scope sections linking scope notes
├── journey/tasks.md              single task registry; each task has scope
├── projects/ intelligence/ journal/   root pillars (always present): unsegregated content + tag-scoped content
├── scopes/<scope>/               only for scopes with layout: folder
│   ├── <scope>.md                folder-note: description, accounts, rules
│   ├── projects/<slug>/<slug>.md
│   ├── intelligence/<topic>/<source>/
│   ├── journal/                  scope notes (meetings, decisions, logs)
│   └── _ingest/                  scoped drop zone
├── anatomy/{scopes,topics,...}.md
└── _ingest/                      root drop; classification assigns scope
```

### Rules

- **Scopes are optional.** A vault with no scopes keeps everything in root pillars (`projects/`, `intelligence/`, `journal/`).
- **Per-scope layout** in `anatomy/scopes.md`: `layout: folder` → content under `scopes/<scope>/` (segregated); `layout: tag` → content in root pillars with frontmatter `scope: <scope>` (logical only). Mixable: e.g. employer `folder`, venture `tag`, personal none.
- **Vertical (scope)**: folder (if `folder`) or frontmatter `scope` defines scope; root entities (people, companies, tasks) carry `scope: [...]`; content without scope is valid (unscoped). Registry `anatomy/scopes.md` (name, `layout`, `private`, storage mode, bound accounts).
- **Horizontal (topic)**: `anatomy/topics.md` global; same topic may exist in several `scopes/*/intelligence/<topic>/`; views `topic=` aggregate across scopes.
- **Connectors**: each account in `anatomy/integrations/<provider>.md` declares `scope:`; fetched content lands in that scope. Storage mode per scope: `reference` (summary + link to source of truth) or `copy`.
- **Links**: plain wikilinks across scopes. A `private` scope is excluded from other scopes' context (surface/next/reflect) unless explicitly linked.
- **Processes**: accept `scope=` and `topic=` filters; surface/reflect group output per scope in the single daily journey.
- **Lifecycle**: `vault-export` / `vault-archive` accept `scope=` (folder + root entities whose only scope is that one); `gilberto status` reports dangling links and unscoped entities.
- **Mechanics**: `mechanic-forge-scope` creates a scope; `mechanic-scope-move` switches a scope between `tag` and `folder` (moves files, rewrites frontmatter, keeps wikilinks); `promote`/`collapse` work in root or scope folder.

## Rollout

- v1 starts unscoped: root pillars only, empty `anatomy/scopes.md`, path resolver with root-only behavior.
- Scope mechanics (`forge-scope`, `scope-move`) and scope-aware processes come after Initiative #2 (intelligence), shaped with real data; reshaping later is a content migration via `scope-move`.

## Consequences

- Bootstrap seeds root pillars + empty `anatomy/scopes.md`; wizard optionally asks scopes and their layout (#10, #44, #45, #54, #58).
- Anatomy file map gains `anatomy/scopes.md`.
- Skill path resolution via a shared resolver: `(pillar, scope?)` → root or `scopes/<scope>/` per `anatomy/scopes.md`; skills never hardcode paths.
- `connector-notion` promoted to v1 (work source of truth).

## References

- [ADR-0001](0001-vault-self-sufficiency.md) · [ADR-0003](0003-connector-plugins.md) · [anatomy file map](../../decision-log/2026-10-27-anatomy-file-map.md)
