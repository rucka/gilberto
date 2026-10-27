# External Integrations (Generic Subdomain)

> Classification: **Generic**

**Business Purpose:**
Pull data from external providers (calendar, mail, wearables, RSS, content feeds) and push to the outside world (calendar create-event, email send) through standard OAuth+API utilities, isolated from the core and fall-back-friendly.

**Key Capabilities:**

- Single cross-pillar dispatcher `gilberto-capability-fetch` (D-40), with default RSS plus utility-overrides registered in anatomy
- Connector plugins per provider family ([ADR-0003](../../tech/adr/0003-connector-plugins.md)): `connector-google` (Gmail, Calendar via `gcalcli`, Drive), `connector-media` (YouTube + transcript), `connector-slack` in v1; Notion, GitHub, messaging, social post-v1
- Uniform utility contract `utility-<provider>-<op>`, API-first deterministic scripts, MCP fallback
- `utility-fetch-oura` (Oura Ring OAuth2 + API v2) — first-party plugin
- `utility-fetch-withings` (Withings OAuth2 + API) — first-party plugin
- `utility-fetch-rss` (generic Atom/RSS)
- External I/O utilities for ACT (`utility-email-send`, `utility-slack-send`, `utility-calendar-create-event`)
- Secrets in OS keychain (fallback `~/.config/gilberto/secrets/`, outside vault); `utility-secrets-{export,import}`; non-secret config `anatomy/integrations/<provider>.md`

**Strategic Importance:**
Commodity. Standard OAuth+pull/push pattern, already implemented by dozens of tools. Not differentiating; the value lies in routing+context (Cognitive Operations), not in the fetch itself. Isolated in utilities so manual fallback (drop into `_ingest/`) remains possible if a provider revokes.

**Complexity Assessment:**
Medium — per-provider OAuth flow, rate-limiting, schema mapping, error handling with retry+backoff, upstream breaking changes. Rigidity is external (provider APIs), not architectural.

**Data Ownership:**
Skills under `plugins/gilberto-core/skills/` (provider-free: fetch dispatcher, RSS, HTML) and `plugins/connector-<family>/skills/`. State-machine sidecars (`_state.json`). Secrets outside the vault. **Not** ingested data (which lives in Personal Knowledge Graph).

**Dependencies:**

- Depends on: Adaptive Anatomy (preferences for OAuth + sync cadences, source registry in playbooks)
- Provides to: Cognitive Operations (CAPTURE pull + ACT push), Plugin Ecosystem (`pulse-health-tracking` and `pulse-ratko` plugins consume wearable utilities)

**Team Recommendations:**
Single-contributor in v1. Profile: integration-engineer (OAuth, REST API, rate-limiting). Mitigation for PRD §11 risk (provider revoke): isolated utilities, multiple providers per source-type, manual fallback.

**Implementation Priority:**
Medium — calendar/mail in PRD Phase 4 (M5); wearables in Phase 3 (first-party plugin, M4); baseline RSS in Phase 2 (M2). User migration scripts (P2) post-v1.
