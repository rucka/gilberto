# Product Requirements Document (PRD)

## 1. Overview

**Product Name:** gilberto — Personal AI-Native Second Brain
**Version:** 0.1
**Date:** May 01, 2026
**Owner:** Gianluca Carucci

### Executive Summary

gilberto is a personal AI-native second brain that lives in the user's filesystem (markdown + JSON), orchestrated by skills compatible with **any AI assistant** (Claude Code, OpenAI Codex, Cowork, and others) and **any model**. It helps the user make better decisions by remembering everything they've lived, learned, and planned — without vendor lock-in (neither cloud, nor AI provider, nor model), with full data sovereignty, and with a memory that compounds over time.

## 2. Product Vision & Mission

### Vision

Become the default personal assistant for AI-savvy knowledge workers who want their own digital twin: a memory and decision-support system that lives in their filesystem, grows with them, and never depends on a third-party cloud.

### Mission

Give a person an assistant that knows them, remembers them, anticipates their next step, and frees them from daily operational friction — while preserving full sovereignty over their data.

Three practical consequences:

1. **Better decisions, faster.** gilberto knows what the user has lived, what they're doing, what they've learned. When a decision is needed, the context is already there.
2. **Minimal operational friction.** Morning briefings, pre-meeting dossiers, weekly consolidations, mail/task triage: daily noise dissolves into automatic or semi-automatic routines.
3. **A memory that grows with you.** Every conversation leaves a trace. Preferences emerge from dialogue, not from initial configuration. The system learns how the user prefers to work.

## 3. Problem Statement

### Current State

Knowledge workers manage their lives across fragmented tools — notes apps, calendars, email, wearables, document storage, project management — each siloed and vendor-locked. AI assistants exist but are stateless, generic, and live behind paywalled APIs that own the conversation history. Personal knowledge does not compound; it scatters and decays.

### Pain Points

- **Fragmented context:** Information lives in N different SaaS apps; none of them sees the whole picture of the user's life.
- **Vendor lock-in:** Notes, conversations, and personal data are hostage to proprietary clouds and APIs that can change pricing, terms, or shut down.
- **Stateless AI assistants:** Generic LLM chat interfaces start every conversation from zero. They don't remember decisions, projects, relationships, or learnings.
- **Operational friction:** Routine work (planning the day, summarizing the week, classifying incoming material) consumes attention better spent on real decisions.
- **Knowledge doesn't compound:** Notes pile up but rarely connect; insights remain isolated; the second brain promised by tools-of-thought rarely materializes in practice.

## 4. Goals & Success Metrics

### Primary Goals

1. Deliver a personal second brain that runs entirely on the user's filesystem with no required cloud backend, maintaining full data sovereignty.
2. Reduce daily operational friction (planning, triage, consolidation) to a near-zero touch baseline through scheduled and on-demand AI routines.
3. Provide a framework that other AI-savvy users can install and personalize via opt-in plugins — not a single-tenant tool tied to one author's stack.

### Success Metrics (KPIs)

- **Bootstrap-to-running time:** Target: under 5 minutes from running the install command (recommended user-friendly path, with npm/Homebrew/native installer as alternatives) to a populated vault with morning-briefing scheduled.
- **Daily active routines:** Target: morning-briefing + reflect-day executed at least 5 days/week per user (own use, then external testers).
- **Plugin install/disable ratio:** Target: at v1.0, ≥3 of the 4 first-party plugins are enabled by ≥50% of testers.
- **Skill catalog growth:** Target: ~90 skills delivered by v1.0 (split across the four categories: process, capability, utility, mechanic).
- **Issue resolution:** Target: critical bugs resolved within 1 week post-v1.0 release.
- **Public adoption (long-tail):** Target: 100 GitHub stars in 6 months post v1.0; 10 community-contributed plugins in 12 months.

## 5. Target Users

### Primary Users

**User Persona 1:** AI-Savvy Knowledge Worker (30-50 years)

- Demographics: Senior IC, tech lead, or independent professional. Comfortable with CLI tools, markdown, and OSS workflows. Already uses an AI assistant (Claude Code, Codex, Cowork, or similar) and is fluent across models.
- Needs: A coherent personal knowledge layer that survives across years and life phases. Wants to control where data lives. Values composability and version control.
- Behaviors: Maintains a personal note-taking system (Obsidian, Logseq, plain markdown). Uses Dropbox/iCloud for sync. Reads productivity/AI content. Tinkers with personal workflows.

