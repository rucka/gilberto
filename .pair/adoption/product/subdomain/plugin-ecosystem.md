# Plugin Ecosystem (Supporting Subdomain)

> Classification: **Supporting**

**Business Purpose:**
Allow framework extension via opt-in plugins that add skills, templates, and playbooks to an existing instance — without forking the core. Enables 4 first-party plugins + a community marketplace post-v1.

**Key Capabilities:**

- Plugin protocol (Anthropic-compatible manifest `.claude-plugin/plugin.json` + per-runtime adapter)
- CLI lifecycle (`gilberto plugin {list,enable,disable,install,update,remove}`)
- Runtime registry (`anatomy/plugins.md`) — kind, version, routes
- Routing rules for kind-specific delegation from universal processes (`next`, `surface`, `reflect`)
- File-per-contributor merge under `anatomy/playbooks/<domain>/` between core and plugins
- 4 first-party plugins: `projects-venture` (11 phases), `projects-editorial` (5 capabilities), `pulse-health-tracking` (Oura+Withings), `pulse-ratko` (Ratko-app)
- External install from a GitHub URL with `--select <name>` for multi-plugin repos

**Strategic Importance:**
Extensibility for community growth and vertical coverage (fitness, editorial, business) without bloating the core. PRD KPIs: ≥3/4 first-party enabled by ≥50% of testers; 10 community plugins in 12 months. Necessary for long-tail adoption but not for the initial single-user case.

**Complexity Assessment:**
Medium — versioned manifest schema, conflict detection during enable/disable (vault entities depending on the plugin), file-per-contributor merge, routing dispatch, plugin discovery (Anthropic marketplace + self-hosted + GitHub URL).

**Data Ownership:**
Skills `gilberto-process-projects-{venture,editorial}-*` (plugin processes), plugin capabilities under `dataset/plugins/<plugin-name>/skills/`. `anatomy/plugins.md` registry. CLI `apps/cli/src/plugin/` commands. Plugin manifest schema (Zod).

**Dependencies:**

- Depends on: Adaptive Anatomy (registry + routing rules + file-per-contributor merge), Vault Lifecycle (mechanic primitives for plugin content scaffolding), Distribution & Onboarding (CLI host + Anthropic marketplace conventions)
- Provides to: Cognitive Operations (delegation via routing), Personal Knowledge Graph (pillar-specific extensions via templates)

**Team Recommendations:**
Single-contributor in v1; designed for external plugin author onboarding. "Plugin author guide" documentation (PRD §12 Support). Profile: platform-engineering (protocol design, semver, conflict resolution).

**Implementation Priority:**
Medium — PRD Phase 3 (M4). Blocked by stable Cognitive Operations (delegation pattern) and mature Adaptive Anatomy (registry semantics). Community marketplace P2 post-v1.
