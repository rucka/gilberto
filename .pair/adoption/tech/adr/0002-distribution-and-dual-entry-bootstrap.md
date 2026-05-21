# ADR-0002: Distribution Surface — Marketplace Plugins + npm Package + Dual-Entry Bootstrap

## Status

Accepted

## Date

2026-05-21

## Context

- PRD §8 originally proposed a single monorepo workspace `dataset/` containing skill, plugin, and template sources, distributed by the CLI. Distribution mechanics were "TBD" and the user entry-point was implicitly `gilberto install` from a terminal.
- Two latent decisions were conflated: (a) **how skills are distributed** to the AI assistant, and (b) **how non-skill vault content** (anatomy, playbooks, vault skeleton, hooks, plists) is distributed and installed. Treating them identically (one `dataset/` workspace) forced a non-existent unified pipeline.
- Claude (and analogous assistants) ship a **plugin marketplace** with native install/update mechanics. Reinventing distribution through a custom `dataset/` workspace duplicates this mechanic for skills, breaks AI-assistant-agnosticism, and loses marketplace UX (discovery, install commands, versioning).
- The user entry-point question is also two-faced: power users prefer `npm install -g gilberto && gilberto install`; users who live inside an AI assistant prefer to invoke a skill (`/gilberto-process-vault-bootstrap`) that orchestrates the install. Forcing one path over the other excludes a primary persona.
- ADR-0001 (vault self-sufficiency) constrains how the CLI and vault interact at runtime; it does not constrain how artifacts reach the user before installation. This ADR fills that gap.

## Options Considered

### Option 1: Unified `dataset/` workspace; CLI as sole entry point

- **Description**: keep PRD §8 verbatim — one `dataset/` workspace holds skills, plugins, templates, playbooks; the CLI is the only way to install into the vault.
- **Pros**: single distribution pipeline; one place for sources.
- **Cons**: ignores the marketplace; "assistant-agnostic" becomes "ours-or-nothing"; only one entry persona served; CLI must reinvent skill install/update/registry mechanics already provided by the marketplace; future support for other assistants requires per-assistant reimplementation of the same.

### Option 2: Marketplace-only distribution for everything

- **Description**: everything (skills + anatomy + vault skeleton) shipped as Claude marketplace plugins; no npm package other than the CLI.
- **Pros**: single distribution surface; uniform install UX inside the assistant.
- **Cons**: non-skill content (vault skeleton, anatomy seeds, launchd plists, FS hooks) is not skill-shaped; misuses marketplace; breaks portability to non-Claude assistants for the non-skill side; tighter coupling to one marketplace's conventions.

### Option 3: Split distribution — marketplace plugins (skills) + npm package (vault content); dual entry-point

- **Description**: split distribution by artifact nature. Skills travel via the **Claude marketplace** as plugins (core: `gilberto-core`; first-party: `pulse-health-tracking`, `pulse-ratko`, `projects-venture`, `projects-editorial`). Non-skill vault content (anatomy + 5-pillar skeleton + network + `_ingest/` + `.claude/hooks/` + launchd plists) travels via an **npm package** `@gilberto/vault-bootstrap`. The CLI consumes the npm package to populate the vault. Two equivalent entry-points exist, both first-class: **(A) skill-led** — user installs the `gilberto-core` plugin, launches a bootstrap skill, the skill downloads the CLI and invokes `gilberto install`; **(B) CLI-direct** — user runs `npm i -g gilberto && gilberto install` from the terminal. Both converge on the same `gilberto install` execution.
- **Pros**: distribution surface matches artifact nature (skill mechanic for skills, npm mechanic for code/templates); marketplace UX preserved for skill install/update; both user personas served; per-assistant adapter limited to skill format (anti-corruption layer at the plugin source build step); CLI remains the single install execution engine, satisfying ADR-0001.
- **Cons**: two release pipelines to maintain (marketplace publish + npm publish); naming clarity required (`gilberto-core` plugin vs `gilberto` npm CLI vs `@gilberto/vault-bootstrap` npm content package); coordination between plugin and package versions for cross-cutting features (mitigated by Changesets fixed-group versioning).

## Decision

**Chosen: Option 3 — Split distribution with dual entry-point.**

### Distribution surfaces