**User Persona 2:** Privacy-Conscious Power User (25-45 years)

- Demographics: Software engineer, researcher, founder. Concerned about vendor lock-in and SaaS data hostage situations. Has tried multiple "tools of thought" without sticking.
- Needs: A second brain that compounds value without surrendering data to a third party. Wants AI-assisted but not AI-dependent.
- Behaviors: Self-hosts services when reasonable. Reads about agentic AI, local LLMs, knowledge graphs. Active in OSS communities.

### User Journey

User reads/hears about gilberto → installs CLI via npm → runs `gilberto install ~/Dropbox/Gilberto` → answers a few bootstrap questions (topics, plugins) → vault is populated with anatomy templates → opens it in Obsidian to navigate → drops a PDF into `_ingest/` and watches it get classified → schedules morning-briefing → next morning gets a contextual summary in their daily note → over weeks, the vault accretes context (mail summaries, weekly consolidations, project status) → decisions feel cheaper because the context is always one prompt away.

## 6. Solution Overview

### Core Solution

A monorepo (`rucka/gilberto`) that ships a CLI npm package (`gilberto`) plus a dataset of skills, plugins, and templates. The CLI bootstraps and updates a user-owned vault (an "instance" of Gilberto). The vault is a markdown + JSON filesystem structured into 5 pillars (`me/`, `pulse/`, `projects/`, `intelligence/`, `journey/`), a transversal `network/` (people + companies), and an `anatomy/` system layer. Skills installed into the vault are **AI-assistant-agnostic** (Claude Code, Codex, Cowork, etc.) and **model-agnostic** — they read/write/classify/recall/connect, orchestrated by 11 process skills and extended via opt-in plugins.

### Key Features

#### Must-Have (P0)

1. **CLI installer (`gilberto install`):** Interactive bootstrap that creates the vault, populates anatomy templates, configures hooks, and registers schedules.
2. **Vault structure (5 pillars + network + anatomy):** Filesystem-as-database, navigable in Obsidian or any markdown editor.
3. **11 core processes:** `ingest`, `structure`, `surface`, `act`, `reflect`, `next`, plus 5 lifecycle (`vault-bootstrap`, `vault-upgrade`, `vault-migrate`, `vault-export`, `vault-archive`). Drive the operating cycle.
4. **`gilberto-capability-fetch` cross-pillar dispatcher:** Universal source-fetcher with default scripts (RSS) plus utility-overrides registered in anatomy (Oura, Withings, calendar, mail, etc.).
5. **Anatomy as operating manual:** Data-driven `playbooks/` + `preferences/` + `templates/` files that govern process behavior without hard-coding.
6. **Plugin protocol:** First-party + external plugins installable via CLI. Anatomy registry (`anatomy/plugins.md`) tracks state and routing.
7. **Landing page + documentation site with coherent brand identity:** Fumadocs-based site (`apps/website/`) with landing page (hero + features + install CTA), reference documentation (architecture, processes, plugin authoring, glossary), auto-generated releases index, and a **coherent visual identity**: logo (mark + wordmark), color palette, typography, hero illustration, OG card. Logo and identity delivered via Claude Design on a curated brief; same identity applied across website, CLI banner, and GitHub repo. Without a presentable public surface and consistent visual identity, the framework cannot launch publicly with the credibility required to attract external users.
8. **GitHub Release Action (CI/CD for distribution):** Automated workflow that on every release tag (a) builds and publishes the npm CLI package, (b) builds and deploys the website (landing + docs) to GitHub Pages or Vercel, (c) generates release notes from `CHANGELOG.md`, (d) appends the release to the website's "Releases" index. Without release automation, distribution is manual and fragile — incompatible with a public launch.

#### Should-Have (P1)

1. **Four first-party plugins:** `projects-venture` (venture-build framework), `projects-editorial` (content pipeline), `pulse-health-tracking` (wearable data: Oura, Withings), `pulse-ratko` (Ratko-app integration for fitness coaching).
2. **Calendar + Task + Mail integration:** Journey extended with `## Agenda` section. `gilberto-capability-journey-tasks` for task CRUD. `gcalcli`-backed Google Calendar sync. Lightweight email pull on demand.
3. **CLI plugin commands:** `gilberto plugin {list, enable, disable, install, update, remove}`.

