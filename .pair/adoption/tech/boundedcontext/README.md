# Bounded Context Catalog

This catalog defines the bounded contexts of **gilberto** — the technical boundaries derived from subdomain analysis ([`../../product/subdomain/README.md`](../../product/subdomain/README.md)) and the architectural commitments in [`../architecture.md`](../architecture.md). For a single-contributor project building a modular monolith with a single CLI deployable, three contexts are sufficient: more would create coordination overhead with no compensating autonomy gain.

## Why This Grouping?

The dominant axis is **runtime location**. Some code runs at the user's machine inside `$GILBERTO_ROOT` once and forever (Vault Runtime); other code runs one-shot at install / update / release time on the developer's or user's machine but never inside the operating cycle (Distribution & Lifecycle); a thin commodity layer connects either side to OS facilities and external APIs (External Connectivity). This split aligns one-to-one with the architectural commitment that the vault is self-sufficient at runtime ([`../adr/0001-vault-self-sufficiency.md`](../adr/0001-vault-self-sufficiency.md)): the boundary between Vault Runtime and Distribution & Lifecycle *is* that ADR, expressed as bounded contexts.

A second consequence: integration is dominated by **filesystem-as-contract**. There is no live RPC across context boundaries inside gilberto. Distribution & Lifecycle writes files; Vault Runtime reads them. External Connectivity utilities are invoked synchronously inside skill execution, so they share the runtime process — they are not a separate service boundary. Async only enters at the OS level (launchd / cron / systemd → fresh skill invocation).

## Bounded Contexts and Subdomain Mapping

### [Vault Runtime](vault-runtime.md) — Core

- **Subdomains:** Cognitive Operations, Adaptive Anatomy, Personal Knowledge Graph, Plugin Ecosystem (runtime surface)
- **Description:** everything alive inside `$GILBERTO_ROOT`. The cognitive cycle, the operating manual, the personal knowledge graph, and the plugin runtime registry/routing. Self-sufficient: no dependency on the CLI, the repo, or the network at runtime.
- **Why grouped:** shared filesystem state, shared skill execution runtime, shared governance via the playbook DSL. These four subdomains co-evolve and cannot be deployed independently.

### [Distribution & Lifecycle](distribution-lifecycle.md) — Supporting

- **Subdomains:** Distribution & Onboarding, Vault Lifecycle, Plugin Ecosystem (CLI surface)
- **Description:** the npm CLI, the Fumadocs website, the GitHub Release Action, brand identity, distribution adapters per AI-assistant runtime, and the five vault-lifecycle processes (`bootstrap`, `upgrade`, `migrate`, `export`, `archive`). Single deployable boundary; recedes after the instance is bootstrapped.
- **Why grouped:** all source-side concerns; all execute outside the runtime path; all share the CLI deployable.

### [External Connectivity](external-connectivity.md) — Infrastructure

- **Subdomains:** External Integrations, Scheduling Infrastructure
- **Description:** OAuth + REST utilities for calendar / mail / wearables / RSS, outbound action utilities, OS-level scheduling, and AI-assistant lifecycle hooks. Provider-specific anti-corruption layers; user-managed OAuth tokens.
- **Why grouped:** both are commodity (generic subdomains), both expose their value through utilities + event triggers, and both can fall back to manual user action without breaking the runtime.

## Integration Overview

| From                      | To                        | Pattern                                  | Notes                                                                                          |
| ------------------------- | ------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Distribution & Lifecycle  | Vault Runtime             | Filesystem-as-contract (ACL)             | CLI writes skills/anatomy/plugins to disk; runtime reads them. Versioned via manifests.        |
| Vault Runtime             | External Connectivity     | Synchronous in-process                   | Capabilities invoke utilities directly inside skill execution; no service boundary.            |
| External Connectivity     | Vault Runtime             | Asynchronous trigger (OS scheduling)     | launchd/cron/systemd fires skill invocations at cadences declared in anatomy preferences.      |
| Distribution & Lifecycle  | External Connectivity     | Out-of-band release pipeline             | Only at release time (npm publish, Pages/Vercel deploy). Not part of runtime.                  |
| Distribution & Lifecycle  | Distribution & Lifecycle  | Anti-corruption layer (assistant adapters) | Canonical dataset → per-runtime format (Anthropic marketplace, Codex, generic). New runtime = new adapter. |

Pattern counts: **sync 1**, **async 1**, **ACL 2** (filesystem contract + assistant adapters), **out-of-band 1**.

---

This catalog drives epic breakdown (`/pair-process-plan-epics`) and ownership decisions if a second contributor joins. As the project or team scales, contexts can be refined for greater autonomy — splitting Plugin Ecosystem, isolating the website, or moving External Connectivity to a separate package would be the most natural next steps.
