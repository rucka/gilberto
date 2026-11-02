---
name: gilberto-process-vault-bootstrap
description: Bootstrap a gilberto vault from the chat (Path A). Detects the gilberto CLI (global PATH, `npm ls -g`, else `npx 'gilberto@>=0.1.0-0 <2'`) and runs `gilberto install --non-interactive`. Use for first-time vault setup.
requires: gilberto@>=0.1.0-0 <2
---

# gilberto-process-vault-bootstrap

Thin orchestrator. The CLI is the only filesystem mutator (ADR-0001, ADR-0002); never write, copy, move or delete anything in `$GILBERTO_ROOT`, `.claude/` or `~/Library/LaunchAgents/`. Never reimplement wizard steps.

Collect missing inputs in chat, then run:

```bash
python3 "$(dirname "$0")/script.py" [--target-path=<path>] [--seed-topics="pillar=a,b;pillar=c"] \
  [--enable-plugins=<list>] [--disable-hooks] [--disable-launchd] [--verbose] [--confirm=upgrade|npx]
```

Arguments: `target_path?` `seed_topics?` `enable_plugins?` `disable_hooks?` `disable_launchd?` `verbose?`. Provided arguments skip prompts; missing ones take CLI defaults. `enable_plugins` is accepted but not forwarded (CLI has no flag yet).

- Detection: `which gilberto` → `npm ls -g gilberto --depth=0` → `npx 'gilberto@>=0.1.0-0 <2'`. Project-local `node_modules/.bin` ignored.
- Version outside `>=0.1.0-0 <2`: print the mismatch message, ask `upgrade` or `npx` (pass as `--confirm`); never proceed silently.
- Always `--non-interactive`; non-macOS hosts get `--no-launchd` (reported).
- Exit 0: summary (target, pillars, anatomy seeds, hooks, launchd); `--verbose` appends CLI output.
- Exit 2 (vault exists): CLI stderr verbatim, no retry. Exits 1, 13, 28, 64, 65, 70, 130: friendly message + stderr; others: `unexpected CLI failure (exit N)`.
- npx with registry unreachable: friendly message + docs link, non-zero exit.
