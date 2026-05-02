# Cognitive Operations (Core Subdomain)

> Classification: **Core**

**Business Purpose:**
Turn gilberto from an inert filesystem into a proactive assistant: orchestrate the continuous cycle that ingests inputs, structures knowledge, anticipates context, executes delegated actions, consolidates memory, and routes the next step.

**Key Capabilities:**

- Polymorphic acquisition from 4 sourcing modes (watch drop, push, on-demand pull, scheduled pull) — `gilberto-process-ingest`
- Automatic filing with classification, sidecar generation, folder-note refresh, wikilink generation — `gilberto-process-structure`
- Anticipatory surfacing (morning briefing, pre-meeting dossier, on-demand query, proactive alert) — `gilberto-process-surface`
- Delegated execution with confirmation (propose/execute) toward the outside world — `gilberto-process-act`
- Temporal consolidation (day/week/month/year) with integrated EVOLVE check — `gilberto-process-reflect`
- Always-available "what should I do now?" navigator — `gilberto-process-next`

**Strategic Importance:**
Primary differentiator vs passive note-apps and stateless AI assistants. The operational cycle is what justifies the "personal assistant" metaphor. Without it, gilberto would be an Obsidian vault with AI plugins — not an agent.

**Complexity Assessment:**
High — thin data-driven orchestration (reads anatomy, dispatches capabilities), confidence-threshold management, idempotency per process, event chains (ingest→structure, surface→act), structured failure modes, concurrency across independent cadences.

**Data Ownership:**
Skills `gilberto-process-*` (6 vital), event chains, narrative execution logs in `journey/logs/YYYY/MM/`, sidecars `.classification.json` / `.ingest.json` / `.error.md` during CAPTURE/STRUCTURE.

**Dependencies:**

- Depends on: Adaptive Anatomy (playbooks + preferences govern behaviour), Personal Knowledge Graph (target of all writes), External Integrations (data sources via `gilberto-capability-fetch`), Scheduling Infrastructure (temporal triggers)
- Provides to: end user (direct output via SURFACE/ACT/NEXT), Plugin Ecosystem (kind-specific delegation), Vault Lifecycle (reuses skills during bootstrap/migrate)

**Team Recommendations:**
Single-contributor in v1 (Gianluca). Profile required: data-driven systems design, prompt engineering for classification, deep domain knowledge (lived experience of a second brain). Sub-skill per each of the 6 processes during implementation.

**Implementation Priority:**
High — PRD Phase 2 (M2-M3). Without the operational cycle there is no value demonstration. Blocked only by Vault Lifecycle (M1: bootstrapped empty vault) and Adaptive Anatomy (playbooks to read).