#### Could-Have (P2)

1. **Community plugin marketplace:** Discovery and install from a curated list of community-contributed plugins.
2. **Ollama integration:** Optional local-LLM runtime for fully offline reasoning.
3. **Migration utilities:** Scripts to import content from existing tools (Obsidian vaults, Notion, Apple Notes, Logseq).
4. **Mobile companion app:** Read-only mobile view of the vault for on-the-go briefings.

## 7. User Stories & Acceptance Criteria

### Epic 1: Bootstrap & Core Vault

**User Story 1.1:** As a new user, I want to install gilberto and bootstrap a vault in under 5 minutes so I can start using it without a long setup.

- **AC1:** The recommended install path (user-friendly install method TBD — see project distribution decisions; alternatives: `npm install -g gilberto`, Homebrew, native installer) succeeds on supported platforms (macOS, Linux).
- **AC2:** `gilberto install <target>` prompts for vault location, topic seeds, and plugin opt-in choices.
- **AC3:** On completion, vault contains the 5 pillars, anatomy, `_ingest/`, and `.claude/skills/` populated with all core skills.
- **AC4:** Verbose mode (`-v`) prints every file written and skill installed.

**User Story 1.2:** As a user, I want to drop a file into `_ingest/` and have gilberto classify and archive it automatically.

- **AC1:** Filesystem watch on `_ingest/` triggers `gilberto-process-ingest`.
- **AC2:** Confidence ≥ threshold → classified and routed to the correct pillar with sidecar.
- **AC3:** Confidence < threshold → file remains with `.classification.json` showing the proposal for human confirmation.

### Epic 2: Daily Operations

**User Story 2.1:** As a user, I want a morning briefing every day at 07:00 so I start with full context.

- **AC1:** launchd job triggers `gilberto-process-surface` with `morning-briefing` playbook at 07:00.
- **AC2:** Output written into the daily journey file under `## Agenda` (planned events + scheduled tasks) and a curated narrative summary.
- **AC3:** User can override the time in `anatomy/preferences.md > ## Cadenze`.

**User Story 2.2:** As a user, I want a daily consolidation at 22:00 so my day is summarized in narrative form.

- **AC1:** `gilberto-process-reflect` with cadence=day runs at 22:00 (configurable).
- **AC2:** `## Sunto` section of the daily journey is populated with cross-pillar summary.
- **AC3:** Optionally proposes evolutions to anatomy (new topics, new sources) when patterns are detected (`evolution-check`).

### Epic 3: Plugin System

**User Story 3.1:** As a user, I want to enable a plugin (e.g., `pulse-health-tracking`) and have its skills, templates, and playbooks installed in my vault.

- **AC1:** `gilberto plugin enable pulse-health-tracking` copies skill files to `.claude/skills/`, templates to `anatomy/templates/`, and playbooks to `anatomy/playbooks/`.
- **AC2:** `anatomy/plugins.md` is updated with the plugin entry (kind, version, routes).
- **AC3:** `gilberto plugin disable <name>` reverses the operation, with a warning if any vault entities depend on it.

**User Story 3.2:** As a user, I want to install an external community plugin from a GitHub URL.

- **AC1:** `gilberto plugin install <repo-url>` clones the repo, validates the manifest, and installs the plugin.
- **AC2:** For multi-plugin repos, `--select <name>` chooses which plugin to install.

### Epic 4: Calendar & Mail

**User Story 4.1:** As a user, I want my Google Calendar events to populate today's agenda automatically.

- **AC1:** `utility-calendar-gcalcli` fetches events for the next N days (configurable) at the cadence defined in preferences.
- **AC2:** Events are written into the `## Agenda > Eventi` section of the corresponding daily journey files.
- **AC3:** When the user explicitly schedules an event via `gilberto-process-act`, it is pushed to Google Calendar.

**User Story 4.2:** As a user, I want gilberto to surface action-required emails from Gmail at reflection time.

- **AC1:** `utility-fetch-gmail` is invoked on demand by `gilberto-process-reflect` (day) or `gilberto-process-next`.
- **AC2:** Action-required emails become tasks in `journey/tasks.md` with reference to the sender ([[network/people/...]]).
- **AC3:** Informational emails are summarized in the `## Sunto` of the day; no individual files stored.

## 8. Technical Considerations

### Architecture Overview

