# Personal Knowledge Graph (Core Subdomain)

> Classification: **Core**

**Business Purpose:**
Host and organise the user's personal memory in markdown + JSON on the filesystem, mirroring the structure of a person (who they are, how they currently are, what they do, what they know, what they live), with cross-cutting links to people and companies. It is the asset that compounds over time.

**Key Capabilities:**

- Long-term identity (`me/`) — values, habits, ambitions, biography
- Operational contexts per topic (`pulse/<topic>/`) — health, body, finance + hybrid `history/` (JSON for machines, MD for humans)
- Active initiatives, flat layout with status in frontmatter (`projects/<slug>/`) — venture, editorial, etc.
- Knowledge per topic + source (`intelligence/<topic>/<source>/`) — newsletters, courses, books, papers
- Hierarchical temporal narrative (`journey/YYYY/MM/`) — daily/weekly/monthly/yearly + `tasks.md` registry + `sparks.md`
- Cross-cutting registry of people + companies (`network/{people,companies}/`) with `relationship-level`
- Bidirectional cross-pillar wikilinks; on-demand file→folder promotion (D-11); free, evolutive schema

**Strategic Importance:**
This *is* the product: the user's navigable vault. Data sovereignty (local markdown + Obsidian-friendly), vendor-agnostic, portable. The "person" metaphor is the system's recognisable signature vs generic Notion/Logseq.

**Complexity Assessment:**
High — coherent multi-pillar schema, stable frontmatter conventions, per-pillar sub-structuring (none/topic/vertical/topic+source/temporal/entity-type/layer), promotion semantics, wikilink integrity under renames, subject rule (pulse vs intelligence), journey↔pulse/history boundaries.

**Data Ownership:**
The user's filesystem under `$GILBERTO_ROOT/`: 5 primary pillars + `network/` + JSON sidecars + folder-notes + YAML frontmatter. `_ingest/` as transient landing zone. **Not** anatomy (separate subdomain).

**Dependencies:**

- Depends on: Vault Lifecycle (initial bootstrap creates the structure), Adaptive Anatomy (templates + naming + frontmatter rules)
- Provides to: Cognitive Operations (read/write target), Plugin Ecosystem (extends pillars via templates + capabilities), External Integrations (sink for ingested data)

**Team Recommendations:**
Single-contributor in v1. Requires knowledge-architect sensitivity: understanding of Obsidian, markdown idioms, naming conventions. Structural decisions tracked as ADR/ADL (D-00..D-48 already consolidated in the `_docs/` decision log corpus).

**Implementation Priority:**
High — PRD Phase 1+2. Baseline schema at bootstrap (M1), enriched during Cognitive Operations (M2-M3). Plugin extensions (M4).
