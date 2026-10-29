# gilberto CLI

Workspace for the `gilberto` binary. `pnpm --filter gilberto build` emits `dist/cli.js` (executable).

## Install (alpha)

```bash
npx gilberto@next --version
```

Requires Node ≥ 22.12. Published on npm tag `next`.

## Layout

- `src/cli.ts` — Commander entry point (placeholder until #37)
- `src/index.ts` — library entry
- `src/{config,registry,commands,ui,test-utils}/`, `src/diagnostics.ts` — aliased via `#config`, `#registry`, `#commands`, `#ui`, `#test-utils`, `#diagnostics` (`tsconfig.json > paths`)
