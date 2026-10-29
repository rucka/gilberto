# gilberto CLI

Workspace for the `gilberto` binary. `pnpm --filter gilberto build` emits `dist/cli.js` (executable).

## Install (alpha)

```bash
npx gilberto@next --version
```

Requires Node ≥ 22.12. Published on npm tag `next`.

## Install wizard steps 5-6

Step 5 lists the bundled first-party plugins (info only, no prompt, no install). Step 6 copies `seed/anatomy/` from `@foomakers/gilberto-vault-bootstrap` into `<tmp>/anatomy/` (`{{DATE}}` → install date; `--seed-topics` rows appended to `topics.md`). Missing package or unreadable seed → stderr message, temp dir removed, exit 70. `--verbose` prints `wrote file=<path>` / `wrote dir=<path>`.

## Layout

- `src/cli.ts` — Commander entry point (placeholder until #37)
- `src/index.ts` — library entry
- `src/{config,registry,commands,ui,test-utils}/`, `src/diagnostics.ts` — aliased via `#config`, `#registry`, `#commands`, `#ui`, `#test-utils`, `#diagnostics` (`tsconfig.json > paths`)
