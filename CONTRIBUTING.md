# Contributing to gilberto

> Draft — expanded incrementally as the project matures.

## Workflow

Single-contributor (Gianluca) on Kanban — see [way-of-working.md](.pair/adoption/tech/way-of-working.md). External contributors: open an issue first; PRs welcome after alignment.

## Committing

gilberto enforces [Conventional Commits](https://www.conventionalcommits.org/) via commitlint + Husky.

### Format

```text
<type>(<scope>): <subject> [#<issue>]
```

- **type** — one of: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`
- **scope** — one of: `cli`, `dataset`, `website`, `plugin`, `docs`, `infra`
- **subject** — imperative, lowercase, ≤72 chars, no trailing period; sacrifice grammar for concision
- **issue ref** — `(#NNN)` inline when useful; `Closes #NNN` in body for auto-close on merge

### Examples

- `feat(infra): bootstrap monorepo skeleton (#31)`
- `chore(infra): install husky 9 + commitlint deps (#33)`
- `fix(cli): handle missing GILBERTO_ROOT (#88)`
- `test(cli): cover wizard topic seeding (#45)`

### Merge commits

Merge commits (`Merge branch …`) bypass commitlint via the `ignores` rule.

## Hooks

Installed by Husky on `pnpm install` (`prepare` script):

| Hook         | Command                                                         | Purpose                                             |
| ------------ | --------------------------------------------------------------- | --------------------------------------------------- |
| `commit-msg` | `./tools/commitlint-config/bin/commitlint-check.sh --edit "$1"` | Reject non-conventional messages                    |
| `pre-commit` | `pnpm ts:check`                                                 | Fast type-check before commit                       |
| `pre-push`   | `pnpm quality-gate`                                             | Full gate (type + test + lint + format) before push |

### `--no-verify` bypass

Discouraged. Use only for true emergencies (e.g., shipping a hotfix when CI is broken). CI runs the same gate and is the mandatory fallback.

If you bypass, fix the underlying issue in the next commit. Repeated bypasses defeat the gate.

## Branching

`feat/<issue>-<slug>` from `main`. Short-lived; squash-merge; branch deleted post-merge. See [way-of-working.md](.pair/adoption/tech/way-of-working.md#branching).

## Pull Requests

Use [`.github/pull_request_template.md`](.github/pull_request_template.md). Body includes `Closes #<issue>` for auto-close.

## Code of Conduct

TBD — until then, follow common sense: be kind, technical, specific.
