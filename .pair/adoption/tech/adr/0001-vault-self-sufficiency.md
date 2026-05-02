# ADR-0001: Vault Self-Sufficiency at Runtime

## Status

Accepted

## Date

2026-05-02

## Context

- gilberto distributes a CLI npm package that bootstraps a user vault (`$GILBERTO_ROOT`). Once installed, the vault is operated by AI assistant skills (Claude Code, Codex, others) that read/write the filesystem.
- Two separation directions are easy to conflate: (a) the monorepo is not an executable instance, (b) the instance does not depend on the monorepo at runtime. Direction (a) was already implicit in design narrative; direction (b) was not stated as a hard constraint.
- Without an explicit constraint, future skills could drift into importing modules from `apps/cli/`, calling out to the CLI binary at runtime, or relying on files outside `$GILBERTO_ROOT`. Each such drift creates lock-in to the CLI version, breaks AI assistant-agnosticism, and degrades data sovereignty.
- gilberto is positioned as AI assistant-agnostic + model-agnostic with full data sovereignty (Type A pet project, single user). This positioning collapses if the runtime requires the CLI or the source repo.

## Options Considered

### Option 1: Vault self-sufficient at runtime; CLI for install/update only

- **Description**: After install, `$GILBERTO_ROOT` contains everything needed (skills, anatomy, templates, plugin contributions). Skills must not import from `apps/cli/` nor execute the `gilberto` binary at runtime. CLI scope is strictly install / update / status / plugin lifecycle.
- **Pros**: AI assistant-agnostic preserved; user can uninstall the CLI and the vault still works; no version coupling between CLI and vault skills; clear boundary for plugin authors.
- **Cons**: Some operations that could be simpler if delegated to the CLI (e.g., dynamic skill discovery) must happen via filesystem reads instead.

### Option 2: CLI-coupled runtime

- **Description**: Skills delegate certain operations to the CLI at runtime (e.g., spawn `gilberto plugin list` to discover plugins).
- **Pros**: CLI logic is reusable; less duplication.
- **Cons**: Vault stops working if CLI is uninstalled or out of date; couples vault to a specific CLI version; breaks AI assistant-agnosticism (skill authors must assume the CLI is on `$PATH`).

### Option 3: Hybrid (skills work without CLI but degrade)

- **Description**: Skills check for CLI presence and use it when available, fall back otherwise.
- **Pros**: Best of both worlds in theory.
- **Cons**: Two execution paths to test and maintain; degraded mode tends to rot; ambiguity for plugin authors.

## Decision

**Chosen: Option 1 — Vault self-sufficient at runtime; CLI for install/update only.**

The vault is the operational unit. The CLI is the installer/updater. They never share a runtime process. This separation is bidirectional:

- Repo → vault: the monorepo is source-only and cannot be run as an instance
- Vault → repo: after install, `$GILBERTO_ROOT` runs without the CLI and without repo access

CLI scope is closed: `install`, `update`, `status`, `plugin {list,enable,disable,install,update,remove}`.

All runtime behavior is sourced from inside `$GILBERTO_ROOT`:

| What | Where |
|---|---|
| Operations | `.claude/skills/<skill-name>/` (process · capability · utility · mechanic) |
| Structural rules | `anatomy/anatomy.md` |
| Per-event dispatch | `anatomy/playbooks/<domain>/<event>.md` |
| Preferences | `anatomy/preferences.md` |
| Canonical registries | `anatomy/topics.md` · `anatomy/plugins.md` · `anatomy/gilberto.md` |
| Templates | `anatomy/templates/<pillar>/<name>/` |
| Extension primitives | `mechanic-vault-*` + `mechanic-forge-*` skills |

Runtime mutations (new topic, template, type, playbook) happen via `mechanic-forge-*` skills that edit `anatomy/` in place. No CLI re-run, no repo access.

## Consequences

### Benefits

- AI assistant-agnostic + model-agnostic preserved end-to-end
- User can uninstall the CLI and the vault keeps working
- No version coupling between CLI and skills
- Clear, enforceable boundary for plugin authors
- Sovereignty: nothing in the runtime path depends on infrastructure outside the vault

### Trade-offs and Limitations

- Skills cannot share TypeScript code with `apps/cli/`; any common logic that benefits both must be expressed as: (a) Python/Bash scripts shipped inside the skill, or (b) a separate npm package consumed by both — not through process boundaries
- Plugin discovery at runtime relies on `anatomy/plugins.md` and `.claude/skills/` filesystem state — the CLI must keep these consistent at install/update time
- Self-update of skills is not possible from inside the vault; users must run `gilberto update`

## Adoption Impact

- [`../architecture.md`](../architecture.md) — Vault Self-Sufficiency section already reflects this (this ADR is its source)
- Future skill design: SKILL.md guidance must assert no CLI import / no repo path reads
- Future plugin protocol: plugin authors must follow the same constraint
