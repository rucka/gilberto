# Install

Two entry points, one engine: both run `gilberto install`, the only filesystem mutator ([ADR-0002](../.pair/adoption/tech/adr/0002-distribution-and-dual-entry-bootstrap.md)). Requires Node ≥ 22.12.

## Path A — skill-led (Claude Code)

1. Install the `gilberto-core` plugin from the Claude Code marketplace.
2. Run `/gilberto-process-vault-bootstrap`.
3. Answer the in-chat prompts (target path, topic seeds). Arguments you already gave skip their prompt; any you leave out take the CLI defaults.

The skill is a thin orchestrator. It never writes to the vault, `.claude/` or `~/Library/LaunchAgents/`. It:

- detects the CLI: `which gilberto` → `npm ls -g gilberto --depth=0` → fallback `npx gilberto@latest` (project-local `node_modules/.bin` ignored);
- checks the version against `>=0.1.0 <2`; on mismatch asks `upgrade` or `npx`, never proceeds silently;
- always runs `gilberto install <target> --non-interactive`; adds `--no-launchd` on non-macOS hosts;
- reports a summary (target, pillars, anatomy seeds, hooks, launchd); `verbose` appends the CLI output.

Skill arguments: `target_path`, `seed_topics`, `enable_plugins` (accepted, not forwarded yet), `disable_hooks`, `disable_launchd`, `verbose`.

If the npm registry is unreachable during the npx fallback, the skill exits non-zero. Install the CLI via Path B, then re-run the skill.

## Path B — CLI-direct

```bash
npx gilberto@next install ~/vault
# or
npm i -g gilberto@next && gilberto install ~/vault
```

Interactive by default; pass `--non-interactive` for scripts.

### Flags

| Flag                   | Effect                                                                 |
| ---------------------- | ---------------------------------------------------------------------- |
| `[target]`             | vault directory (default `~/Dropbox/Gilberto/`)                        |
| `--seed-topics <list>` | topic seeds per pillar, e.g. `"intelligence=ai,product;pulse=health"` |
| `--non-interactive`    | never prompt; use arguments and defaults                               |
| `--no-hooks`           | skip step 7                                                            |
| `--no-launchd`         | skip step 8                                                            |
| `--launchd-in-ci`      | write launchd plists even when `CI=true` (macOS)                       |
| `-v`, `--verbose`      | one line per wizard decision                                           |

## Wizard steps

| Step | What            | Writes                                                                                     |
| ---- | --------------- | ------------------------------------------------------------------------------------------ |
| 1    | target path     | nothing                                                                                    |
| 2    | overwrite check | nothing                                                                                    |
| 3    | topic seeds     | nothing (pillars: pulse, intelligence, projects)                                           |
| 4    | vault skeleton  | pillars + `CLAUDE.md` into a temp dir                                                      |
| 5    | plugins         | nothing (lists bundled plugins)                                                            |
| 6    | anatomy seeds   | `anatomy/` seeds into the temp dir, then the temp dir moves atomically to the target       |
| 7    | `.claude` hooks | `.claude/hooks/*.sh` (PreCompact, SessionEnd) + merge into `.claude/settings.json`         |
| 8    | launchd plists  | `~/Library/LaunchAgents/com.foomakers.gilberto.{ingest,morning-briefing,reflect-day}.plist` |

Step 8 runs on macOS only (Linux: stub) and is skipped when `CI=true` unless `--launchd-in-ci`. Plists are written, never loaded (no `launchctl`). It warns if `claude` is not on `PATH`.

## Exit codes

| Code | Meaning                                         |
| ---- | ----------------------------------------------- |
| 0    | success, or user declined                       |
| 1    | target is a file, or a foreign plist is in place |
| 2    | vault already exists                            |
| 13   | target not writable                             |
| 28   | disk full                                       |
| 64   | bad or missing input                            |
| 65   | invalid `settings.json` or plist/plutil failure |
| 70   | vault-bootstrap content package missing         |
| 130  | aborted                                         |

Path A maps these to friendly messages (exit 2 shows CLI stderr verbatim). Any other code reports `unexpected CLI failure (exit N)`.
