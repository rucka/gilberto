# Architecture

Type A — Pet / PoC. See [`../decision-log/2026-05-02-project-categorization.md`](../decision-log/2026-05-02-project-categorization.md).

## Pattern

Modular monolith. CLI single-deployable. Modularity via plugin protocol + data-driven anatomy dispatcher.

## Topology

Monorepo `rucka/gilberto` → CLI npm `gilberto` → user vault instance (`$GILBERTO_ROOT`).

## Repo / Vault Separation (two directions)

See [`adr/0001-vault-self-sufficiency.md`](adr/0001-vault-self-sufficiency.md).

- **Repo is not an instance** — the monorepo is source-only; the CLI distributes from it. The repo cannot be entered and run as Gilberto.
- **Instance is independent of repo at runtime** — after `gilberto install`, `$GILBERTO_ROOT` is self-contained. No CLI process and no repo access in the runtime path.

CLI scope is install/update tooling only:

- `gilberto install <vault>` — bootstrap (writes skills + anatomy + templates + plugins)
- `gilberto update` — propagate framework updates with fork-on-write
- `gilberto status` — drift report
- `gilberto plugin {list,enable,disable,install,update,remove}` — plugin lifecycle

All runtime behavior is sourced from the vault:

| What | Where (in `$GILBERTO_ROOT`) |
|---|---|
| Operations | `.claude/skills/<skill-name>/` (process · capability · utility · mechanic) |
| Structural rules | `anatomy/anatomy.md` (folder-notes vs `index.md`, naming, frontmatter, partitioning) |
| Per-event dispatch | `anatomy/playbooks/<domain>/<event>.md` |
| Preferences | `anatomy/preferences.md` (silence · thresholds · cadences · integrations) |
| Canonical registries | `anatomy/topics.md` · `anatomy/plugins.md` · `anatomy/gilberto.md` |
| Templates | `anatomy/templates/<pillar>/<name>/` |
| Extension primitives | `mechanic-vault-*` + `mechanic-forge-*` skills |

Runtime mutations (new topic / template / type / playbook) happen via `mechanic-forge-*` skills that edit `anatomy/` in place — no CLI re-run, no repo access.

## Monorepo Layout

```
gilberto/
├── apps/{cli,website}/
├── packages/vault-bootstrap/   npm: @gilberto/vault-bootstrap (anatomy + vault skeleton + hooks + plists)
├── plugins/                    Claude marketplace plugin sources (NOT pnpm workspaces)
│   ├── gilberto-core/          core: 11 processes + mechanic + core utility + core capability
│   ├── pulse-health-tracking/  P1
│   ├── pulse-ratko/            P1
│   ├── projects-venture/       P1
│   └── projects-editorial/     P1
├── tools/{eslint-config,markdownlint-config,prettier-config,ts-config}/
└── .changeset/ .github/ .pair/
```

`pnpm-workspace.yaml`: `apps/*`, `packages/*`, `tools/*`. `plugins/*` holds Claude marketplace plugin sources and is **not** a pnpm workspace. See [`adr/0002-distribution-and-dual-entry-bootstrap.md`](adr/0002-distribution-and-dual-entry-bootstrap.md). Authoritative reference: [`../product/PRD.md`](../product/PRD.md) §8.

## Distribution Surface

| Artifact                          | Channel               | Name                                                                              |
| --------------------------------- | --------------------- | --------------------------------------------------------------------------------- |
| Core skills                       | Claude marketplace    | `gilberto-core`                                                                   |
| First-party domain plugins        | Claude marketplace    | `pulse-health-tracking`, `pulse-ratko`, `projects-venture`, `projects-editorial`  |
| Non-skill vault content           | npm                   | `@gilberto/vault-bootstrap`                                                       |
| CLI installer/updater             | npm                   | `gilberto`                                                                        |

Dual entry-point (see ADR-0002):

- **Path A — skill-led**: install `gilberto-core` plugin → launch `/gilberto-process-vault-bootstrap` → skill checks/installs CLI → invokes `gilberto install`
- **Path B — CLI-direct**: `npm i -g gilberto && gilberto install`

