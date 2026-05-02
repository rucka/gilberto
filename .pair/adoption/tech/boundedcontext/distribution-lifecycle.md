# Distribution & Lifecycle Context

> Type: **Supporting**

## Subdomains Covered

- Distribution & Onboarding
- Vault Lifecycle
- Plugin Ecosystem (CLI surface: `gilberto plugin {list,enable,disable,install,update,remove}`)

## Business Scope and Purpose

Everything that gets gilberto from the monorepo to a user's filesystem, and everything that manages the lifetime of an instance after install. This context owns the npm CLI (`apps/cli/`), the Fumadocs website (`apps/website/`), the GitHub Release Action, the brand identity, the Anthropic/Codex/generic distribution adapters, and the five vault-lifecycle processes (`bootstrap`, `upgrade`, `migrate`, `export`, `archive`).

The three subdomains are grouped here because they share a single deployable boundary (the CLI npm package + the static website) and because they execute outside the runtime: Vault Lifecycle skills run *one-shot*, invoked by the CLI, not by the cognitive cycle; Plugin CLI commands wrap mechanic primitives but live in `apps/cli/src/plugin/`; Distribution & Onboarding owns the public surface and the release pipeline. None of these are part of the runtime path.

This context is what makes adoption possible. Without a coherent install path, brand, and documentation, the framework cannot launch publicly (PRD §6 P0#7+P0#8). Once an instance is alive, this context recedes — `gilberto update` runs rarely; `migrate` even more so.

## Relationships Between Bounded Context and Sub Domains

- **Distribution & Onboarding** owns the CLI scaffold (commander/yargs), distribution adapters (Claude Code marketplace, Codex, generic), the website (landing + reference docs + auto-generated releases index), brand assets, and the GitHub Release Action.
- **Vault Lifecycle** owns the five `gilberto-process-vault-*` processes plus `mechanic-vault-{new,promote,collapse}`. These are *skill source* in the dataset; at runtime they execute inside the user's vault (technically Vault Runtime territory), but their *design and lifecycle* belong here because they are invoked by the CLI and exist to manage the instance, not to operate on personal data.
- **Plugin Ecosystem (CLI surface)** owns the `gilberto plugin {...}` commands. The plugin protocol (manifest schema, registry semantics, routing rules) lives in Vault Runtime; this context provides the user-facing entry points that mutate the plugin state on disk.
- Cross-context: this context **provides** the on-disk artefacts that Vault Runtime consumes (skills, anatomy templates, plugin contents, scaffolding). It **invokes** External Connectivity only at release time (npm registry publish, Pages/Vercel deploy).

## Integration Patterns

- **Filesystem-as-contract (ACL) outbound** — the CLI never calls into the runtime; it writes files (skills, anatomy templates, plugins, plists) to the user's filesystem. The contract is the documented on-disk layout + the manifest/version schema. Fork-on-write protects user customisations during upgrade.
- **Synchronous in-process** within the CLI — `gilberto install` invokes `gilberto-process-vault-bootstrap` as an in-process skill execution against the target directory; same pattern for `update` ↔ `vault-upgrade`, etc.
- **Out-of-band release** — at git tag, the GitHub Release Action publishes to the npm registry and deploys the website (Pages/Vercel) and appends release notes. No runtime traffic; pipelines are external systems.
- **Anti-corruption layer for AI-assistant runtimes** — distribution adapters (`apps/cli/src/distribution/adapters/{claude-code,codex,generic}/`) translate the canonical dataset format into per-runtime formats (Anthropic plugin marketplace, Codex frontmatter superset, generic drop-in). New assistant support is a new adapter; the canonical dataset never changes.

## Data Ownership

- `apps/cli/` — CLI source, commands (`install`, `update`, `status`, `plugin {...}`), distribution adapters, install wizard
- `apps/website/` — Fumadocs site (Next.js + MDX), content, brand-aware theming
- `.github/workflows/release.yml` and `.changeset/`
- `dataset/skills/process/gilberto-process-vault-*` (skill source for the five lifecycle processes)
- `dataset/skills/mechanic/mechanic-vault-*` (skill source for vault-shape primitives)
- Brand assets (logo system, palette, typography, hero, OG card)
- `tools/{eslint,prettier,markdownlint,ts}-config/` (shared linting + formatting)
- Public surfaces: GitHub repo metadata, README, CONTRIBUTING, npm package metadata

## Team Alignment

Single-contributor in v1 (Gianluca). One external dependency: brand identity delivered via Claude Design on a curated brief. Profile required: full-stack (Node CLI, Next.js/MDX, GitHub Actions, design-system basics). Coordinated tightly with Vault Runtime via the on-disk contract — every change to dataset layout or manifest schema is a joint design step.

Future split (post-v1): a release/DevEx engineer could own this context independently, since the contract with Vault Runtime is the only interface to maintain.

## Ubiquitous Language

| Term            | Definition                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| CLI             | The npm-distributed `gilberto` binary. Scope is closed to `install` / `update` / `status` / `plugin {...}`.                          |
| Instance        | A user's vault (`$GILBERTO_ROOT`) created by `gilberto install` and maintained by `gilberto update`. Distinct from the repo.        |
| Bootstrap       | The one-shot setup of an instance: scaffolds 5 pillars + network + anatomy + `.envrc` + launchd plists. Refuses to re-run.          |
| Upgrade         | The pull-and-merge of new dataset versions into an existing instance, preserving customisations via fork-on-write.                  |
| Migration       | A backwards-incompatible shape change applied to the vault, gated by `--dry-run`, with a pre-migration snapshot for rollback.       |
| Adapter         | A distribution translator from the canonical dataset to a per-runtime format (Anthropic marketplace, Codex, generic drop-in).        |
| Release Action  | The GitHub workflow firing on git tag: builds the npm package, deploys the website, generates and indexes release notes.            |
| Manifest        | The plugin descriptor (`.claude-plugin/plugin.json`); also any source-of-truth schema describing what a CLI command writes on disk. |
| Brand identity  | The cohesive visual system (logo, palette, typography, hero, OG card) applied across website, CLI banner, and GitHub repo.          |

## Quality Attributes

- **Performance:** `gilberto install` completes in under 5 minutes on supported platforms (PRD §4 KPI). CLI commands return within 2 seconds for in-vault operations (PRD §8). Website Lighthouse scores green on all four metrics at v1.0 launch.
- **Scalability:** single-user single-instance; no multi-tenant. Release pipeline scales with the number of supported AI assistants (one adapter per runtime). Website content scales with documentation depth, not user count.
- **Reliability:** install/upgrade are idempotent; failures leave the vault in a recoverable state (snapshot + rollback for migrate). The CLI ships pre-built where Node version matrix risks exist (PRD §11). Release pipeline runs in green on every tag or the release is rolled back.