Monorepo (`rucka/gilberto`) using pnpm + turbo (pair-aligned). Top-level workspaces: `apps/cli/` (the CLI), `apps/website/` (Fumadocs documentation site), `tools/{eslint-config, markdownlint-config, prettier-config, ts-config}/` (shared linting/formatting/TS configs), and `dataset/` (skill, plugin, template sources). The dataset follows **standard skill/plugin formats compatible with AI assistants' native plugin systems** (e.g., Anthropic skills marketplace conventions); the CLI orchestrates installation rather than reinventing distribution mechanics. Skills run inside the **user's AI assistant of choice** (Claude Code, OpenAI Codex, Cowork, or any other AI assistant supporting markdown-driven skills) with **any underlying model** — they are written as portable markdown + scripts, not tied to a specific runtime. Deterministic operations are Python/Bash scripts orchestrated by skills. Anatomy (`anatomy/`) is a data-driven configuration layer that governs all process behavior.

### Key Technical Requirements

- **Performance:** CLI commands complete within 2 seconds for in-vault operations; bootstrap completes in under 5 minutes including download. Background processes (ingest, reflect) are async and non-blocking.
- **Security:** No data leaves the user's filesystem unless explicitly initiated by the user (e.g., `gilberto-process-act` pushes to calendar). OAuth tokens stored in vault `anatomy/preferences.md > ## Integrations` (user-managed). No cloud backend.
- **Scalability:** Single-user, single-vault. Vault should remain navigable up to ~10K markdown files. No multi-tenant requirements.
- **Integration:** AI assistants as skill runtime (Claude Code, OpenAI Codex, Cowork, and others — assistant-agnostic), Obsidian (visual layer, optional), Dropbox or iCloud (sync), OAuth providers (Google, Oura, Withings, Microsoft Graph), launchd (scheduling on macOS), pair-cli (knowledge base companion).
- **Reliability:** Every skill is idempotent (safe re-run). Vault upgrades preserve user customizations via fork-on-write pattern.

### Constraints

- **AI runtime:** Assistant-agnostic and model-agnostic. Works with Claude Code, OpenAI Codex, Cowork, and any AI assistant supporting markdown-based skills, on any underlying model. No lock-in to a specific AI provider. Skill format is portable; conventions follow common patterns (frontmatter + markdown body + optional scripts).
- **Platform:** macOS first (launchd, native scheduling). Linux supported. Windows not in v1 scope.
- **Single contributor:** One developer (Gianluca) initially; framework must remain comprehensible to a second contributor without long onboarding.
- **Time budget:** Estimated 200-240 dev-days from start to v1.0 (4 initiatives × ~5 epics × ~5 user stories each).
- **No external paid services:** Project must run end-to-end on free tiers / user-owned tooling for v1.

## 9. Design Requirements

### UI/UX Principles

- **Conversational over procedural:** The user never sees paths, frontmatter, or naming conventions; they interact in natural language.
- **Minimum surface, maximum value:** CLI commands are few and predictable (`install`, `update`, `status`, `plugin <action>`). Vault interaction is markdown-native via Obsidian or any editor.
- **Confirm + silence learned:** All consequential actions require user confirmation; preferences are learned, not configured upfront.
- **Tone:** Personal assistant / butler. Warmth + structure. Not a "cold AI app".

### Visual Requirements

- **Logo + identity — alive, with personality:** gilberto is an assistant, so the visual identity must convey **personality and character**, not a cold/corporate/sterile brand. The system should feel **alive**: expressive marks, recognizable visual character, hints of motion or organic form, warmth + structure together (not warmth at the expense of clarity, nor structure at the expense of soul). Italian historical resonance ("brilliant", "companion") informs tone but isn't decorative. Functional constraints: readable at 16px, monogrammable in light/dark, OG-card friendly. **Delivered via a dedicated Claude Design study** (curated brief, multiple iterations, downstream applied across website, CLI banner, and GitHub repo).
- **Documentation site:** Fumadocs-based, Next.js + MDX. Clean typography, generous whitespace. Hero with install CTA, sidebar navigation by topic. The site **inhabits the brand identity** (color, typography, illustration) — not a vanilla Fumadocs theme.
- **CLI output:** Structured, color-aware, progress indicators. Conversational confirmations for destructive operations. ASCII banner for the CLI consistent with the brand mark.
- **Vault visualization:** Optimized for Obsidian rendering (folder-notes, wikilinks, frontmatter consistent across pillars).

