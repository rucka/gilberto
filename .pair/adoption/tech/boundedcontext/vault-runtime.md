# Vault Runtime Context

> Type: **Core**

## Subdomains Covered

- Cognitive Operations
- Adaptive Anatomy
- Personal Knowledge Graph
- Plugin Ecosystem (runtime surface: registry, routing, file-per-contributor merge, delegation)

## Business Scope and Purpose

Everything that executes inside the user's instance (`$GILBERTO_ROOT`) once `gilberto install` has run. This is where gilberto is *alive*: the cognitive cycle reads anatomy, dispatches capabilities, mutates the personal knowledge graph, and proposes its own evolution. The four subdomains are grouped here because they share the same filesystem state, the same skill-execution runtime (the user's chosen AI assistant), and the same governance model (the playbook DSL). They cannot be deployed or evolved independently at runtime.

The architectural commitment "vault self-sufficient at runtime" (ADR-0001) makes this context the centre of gravity of the whole product: no CLI, no repo, no network call is part of the runtime path. The vault must keep working even after the CLI is uninstalled.

## Relationships Between Bounded Context and Sub Domains

- **Cognitive Operations** is the *engine*. Its 6 vital processes (CAPTURE/STRUCTURE/SURFACE/ACT/REFLECT/NEXT) plus the navigator are the only orchestrators in the system; everything else is invoked from them.
- **Adaptive Anatomy** is the *manual*. Every dispatch decision in Cognitive Operations is read from `anatomy/playbooks/`; every behaviour modulation is read from `anatomy/preferences.md`; every structural rule comes from `anatomy/anatomy.md`. EVOLVE proposes anatomy changes during REFLECT.
- **Personal Knowledge Graph** is the *substrate*. It is the read/write target of every capability invoked by the cycle. Folder-notes, sidecars, and wikilinks are the data structures Cognitive Operations produces and consumes.
- **Plugin Ecosystem (runtime)** *extends* both: plugin processes register in `anatomy/plugins.md` and are delegated to by universal processes; plugin capabilities operate on pillars; plugin templates land in `anatomy/templates/`.
- Cross-context: this context **consumes** anatomy contents written by Distribution & Lifecycle at install/update (via filesystem-as-contract), and **invokes** External Connectivity utilities synchronously when capabilities need external data or actions.

## Integration Patterns

- **Filesystem-as-contract (ACL) inbound** — Distribution & Lifecycle never calls runtime code; it writes skills, anatomy templates, and plugin contents to disk. Runtime reads them at execution time. The contract is the on-disk layout + manifest schema, versioned via Adaptive Anatomy.
- **Synchronous in-process outbound** — Cognitive Operations invokes External Connectivity utilities directly inside skill execution (e.g., `gilberto-capability-fetch` calls `utility-fetch-rss`). No service boundary, no RPC.
- **Asynchronous trigger inbound** — Scheduling Infrastructure fires skill executions at cadences declared in `anatomy/preferences.md > ## Cadenze` (07:00 briefing, 22:00 reflect). The trigger is OS-level (launchd/cron); the runtime sees it as a fresh skill invocation.
- **No outbound calls to other contexts** — runtime never imports from `apps/cli/`, never invokes the `gilberto` binary, never reads files outside `$GILBERTO_ROOT`. Strict isolation.

## Data Ownership

- All runtime skills under `$GILBERTO_ROOT/.claude/skills/{process,capability,utility,mechanic}/`
- Full `$GILBERTO_ROOT/anatomy/` (structure + playbooks + preferences + registries + templates + migrations)
- The five primary pillars + `network/` + sidecar JSON + folder-notes
- Transient `_ingest/` landing zone with `.classification.json` / `.ingest.json` / `.error.md` sidecars
- Narrative execution logs in `journey/logs/YYYY/MM/`
- Plugin runtime contents installed by `gilberto plugin enable` (skills, templates, playbooks, registry entry)

## Team Alignment

Single-contributor in v1 (Gianluca). All four subdomains co-evolve at the same pace; splitting ownership before stable contracts emerge would create coordination overhead without payoff. Future split (post-v1, with a second contributor): one engineer on Cognitive Operations + Adaptive Anatomy (the orchestration core), one on Personal Knowledge Graph + Plugin Ecosystem (the schema/extension layer). High autonomy: this context is the product; design decisions originate here.

## Ubiquitous Language

| Term                  | Definition                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Process               | A thin orchestrator skill (`gilberto-process-*`); the only kind of skill that may invoke other skills.                    |
| Capability            | A vault-aware skill (`gilberto-capability-*`) that operates on pillars and knows their structure.                         |
| Utility               | A vault-agnostic skill (`utility-*`) that performs a pure function (HTTP fetch, format conversion, OAuth flow).           |
| Mechanic              | A primitive skill (`mechanic-vault-*`, `mechanic-forge-*`) that mutates vault structure or anatomy in place.              |
| Anatomy               | The set of files under `anatomy/` that govern runtime behaviour (structure rules + playbooks + preferences + registries). |
| Playbook              | A markdown file at `anatomy/playbooks/<domain>/<event>.md` declaring which capabilities to call for an event/type.        |
| Pillar                | A top-level vault directory mapped to a facet of the user (`me`, `pulse`, `projects`, `intelligence`, `journey`).         |
| Folder-note           | The markdown file co-named with its containing folder (`<slug>/<slug>.md`); the canonical entry point of an entity.       |
| Sidecar               | A `.<extension>.<name>` file co-located with a primary artefact, carrying metadata, classification, or notes.             |
| EVOLVE                | The proposal layer attached to every REFLECT cadence; emits anatomy modification proposals based on observed patterns.    |
| Confidence threshold  | Per-event numeric gate read from anatomy that decides whether STRUCTURE auto-routes or asks for human confirmation.       |
| Fork-on-write         | Upgrade strategy that copies a core anatomy file to a user-overlay path before applying user modifications.                |
| Silence-learned       | A user preference, expressed during dialogue, that suppresses future confirmation prompts for a recurring action.         |

## Quality Attributes

- **Performance:** in-vault skill executions complete within 2 s for read paths and within 5 s for typical write paths (PRD §8). Background processes (ingest, reflect) are async and non-blocking from the user's point of view.
- **Scalability:** single-user, single-vault. Schema and indexes must remain navigable up to ~10 K markdown files (PRD §8). No multi-tenant requirements.
- **Reliability:** every skill is idempotent (safe re-run). Last-write-wins on sidecars; append-only on log/sunto sections. No data leaves the filesystem unless explicitly user-initiated. The runtime has no cloud dependency and must operate fully offline once external integrations have been pulled.
