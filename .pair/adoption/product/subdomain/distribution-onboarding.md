# Distribution & Onboarding (Supporting Subdomain)

> Classification: **Supporting**

**Business Purpose:**
Get gilberto from the monorepo to the user's filesystem in <5 minutes, with coherent visual identity and navigable public documentation. Covers packaging, release automation, doc site, brand identity, AI-assistant runtime adapters.

**Key Capabilities:**

- npm CLI `gilberto` (commander/yargs) with closed scope: `install` / `update` / `status` / `plugin {...}`
- Distribution adapters per runtime (Claude Code marketplace, Codex best-effort, generic drop-in)
- Fumadocs website (Next.js + MDX) — landing + reference docs + auto-generated releases index — under `apps/website/`
- GitHub Release Action — on tag: build+publish npm, deploy website, generate release notes from CHANGELOG, append to Releases index
- Brand identity (logo mark+wordmark, palette, typography, hero illustration, OG card) delivered via Claude Design on a curated brief
- ASCII CLI banner consistent with the brand mark
- Quickstart + architecture deep-dive + plugin author guide + FAQ (`apps/website/content/`)

**Strategic Importance:**
Required for the public launch (PRD §6 P0#7+P0#8 + §10 Phase 4 M6). Without a public surface and coherent identity there is no credibility. Yet it is not what brings users back: it is a one-shot adoption enabler.

**Complexity Assessment:**
Medium — custom Fumadocs theming, brand consistency across surfaces (site + CLI + GitHub), multi-target release pipeline (npm + Pages/Vercel + release notes), CLI test matrix (macOS/Linux × Node 20/22), per-assistant adapter with surface compatibility.

**Data Ownership:**
`apps/cli/` (CLI source + adapters), `apps/website/` (Fumadocs site + MDX content), `.github/workflows/release.yml`, `.changeset/`, brand assets (logo + design tokens), `tools/{eslint,prettier,markdownlint,ts}-config/` shared linting/formatting.

**Dependencies:**

- Depends on: Vault Lifecycle (CLI install invokes bootstrap), External Integrations (release pipeline touches npm registry + Pages/Vercel deploy)
- Provides to: every runtime subdomain (it is the channel that delivers them to the user), Plugin Ecosystem (CLI host + marketplace conventions)

**Team Recommendations:**
Single-contributor in v1, with one external dependency: brand identity delegated to Claude Design (curated brief, multiple iterations). Profile: full-stack (Node CLI, Next.js/MDX, GitHub Actions, design-system basics).

**Implementation Priority:**
Medium for CLI scaffold (Phase 1, M1); High for release+website+brand (Phase 4, M6). Blocking for public launch — no M6 without a presentable surface.
