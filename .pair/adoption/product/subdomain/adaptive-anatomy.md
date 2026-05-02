# Adaptive Anatomy (Core Subdomain)

> Classification: **Core**

**Business Purpose:**
Provide the data-driven operating manual that governs every skill's behaviour — structural rules, per-event/per-type playbooks, user preferences — and let it evolve automatically based on observed patterns. It is the "cerebellum" that lets orchestrators stay thin.

**Key Capabilities:**

- Structure layer (`anatomy/anatomy.md`) — vault structural rules, naming, frontmatter, partitioning
- Playbooks layer (`anatomy/playbooks/<domain>/<event>.md`) — for each event/type, declares which capability to invoke
- Preferences layer (`anatomy/preferences.md`) — silence learned, thresholds, cadences, integrations
- Canonical registries (`topics.md`, `plugins.md`, `gilberto.md`)
- Evolution-check (`gilberto-capability-anatomy-evolution-check`) — daily/weekly/monthly/yearly modification proposals
- Mechanic primitives (`mechanic-forge-{topic,type,template,playbook,source}`) for in-place anatomy edits
- CRUD-uniform (`gilberto-capability-anatomy-{topics,playbooks,preferences}`)

**Strategic Importance:**
Differentiator vs hard-coded systems. Adding a new event type means adding a playbook entry, not editing orchestrator code. Enables the "minimize-layers" principle (D-40) and self-evolution (D-37 §3.8). It is what makes gilberto a living system, not a collection of scripts.

**Complexity Assessment:**
High — layered semantics (structure/playbooks/preferences), file-per-contributor merge between core and plugins, non-trivial evolution heuristics (when is a pattern worth crystallising?), conflict resolution during fork-on-write upgrade.

**Data Ownership:**
Full `$GILBERTO_ROOT/anatomy/`: `anatomy.md`, `gilberto.md`, `topics.md`, `plugins.md`, `preferences.md`, `playbooks/<domain>/<event>.md`, `templates/<pillar>/<name>/`, `migrations/`. Skills `mechanic-forge-*` and `gilberto-capability-anatomy-*`.

**Dependencies:**

- Depends on: Vault Lifecycle (bootstrap installs anatomy templates + initial customisations)
- Provides to: Cognitive Operations (governs every dispatch), Plugin Ecosystem (registry + routing rules), Personal Knowledge Graph (templates + naming + frontmatter rules), Vault Lifecycle (upgrade reads versioning + migrations)

**Team Recommendations:**
Single-contributor in v1. Requires meta thinking: design a declarative language (playbook DSL) + an evolution engine. Profile: language-design / config-system. Tight iteration with Cognitive Operations.

**Implementation Priority:**
High — PRD Phase 2, in parallel with the operational cycle. Initial bootstrap (M1) installs core anatomy; enriched during M2-M3 with real playbooks. EVOLVE active from M3.