## 10. Timeline & Milestones

### Development Phases

**Phase 1: Foundation** (Weeks 1-4 from project start)

- Monorepo + CI/CD baseline
- CLI scaffolding
- 9 mechanic primitives (`vault-new`, `vault-promote`, `forge-*`)
- `gilberto-process-vault-bootstrap` interactive wizard
- **M1:** User can install CLI and bootstrap an empty vault.

**Phase 2: Core Vault & Processes** (Weeks 5-12)

- `gilberto-process-ingest` + `gilberto-capability-fetch` + first utilities (`fetch-rss`, `classify-medical`)
- `gilberto-process-structure` + per-pillar refresh capabilities
- `gilberto-process-surface` + per-pillar summarize capabilities
- `gilberto-process-reflect` with consolidate-day playbook
- `gilberto-process-act` + `gilberto-process-next`
- CRUD-homogeneous capabilities (network-people, anatomy-topics, etc.)
- Lifecycle processes (`vault-upgrade`, `vault-migrate`, `vault-export`, `vault-archive`)
- **M2:** Drop file in `_ingest/` → archived in correct pillar with sidecar.
- **M3:** Morning-briefing 07:00 + reflect-day 22:00 working end-to-end.

**Phase 3: Plugins** (Weeks 13-20)

- Plugin protocol implementation (manifest, CLI commands, registry, routing)
- `pulse-health-tracking` plugin (Oura + Withings)
- `pulse-ratko` plugin (Ratko-app integration)
- `projects-venture` plugin (11 phase capabilities + 2 plugin processes)
- `projects-editorial` plugin (5 capabilities + 4 plugin processes)
- **M4:** All four first-party plugins installable via CLI and functional.

**Phase 4: Calendar/Mail + Distribution** (Weeks 21-28)

- `gilberto-capability-journey-tasks` + Calendar/Mail integration via extended `gilberto-capability-fetch`
- `utility-calendar-gcalcli` primary
- `utility-fetch-gmail` lightweight
- CLI npm release (v0.1.0-alpha)
- GitHub Release Action
- Fork-on-write pattern for anatomy customizations during upgrade
- Documentation site (Fumadocs) at `apps/website/`
- Logo + visual identity via Claude Design
- Migration scripts for author's existing content (my-intelligence, ratko-mvp)
- **M5:** Daily agenda populated from Google Calendar + scheduled tasks.
- **M6:** External user can run the recommended install path (e.g., `curl ... | sh` wizard, or `npm install -g gilberto`, etc.) followed by `gilberto install` and obtain a working instance. v1.0 public release.

### Dependencies