| Artifact                                                                                        | Distribution surface                          | Package/plugin name                                                                                              |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Core skills (11 processes + mechanic primitives + core utilities + core capabilities)           | **Claude marketplace plugin**                 | `gilberto-core`                                                                                                  |
| First-party domain plugins (Phase 3–4)                                                          | **Claude marketplace plugin**                 | `pulse-health-tracking`, `pulse-ratko`, `projects-venture`, `projects-editorial`                                 |
| Non-skill vault content (anatomy, pillar skeleton, network/, `_ingest/`, `.claude/hooks/`, launchd plist templates) | **npm package**                               | `@gilberto/vault-bootstrap`                                                                                       |
| CLI installer                                                                                   | **npm package** (already in PRD)              | `gilberto`                                                                                                       |

### Monorepo layout

```text
apps/
  cli/                          ← npm: gilberto (installer/updater)
  website/                      ← Fumadocs documentation site
packages/
  vault-bootstrap/              ← npm: @gilberto/vault-bootstrap (vault content)
plugins/                        ← Claude marketplace plugin sources (NOT pnpm workspaces)
  gilberto-core/
  pulse-health-tracking/
  pulse-ratko/
  projects-venture/
  projects-editorial/
tools/
  eslint-config/ prettier-config/ markdownlint-config/ ts-config/
```

`pnpm-workspace.yaml` declares `apps/*`, `packages/*`, `tools/*`. `plugins/*` is **not** a pnpm workspace: each subfolder is a plugin source (markdown + scripts + plugin manifest) consumed by the marketplace publish pipeline.

### Dual entry-point

Both paths are first-class and converge on the same CLI invocation:

| Path | Persona                                | Trigger                                                     | Mechanism                                                                                                     |
| ---- | -------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| A    | User living inside the AI assistant    | `/gilberto-process-vault-bootstrap` (or `/gilberto-process-next` detecting "no vault") | Skill (from `gilberto-core` plugin) verifies CLI presence; if missing, downloads via `npx`/`pnpm dlx`; invokes `gilberto install` with collected params |
| B    | Power user from terminal               | `npm i -g gilberto && gilberto install` (or `npx gilberto install`) | CLI executes the wizard natively                                                                              |

Both terminate at the same `gilberto install <target> --topics=… --plugins=…` execution. The CLI is the single source of filesystem truth (ADR-0001 unchanged).

## Consequences

### Benefits

- Distribution surface matches artifact nature: marketplace UX for skills, npm UX for code/content
- Marketplace install/update/discovery/versioning reused; no reinvention
- AI-assistant-agnosticism preserved at the skill source level (one plugin source → per-assistant adapter at build)
- Two user personas served by two equivalent entry-points
- `gilberto install` remains the unique CLI executor — ADR-0001 (vault self-sufficiency) is unaffected
- Naming separates concerns: `gilberto` (CLI npm) · `gilberto-core` (marketplace plugin) · `@gilberto/vault-bootstrap` (npm content) — no aliasing
- `plugins/*` not being a pnpm workspace avoids polluting the dep graph with sources that are not Node packages

### Trade-offs and Limitations

- Two release pipelines (marketplace publish + npm publish) must be coordinated; Changesets fixed-group versioning mitigates by pinning groups
- Plugin marketplace publish mechanics (per assistant) become a release-time dependency; new assistant support = new adapter in the build pipeline
- Skill-led path (A) requires the bootstrap skill to fetch the CLI on first run; npm registry availability becomes a soft dependency at install time (cacheable via `npx`)
- Plugin name `gilberto-core` differs from npm name `gilberto`; documentation must make the distinction explicit on the install page
- Until US-018 lands, only path B is functional; path A becomes available with `gilberto-core` v1.0

## Adoption Impact

- [`../architecture.md`](../architecture.md) — Monorepo Layout describes `apps/`, `packages/`, `plugins/`, `tools/` with `plugins/*` as a non-workspace source tree.
- [`../../product/PRD.md`](../../product/PRD.md) — §6 (Solution Overview) and §8 (Technical Considerations / Architecture Overview) describe dual-entry, marketplace + npm split, `gilberto-core` plugin, and `@gilberto/vault-bootstrap` content package.
- [`../tech-stack.md`](../tech-stack.md) — Workspace section declares `apps/*`, `packages/*`, `tools/*` with `plugins/*` as non-workspace sources; Distribution Packages section lists the four distributed names.
- Epic #10 (Bootstrap process) — describes the dual-entry pattern; **issue #48** covers path A (skill-led entry): "Skill-led bootstrap entry from gilberto-core (CLI presence check + invoke)".
- Issue #31 — refinement captures the layout (`pnpm-workspace.yaml: apps/*, packages/*, tools/*`).
- Plugin manifest schema (Epic Plugin protocol, #15) — supports both per-assistant adapters and the canonical plugin source format used by `plugins/*`.
