# @gilberto/vault-bootstrap

Seed content for a new gilberto vault + two pure functions. Read-only: copy/write logic lives in the CLI (ADR-0001).

## API

```ts
import { PILLARS, getSeedRoot, resolvePillarPath, UnknownPillarError } from '@gilberto/vault-bootstrap'

getSeedRoot() // absolute path of shipped seed/, resolved from the module file
resolvePillarPath(vaultRoot, 'me') // join(vaultRoot, 'me')
resolvePillarPath(vaultRoot, 'me', 'work') // scope ignored in v1 (ADR-0004) -> same path
resolvePillarPath(vaultRoot, 'x' as never) // throws UnknownPillarError
```

`PILLARS`: `me, pulse, projects, intelligence, journey, network`.

## Seed tree

```text
seed/
├── anatomy/      anatomy.md topics.md scopes.md gilberto.md preferences.md plugins.md playbooks/ templates/
├── skeleton/     CLAUDE.md, <pillar>/<pillar>.md, network/{people,companies}/, _ingest/
├── hooks/        dispatch.sh (POSIX; exits 0 "skill not installed" when skill missing)
└── launchd/      morning-briefing, reflect-day, ingest-watch plist templates
```

Placeholders: `{{VAULT_ROOT}}`, `{{LABEL_PREFIX}}`, `{{DATE}}`, `{{OWNER_NAME}}`. Plists are templates, never loaded here.

## Scripts

`pnpm build` · `pnpm ts:check` · `pnpm lint` · `pnpm test`