- **`@foomakers/pair-cli`:** Knowledge-base companion installed as devDep; planning workflow depends on it.
- **AI assistant skill runtimes:** Skills must remain compatible with the supported assistants (Claude Code, OpenAI Codex, Cowork, and others); changes in each provider's skill format must be tracked and tested.
- **launchd:** macOS scheduling; Linux equivalents (cron, systemd timers) for Linux support.
- **OAuth provider stability:** Google Calendar, Gmail, Oura, Withings APIs must remain accessible; breaking changes require utility updates.
- **Ratko-app:** External app dependency for `pulse-ratko` plugin (author's own project; coordinated changes).

## 11. Risks & Mitigations

| Risk                                                                    | Impact | Probability | Mitigation Strategy                                                                                  |
| ----------------------------------------------------------------------- | ------ | ----------- | ---------------------------------------------------------------------------------------------------- |
| AI-assistant skill format divergence (Claude Code vs Codex vs Cowork)  | High   | Medium      | Skills written in portable markdown + scripts; per-assistant adapters where needed; test matrix across supported assistants on each release. |
| OAuth provider revokes API access (Oura, Withings, Google)              | Medium | Low         | Utilities are isolated; fall back to manual `_ingest/` drops; multiple providers per source-type.    |
| Single-developer bottleneck delays v1.0                                 | High   | High        | Break work into small stories (pair-style); bias toward shipping P0 over P1; defer P2 indefinitely. |
| Self-development drag (gilberto used to develop gilberto, dogfooding)   | Medium | Medium      | Maintain a stable working branch separate from experimental; ensure CLI install always works for own use. |
| Plugin protocol design proves too rigid for community plugins           | Medium | Low         | Plugin manifest is YAML, easy to extend; document protocol versioning; keep protocol additive.       |
| User data corruption during vault-upgrade or fork-on-write              | High   | Low         | Snapshot pre-upgrade; rollback mechanism in `gilberto-process-vault-migrate`; explicit confirmation on destructive ops. |
| Distribution friction (CLI fails on common Node setups)                 | High   | Medium      | Test matrix (macOS/Linux × Node 20/22); ship pre-built binaries as fallback; clear error messages.  |
| Naming/architecture decisions made today don't survive v2 needs         | Medium | Medium      | Decision log already records the "why"; ADR/ADL adoption pattern (via pair) for new decisions.       |

## 12. Launch & Go-to-Market

### Launch Strategy

**Phase 1 — Personal use (M1-M4):** Author runs gilberto as own daily driver. Iterate based on lived friction.

**Phase 2 — Closed alpha (M5):** Invite 5-10 AI-savvy peers to install and provide feedback. Limited to inner circle.

**Phase 3 — Public v1.0 launch (M6):** Open-source release on GitHub with full website, install instructions, and a launch post. Soft, not hyped.

### Marketing & Communication

- **GitHub:** Public repo with comprehensive README, install instructions, changelog, and contributing guidelines.
- **Documentation site:** `gilberto.dev` (or similar) with hero, install, quickstart, architecture, plugin gallery.
- **Launch post:** Personal blog post explaining the philosophy (sovereignty, compounding memory, conversational over procedural). Cross-posted to Hacker News, X/Twitter, foomakers community.
- **Key messages:**
  - "Your second brain. In your filesystem. AI-native."
  - "Sovereignty + compounding memory = a better digital twin."
  - "Build it, plug it in, forget about it."

### Support & Documentation

- **Quickstart guide:** 5-minute install + first-day usage walkthrough.
- **Architecture deep-dive:** Reference for contributors and plugin authors.
- **Plugin author guide:** How to write a plugin (manifest, skills, templates, playbooks).
- **FAQ + troubleshooting:** Common install issues, permissions, OAuth setup.
- **GitHub Issues:** Single channel for bugs and feature requests; triage weekly.

## 13. Post-Launch

### Monitoring & Analytics

- **GitHub stars & forks:** Weekly, as a coarse adoption signal.
- **Install count across distribution channels (npm, curl-pipe wizard, Homebrew, etc.):** Weekly; flag drops or anomalies.
- **Issue volume + close rate:** Weekly; triage critical bugs within 1 week, others within 1 month.
- **Plugin adoption:** Survey or telemetry (opt-in only) on which first-party plugins are enabled by users.
- **Community contributions:** PRs, issue discussions, third-party plugin releases.

### Iteration Plan

- **Weekly:** Triage issues, merge PRs, ship patch releases.
- **Monthly:** Minor release with new skills/utilities or bug fixes; review roadmap.
- **Quarterly:** Major release with significant features (e.g., new plugin, calendar provider, etc.); update documentation site.
- **Pivot criteria:** If after 6 months post-v1.0 the only active user is the author, reassess go-to-market and consider repositioning (e.g., niche down to a specific persona like fitness/health quantified-self, or pair tightly with pair).
- **Future roadmap (v2+):** Ollama local-LLM integration, mobile companion, community plugin marketplace, multi-vault support (research/work separation), team-vault patterns.

---

## Appendix

### Research & Data

- **Discovery sources:** Cole Medin (AI-native workflows), Ben AI (vault patterns), Dario Vignali (delegation principle: "automate the unimportant to free time for the important"). Synthesized during Phase 1 discovery.
- **Reference projects:** [foomakers/pair](https://github.com/foomakers/pair) for monorepo + AI-native tooling pattern. Existing author projects (`my-intelligence`, `ratko-mvp`) absorbed as plugins.

### Mockups & Prototypes

- Visual identity: TBD via Claude Design on a curated brief covering tone, semantic references, constraints, and required outputs (logo system, palette, typography pair, hero, OG card).
- Documentation site mockups: TBD; will follow Fumadocs conventions adapted to gilberto branding.

### Additional Resources

- **Pair knowledge base:** `.pair/knowledge/` — operational guidelines and how-to flows.
- **Repository:** [github.com/rucka/gilberto](https://github.com/rucka/gilberto)
