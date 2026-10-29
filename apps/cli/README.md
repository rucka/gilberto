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

Wizard steps 1-4 (steps 1-3 never write; step 4 writes only inside a temp dir, then moves it atomically):

1. target path — positional arg or prompt (default `~/Dropbox/Gilberto/`); `~`/`$HOME` expanded
2. overwrite check — vault marker (`anatomy/anatomy.md` or `.claude/skills/gilberto-*`) aborts; other existing path asks `Target path exists. Continue?` (default No)
3. topic seeds — one multi-select per `pulse`, `intelligence`, `projects`
4. skeleton — builds `$TMPDIR/gilberto-install-<pid>/`, then a single rename puts it at the target (cross-device: copy to a sibling staging dir, then rename). Any failure or Ctrl+C removes the temp dir and leaves the target untouched. Materialized layout:

```text
me/me.md  journey/journey.md  network/network.md  network/{people,companies}/
pulse/pulse.md  pulse/<topic>/<topic>.md  pulse/<topic>/history/
intelligence/intelligence.md  intelligence/<topic>/<topic>.md
projects/projects.md  projects/<topic>/<topic>.md
_ingest/.gitkeep  anatomy/  .claude/skills/  CLAUDE.md
```

Folder-notes come from `@foomakers/gilberto-vault-bootstrap` templates; topics from step 3. `.claude/settings.json` and anatomy seeds land in later steps.

Flags:

- `--seed-topics <list>` — `pillar=a,b;pillar=c`; skips step 3 prompts, unnamed pillars keep defaults
- `--non-interactive` — never prompt; `target` required
- `--no-hooks`, `--no-launchd` — parsed only (later steps)
- `-v, --verbose` — one `key=value` line per decision, plus `wrote dir="<rel>"` / `wrote file="<rel>"` per item of step 4

Exit codes: `0` declined overwrite, `1` target is a file, `2` vault exists, `13` not writable, `28` disk full, `64` missing/invalid input, `70` vault-bootstrap package missing, `130` Ctrl+C.
