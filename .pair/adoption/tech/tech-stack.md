# Technology Stack

## Languages

- TypeScript 5.x — strict mode (full strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`)
- Node.js ≥22 LTS
- Python 3.11+ — deterministic skill scripts (optional `script.py`)
- Bash POSIX — skill scripts where lighter than Python

## Workspace

- pnpm 10.33.2+ (pinned via `packageManager`)
- Workspaces: `apps/*`, `packages/*`, `tools/*`
- `plugins/*` is **not** a pnpm workspace — Claude marketplace plugin sources (see [ADR-0002](adr/0002-distribution-and-dual-entry-bootstrap.md))
- Versions via `pnpm-workspace.yaml > catalog`
- Turborepo (task graph + caching)

## Distribution Packages

- `gilberto` (npm) — CLI installer/updater
- `@gilberto/vault-bootstrap` (npm) — vault content package (anatomy + 5-pillar skeleton + network/ + `_ingest/` + `.claude/hooks/` + launchd plist templates)
- `gilberto-core` (Claude marketplace plugin) — core skills (11 processes + mechanic + core utility + core capability)
- `pulse-health-tracking`, `pulse-ratko`, `projects-venture`, `projects-editorial` (Claude marketplace plugins) — first-party domain plugins (P1)

## CLI (`apps/cli/`)

- Argparse: commander or yargs (resolved in CLI scaffolding initiative)
- Output: structured + color-aware; ASCII banner ≤80 cols
- Logging: structured + `--verbose`
- Distributed on npm as `gilberto`

## Website (`apps/website/`)

- Fumadocs on Next.js (App Router) + MDX
- Tailwind + brand tokens (CSS vars + JSON)
- Content: MDX in `apps/website/content/`

## Shared Tooling (`tools/`)

- `eslint-config` (flat, TS + import order + unused imports)
- `prettier-config`
- `markdownlint-config`
- `ts-config` (shared `tsconfig.base.json`)

## Testing

- Vitest (unit + integration; co-located `*.test.ts`)
- Playwright (website E2E, only if/when complexity warrants)
- Coverage threshold deferred to first measurement

## Quality Gates

- Standard pipeline tools: `tsc --noEmit` (type-check) · `vitest run` (test) · `eslint` (lint) · `prettier` (format)
- See [`way-of-working.md`](way-of-working.md) §Quality Gates for the registry
- `markdownlint-config` available in `tools/` but not gated in v1

## Schema

- Zod (runtime + TS-derived types) — preferred
- JSON Schema where Zod can't cover (e.g., externally-exposed plugin manifest)

## Git & Release

- Conventional Commits + commitlint
- Husky + lint-staged
- Changesets — version + changelog + npm publish
- GitHub Actions

## AI Assistant Runtime

- Claude Code (primary)
- OpenAI Codex (best-effort via adapter)
- Generic markdown + frontmatter (any assistant supporting markdown skills)

## External Integrations

- Google Calendar via `gcalcli`
- Gmail API (lightweight pull)
- Oura Ring (OAuth2 + API v2)
- Withings (OAuth2 + API)
- Ratko-app (HTTP)
- RSS / Atom

## Scheduling

- macOS: launchd (plists generated at install)
- Linux: cron / systemd user timers
- Windows: out of v1

## Filesystem Conventions

- Vault: markdown + JSON sidecars
- Frontmatter: YAML; mandatory `type`, `topics`, `created`, `updated`; optional `tags`
- Naming: lowercase, hyphen-only, English
- Skill: dir + `SKILL.md` (+ optional `script.{py,sh}`)
- Plugin: `plugin.yaml` (or `.claude-plugin/plugin.json` per Anthropic)

## Pinned Versions (catalog)

| Component | Version |
|---|---|
| pnpm | 10.33.2 |
| Node | ≥22 LTS |
| TypeScript | 5.x |
| Vitest | 1.x |
| Turborepo | 2.x |
| Next.js | 15.x |
| Fumadocs | latest |
| Changesets | latest |
| ESLint | 9.x (flat) |
| Prettier | 3.x |
| Husky | 9.x |
| commitlint | latest |

Authoritative versions in `pnpm-lock.yaml` + `pnpm-workspace.yaml > catalog`.

## References

- [`../product/PRD.md`](../product/PRD.md) §8
- Peers: [`architecture.md`](architecture.md) · [`infrastructure.md`](infrastructure.md) · [`way-of-working.md`](way-of-working.md)
