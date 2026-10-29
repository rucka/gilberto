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

## `gilberto install [target]`

Wizard steps 1-3 (no filesystem writes; state kept in memory):

1. target path — positional arg or prompt (default `~/Dropbox/Gilberto/`); `~`/`$HOME` expanded
2. overwrite check — vault marker (`anatomy/anatomy.md` or `.claude/skills/gilberto-*`) aborts; other existing path asks `Target path exists. Continue?` (default No)
3. topic seeds — one multi-select per `pulse`, `intelligence`, `projects`

Flags:

- `--seed-topics <list>` — `pillar=a,b;pillar=c`; skips step 3 prompts, unnamed pillars keep defaults
- `--non-interactive` — never prompt; `target` required
- `--no-hooks`, `--no-launchd` — parsed only (later steps)
- `-v, --verbose` — one `key=value` line per decision

Exit codes: `0` declined overwrite, `1` target is a file, `2` vault exists, `13` not writable, `64` missing/invalid input, `130` Ctrl+C.