Both converge on `gilberto install`. ADR-0001 (vault self-sufficiency at runtime) is unchanged.

## Skill / Plugin Source Layout

Hard constraints:

- Anthropic plugin marketplace compatibility (`.claude-plugin/plugin.json` + `marketplace.json`)
- Codex compatibility (frontmatter superset: `name` + `description`)
- Generic drop-in (`<skill-name>/SKILL.md`)

Adapters at `apps/cli/src/distribution/adapters/{claude-code,codex,generic}/` materialize the canonical source from `plugins/*` per assistant.

## Vault Layout

5 pillars + transversal `network/` + system `anatomy/`:

- `me/me.md`
- `pulse/<topic>/<topic>.md` + `history/`
- `projects/<slug>/<slug>.md` (flat; `status` in frontmatter)
- `intelligence/<topic>/<source>/<source>.md`
- `journey/YYYY/MM/YYYY-MM-DD.md` + `journey/tasks.md`
- `network/{people,companies}/<slug>.md`
- `anatomy/{anatomy,gilberto,topics,plugins,preferences}.md` + `playbooks/<domain>/<event>.md` + `templates/<pillar>/<name>/`
- `_ingest/`, `.claude/{settings.json,skills/}`

## Skill Taxonomy

| Category | Naming |
|---|---|
| process | `gilberto-process-<scope>-<op>` |
| capability | `gilberto-capability-<pillar>-[<sub-scope>-]<op>` |
| utility | `utility-<scope>-<op>` |
| mechanic | `mechanic-<scope>-<op>` |

Composition: process → capability → utility; mechanic orthogonal. Target v1.0: 17p + 44c + 20u + 9m = 90.

## Anatomy

Process skills are thin dispatchers: read `anatomy/playbooks/<domain>/<event>.md` → dispatch.

Strata: `anatomy.md` (structure) · `playbooks/` (per-event) · `preferences.md` (silence/thresholds/cadences/integrations).

## Plugin Protocol

- 4 first-party: `projects-venture`, `projects-editorial`, `pulse-health-tracking`, `pulse-ratko`
- External: `gilberto plugin install <repo-url>` (single + multi-plugin)
- Manifest: Anthropic convention (`.claude-plugin/plugin.json`); per-runtime via adapters
- Contents: `skills/`, `templates/`, `playbooks/`
- File-per-contributor merge in same dir
- Plugin processes autonomous + delegated via `anatomy/plugins.md`

## Hooks & Scheduling

- Claude Code hooks: SessionStart (optional `next`) · PreCompact (snapshot) · SessionEnd (`reflect day`)
- launchd / cron / systemd: 07:00 morning-briefing · 22:00 reflect-day · Sun 22:00 reflect-week · 1st-of-month · Jan 1 · periodic `fetch`
- Override: `anatomy/preferences.md > ## Cadenze`

## Cycles

- A — lifecycle: bootstrap → upgrade ⇄ migrate → archive/export (5 processes)
- B — operational: CAPTURE → STRUCTURE → SURFACE → ACT → REFLECT (+EVOLVE) → NEXT (6 processes)

## Distribution Targets v1.0

Claude Code marketplace (primary) · self-hosted `marketplace.json` · skills.sh · Codex (best-effort, curated).

## Constraints

- Vault self-sufficient at runtime; CLI only for install/update
- AI assistant-agnostic, model-agnostic
- No cloud backend; data never leaves filesystem unless user-initiated
- Single-user, single-vault
- Skills idempotent; fork-on-write upgrades; snapshot before destructive ops
- Platform: macOS first, Linux supported, Windows out of v1

## References

- [`../product/PRD.md`](../product/PRD.md) §8
- Peers: [`tech-stack.md`](tech-stack.md) · [`infrastructure.md`](infrastructure.md) · [`ux-ui.md`](ux-ui.md) · [`way-of-working.md`](way-of-working.md)
- Decisions: [`adr/`](adr) · [`../decision-log/`](../decision-log)
