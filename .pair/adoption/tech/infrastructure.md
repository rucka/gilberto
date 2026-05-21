# Infrastructure

## Hosting

- CLI: npm registry (`gilberto`)
- Website: Vercel (primary) / GitHub Pages (fallback)
- Source: `github.com/rucka/gilberto`
- No application backend; no database hosting

## CI/CD

- GitHub Actions
- `ci.yml` on PR + main: install · type-check · lint · format-check · test · build
- `release.yml` on tag: build CLI · npm publish · website deploy · changelog · append to website Releases index
- Cache: pnpm store + turbo
- Merge gate: `pnpm quality-gate`

## Release & Distribution

- SemVer via Changesets
- CLI on npm as `gilberto`
- Website auto-deploys on tag (Vercel)
- Marketplaces: Claude Code (primary) · self-hosted `marketplace.json` · skills.sh · Codex (best-effort)
- Alt installers post-v1: `curl ... | sh`, Homebrew

## Environments

- dev: developer machine (`gilberto install --dry-run` reads source directly)
- prod: end-user machines (each `$GILBERTO_ROOT` independent)
- No staging (Vercel previews substitute)

## Secrets

- No central secret store
- OAuth tokens in user vault `anatomy/preferences.md > ## Integrations`
- CI: `NPM_TOKEN`, `VERCEL_TOKEN` as repo secrets
- No telemetry by default (opt-in only post-v1)

## User-Side Scheduling

- macOS: launchd plists (user-scope LaunchAgents)
- Linux: cron / systemd user-units
- Cadences: 07:00 morning-briefing · 22:00 reflect-day · Sun 22:00 · 1st-of-month · Jan 1 · periodic `fetch`
- Override via `anatomy/preferences.md > ## Cadences`

## Backup & Recovery

- Vault: user-managed (Dropbox / iCloud / git)
- Pre-upgrade snapshot via `gilberto-process-vault-migrate`; rollback supported
- Fork-on-write preserves user customizations across `gilberto update`
- No author-side backup of user data

## Monitoring (Post-Launch)

- GitHub stars / forks (weekly)
- npm install count (weekly)
- Issue triage weekly; SLA: critical ≤1 week, others ≤1 month
- Vercel Analytics (free) for website
- No APM (no backend)

## Security

- Data sovereignty: no data leaves user filesystem unless explicitly initiated
- OAuth2 to external providers; tokens user-managed
- pnpm lockfile integrity
- npm publish via short-lived token
- Dependabot enabled
- `pnpm audit` in CI

## DevOps

- No IaC (Vercel-managed)
- No containers in v1
- Reproducibility via lockfile

## References

- [`../product/PRD.md`](../product/PRD.md) §13
- Peers: [`architecture.md`](architecture.md) · [`tech-stack.md`](tech-stack.md) · [`way-of-working.md`](way-of-working.md)
