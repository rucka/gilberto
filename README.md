# gilberto

![CI](https://github.com/rucka/gilberto/actions/workflows/ci.yml/badge.svg)

Personal AI-native second brain — vault + CLI.

Markdown + JSON vault on your filesystem, operated by portable skills that run in any AI assistant (Claude Code, Codex, …) on any model. No cloud backend, no lock-in.

## Architecture

### Two worlds: repo vs vault

```text
rucka/gilberto (source only)            $GILBERTO_ROOT (user instance)
├── apps/cli        ──npm: gilberto──▶   install / update / status / plugin
├── packages/vault-bootstrap ──npm──▶    anatomy + pillars + hooks + plists
└── plugins/*       ──marketplace──▶     .claude/skills/*
```

- Repo is never an instance: it cannot be run as Gilberto.
- Vault is self-sufficient at runtime: no CLI, no repo access ([ADR-0001](.pair/adoption/tech/adr/0001-vault-self-sufficiency.md)).
- CLI is install/update tooling only — the single filesystem-mutation engine for install.

### Entry points

Both converge on `gilberto install` ([ADR-0002](.pair/adoption/tech/adr/0002-distribution-and-dual-entry-bootstrap.md)):

- **Path A — skill-led**: install `gilberto-core` plugin → `/gilberto-process-vault-bootstrap` → ensures CLI → `gilberto install`.
- **Path B — CLI-direct**: `npm i -g gilberto && gilberto install <vault>`.

### Vault layout

```text
$GILBERTO_ROOT/
├── me/me.md                                 person (single)
├── network/{people,companies}/              one entity per person, scope: [...]
├── pulse/<topic>/ + history/                health & life signals
├── journey/YYYY/MM/YYYY-MM-DD.md + tasks.md one day, per-scope sections
├── projects/ intelligence/ journal/         default home (unscoped or tag-scoped)
├── scopes/<scope>/                          optional, only layout: folder scopes
│   ├── <scope>.md                           description, accounts, rules
│   ├── projects/<slug>/<slug>.md            projects (status in frontmatter)
│   ├── intelligence/<topic>/<source>/       knowledge
│   ├── journal/                             scope notes (meetings, decisions)
│   └── _ingest/                             scoped drop zone
├── _ingest/                                 root drop zone
├── anatomy/                                 system layer (operating manual)
│   ├── anatomy.md gilberto.md topics.md plugins.md preferences.md scopes.md
│   ├── integrations/<provider>.md
│   ├── playbooks/<domain>/<event>.md
│   └── templates/<pillar>/<name>/
└── .claude/{settings.json,skills/}
```

### Scopes and topics

One person, two dimensions ([ADR-0004](.pair/adoption/tech/adr/0004-scopes.md)):

- **Scope (vertical, optional)** — a context (employer, venture, …); per scope choose `layout: folder` (segregated under `scopes/<scope>/`) or `tag` (stays in root pillars, frontmatter `scope`); unscoped content is fine; connectors bound per scope; storage `reference` (link to Notion/Slack/Google source of truth) or `copy`; `private` scopes stay out of other scopes' context; export/archive per scope.
- **Topic (horizontal)** — global `anatomy/topics.md`; a topic spans scopes, views aggregate with `topic=`.
- Person-level data (me, network, pulse, journey) stays at root; wikilinks cross scopes freely.

### Anatomy: data-driven behavior

Process skills are thin dispatchers: read `anatomy/playbooks/<domain>/<event>.md`, then dispatch.

- `anatomy.md` — structure, naming, frontmatter, partitioning.
- `playbooks/` — per-event behavior.
- `preferences.md` — silence, thresholds, cadences, integrations.
- Runtime evolution via `mechanic-forge-*` skills editing `anatomy/` in place.

### Skill taxonomy

| Category   | Naming                                         | Role                         |
| ---------- | ---------------------------------------------- | ---------------------------- |
| process    | `gilberto-process-<scope>-<op>`                | orchestrates a cycle step    |
| capability | `gilberto-capability-<pillar>-[<sub>-]<op>`    | pillar-level operation       |
| utility    | `utility-<scope>-<op>`                         | low-level helper / connector |
| mechanic   | `mechanic-<scope>-<op>`                        | vault/anatomy extension      |

Composition: process → capability → utility; mechanic orthogonal. Target v1.0: ~90 skills.

### Cycles

- **A — lifecycle**: bootstrap → upgrade ⇄ migrate → export / archive.
- **B — operational**: CAPTURE (ingest) → STRUCTURE → SURFACE → ACT → REFLECT (+evolve) → NEXT.

### Scheduling & hooks

- Claude Code hooks: SessionStart (`next`), PreCompact (snapshot), SessionEnd (`reflect day`).
- launchd/cron: 07:00 morning briefing · 22:00 reflect day · Sun reflect week · monthly · yearly · periodic `fetch`.
- Override in `anatomy/preferences.md > ## Cadences`.

### Plugins

- First-party: `pulse-health-tracking`, `pulse-ratko`, `projects-venture`, `projects-editorial`.
- Connectors ([ADR-0003](.pair/adoption/tech/adr/0003-connector-plugins.md)): `connector-{google,media,slack}` (v1), more post-v1. API-first deterministic scripts, MCP fallback; secrets in OS keychain, never in the vault; unattended runs never write externally.
- External: `gilberto plugin install <repo-url>`.
- Manifest `.claude-plugin/plugin.json`; contents `skills/`, `templates/`, `playbooks/`; registry `anatomy/plugins.md`.
- Per-assistant adapters (`claude-code`, `codex`, `generic`) materialize skills from `plugins/*`.

### Constraints

- Data never leaves the filesystem unless user-initiated.
- Single-user, single-vault; skills idempotent; fork-on-write upgrades; snapshot before destructive ops.
- macOS first, Linux supported, Windows out of v1.

## Monorepo

```text
apps/{cli,website}/         CLI (npm gilberto) · docs site (Fumadocs)
packages/vault-bootstrap/   npm @gilberto/vault-bootstrap
plugins/                    marketplace plugin sources (not pnpm workspaces)
tools/                      shared eslint/prettier/markdownlint/ts/commitlint configs
.pair/                      product + tech adoption, ADRs, decision log
```

Stack: Node ≥ 22.12, pnpm, Turbo, TypeScript, Vitest, Changesets.

```bash
pnpm install
pnpm quality-gate
```

## References

- Product: [PRD](.pair/adoption/product/PRD.md)
- Architecture: [architecture.md](.pair/adoption/tech/architecture.md) · [tech-stack.md](.pair/adoption/tech/tech-stack.md)
- Decisions: [ADR](.pair/adoption/tech/adr) · [decision log](.pair/adoption/decision-log)
- Workflow: [CONTRIBUTING.md](CONTRIBUTING.md) · [way-of-working.md](.pair/adoption/tech/way-of-working.md)
