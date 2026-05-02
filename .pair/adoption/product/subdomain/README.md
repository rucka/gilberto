# Subdomain Catalog Index

This folder contains the strategic subdomain definitions for **gilberto** — Personal AI-Native Second Brain. Each file provides a detailed specification supporting Domain-Driven Design and downstream architecture decisions.

Authoritative source: [`../PRD.md`](../PRD.md).

## Subdomain List

### Core Subdomains

- [Cognitive Operations](cognitive-operations.md) — orchestration of the continuous CAPTURE/STRUCTURE/SURFACE/ACT/REFLECT/NEXT cycle
- [Personal Knowledge Graph](personal-knowledge-graph.md) — multi-pillar vault (me, pulse, projects, intelligence, journey, network) as the compounding asset
- [Adaptive Anatomy](adaptive-anatomy.md) — data-driven operating manual (structure + playbooks + preferences) with self-evolution

### Supporting Subdomains

- [Vault Lifecycle](vault-lifecycle.md) — bootstrap, upgrade, migrate, export, archive of an instance
- [Plugin Ecosystem](plugin-ecosystem.md) — plugin protocol, registry, routing, 4 first-party plugins
- [Distribution & Onboarding](distribution-onboarding.md) — npm CLI, Fumadocs website, release action, brand identity

### Generic Subdomains

- [External Integrations](external-integrations.md) — calendar, mail, wearables, RSS, OAuth providers
- [Scheduling Infrastructure](scheduling-infrastructure.md) — launchd, cron, systemd, AI-assistant hooks

## Subdomain Relationship Matrix

| From                      | To                        | Relationship Type | Data/Knowledge Flow                                     | Coordination Level |
| ------------------------- | ------------------------- | ----------------- | ------------------------------------------------------- | ------------------ |
| Cognitive Operations      | Personal Knowledge Graph  | consumer          | Read+write on pillars via capabilities                  | High               |
| Cognitive Operations      | Adaptive Anatomy          | consumer          | Read playbooks + preferences for dispatch               | High               |
| Cognitive Operations      | External Integrations     | consumer          | Pull via `gilberto-capability-fetch`; push via ACT      | Medium             |
| Cognitive Operations      | Scheduling Infrastructure | consumer          | Temporal triggers (briefing, reflect, fetch)            | Medium             |
| Adaptive Anatomy          | Cognitive Operations      | governor          | Governs every dispatch via the playbook DSL             | High               |
| Adaptive Anatomy          | Personal Knowledge Graph  | governor          | Templates + naming + frontmatter rules                  | High               |
| Adaptive Anatomy          | Plugin Ecosystem          | governor          | Registry + routing rules + file-per-contributor merge   | High               |
| Vault Lifecycle           | Personal Knowledge Graph  | producer          | Materialises initial structure at bootstrap             | High               |
| Vault Lifecycle           | Adaptive Anatomy          | producer          | Installs core anatomy; manages versioning               | High               |
| Vault Lifecycle           | Scheduling Infrastructure | producer          | Generates plist/cron at bootstrap                       | Medium             |
| Plugin Ecosystem          | Cognitive Operations      | extender          | Kind-specific delegation via routing                    | Medium             |
| Plugin Ecosystem          | Personal Knowledge Graph  | extender          | Pillar-specific templates + capabilities                | Medium             |
| Distribution & Onboarding | Vault Lifecycle           | host              | CLI invokes `install` / `update`                        | High               |
| Distribution & Onboarding | Plugin Ecosystem          | host              | CLI `plugin {...}` + Anthropic marketplace conventions  | Medium             |
| External Integrations     | Cognitive Operations      | provider          | External data (calendar, mail, wearables, RSS)          | Medium             |
| Scheduling Infrastructure | Cognitive Operations      | trigger           | Periodic skill execution                                | Medium             |

---

For details on each subdomain, see the linked files above. This catalog is the foundation for bounded context definition (`/pair-process-map-contexts`) and team alignment.
