# External Connectivity Context

> Type: **Infrastructure**

## Subdomains Covered

- External Integrations
- Scheduling Infrastructure

## Business Scope and Purpose

The thin commodity layer that connects gilberto to the outside world: OAuth + REST adapters for calendar / mail / wearables / RSS, outbound action utilities (send email, create event, post message), and OS-level scheduling (launchd / cron / systemd) plus AI-assistant lifecycle hooks. The two subdomains are grouped because both are *generic* — implementations are commoditised, the differentiation is *negative* (decoupled from a specific provider, decoupled from the AI assistant) — and both expose their value through the same interface: a vault-agnostic utility callable by Vault Runtime capabilities, plus an event source that triggers runtime invocations.

Strategic stance (PRD §6 P0#4 + D-37 §3.3): *no cloud backend; the AI assistant is the skill engine, not the scheduler*. This context is what enforces both stances. Utilities are isolated and replaceable; provider revocations fall back to manual `_ingest/` drops; scheduling never assumes the AI assistant is running.

## Relationships Between Bounded Context and Sub Domains

- **External Integrations** provides utilities (`utility-fetch-{rss,gmail,oura,withings}`, `utility-calendar-gcalcli`, `utility-email-send`, `utility-slack-send`, `utility-calendar-create-event`) that are invoked synchronously by the cross-pillar dispatcher `gilberto-capability-fetch` and by ACT capabilities. Provider state machines (where required) live in JSON sidecars (`_state.json`).
- **Scheduling Infrastructure** generates and registers `~/Library/LaunchAgents/com.gilberto.*` plists (macOS) / cron entries / systemd user timers (Linux) at bootstrap, and provides Claude Code hooks (SessionStart / PreCompact / SessionEnd). It does not execute skills directly; it triggers them.
- Cross-context: this context **provides** data and event triggers to Vault Runtime; it **is consumed by** Distribution & Lifecycle only at release time (npm registry publish, Pages/Vercel deploy — not part of runtime).

## Integration Patterns

- **Synchronous in-process** with Vault Runtime — utilities are invoked as direct skill calls within a single capability execution. No service boundary; the result returns to the caller and is then routed to the appropriate pillar by Cognitive Operations.
- **Asynchronous trigger** to Vault Runtime — launchd / cron / systemd fires skill invocations at the cadences declared in `anatomy/preferences.md > ## Cadenze`. Hooks (Claude Code SessionStart / PreCompact / SessionEnd) provide an additional event source.
- **Anti-corruption layer per provider** — each utility isolates a single provider's surface (Oura v2, Withings, Gmail, Google Calendar). Schema mapping happens inside the utility; capabilities downstream never see provider payloads. Replacing a utility (e.g., another wearable provider) does not touch capabilities.
- **OAuth tokens user-managed** — tokens live in `anatomy/preferences.md > ## Integrations`, never in code or external storage. Utilities read tokens at invocation; refresh logic is per-utility, with retry+backoff.
- **Outbound rate-limit + backoff** at the utility level; failures bubble up to capabilities as typed errors that the orchestrator can route into `_ingest/` `.error.md` sidecars or surface to the user.

## Data Ownership

- `dataset/skills/utility/utility-fetch-*` and `dataset/skills/utility/utility-{email,slack,calendar}-*` skill source
- Provider state-machine sidecars (`_state.json`) co-located with the synced source
- Generated launchd plists under `~/Library/LaunchAgents/com.gilberto.*` and equivalent Linux units (cron tab entries / `systemd/user/` units)
- AI-assistant lifecycle hook scripts (Claude Code `SessionStart` / `PreCompact` / `SessionEnd`)
- **Not owned**: OAuth tokens (user-managed in `anatomy/preferences.md`); ingested payloads (owned by Personal Knowledge Graph in Vault Runtime).

## Team Alignment

Single-contributor in v1. Profile: integration-engineer mindset (OAuth, REST, rate-limiting) plus minimal sysadmin (launchd/cron/systemd). Mitigation for PRD §11 risk (provider revoke API access): utilities are isolated, multiple providers per source-type are supported, and a manual fallback always remains (drop into `_ingest/`).

Future split: this is the easiest context to delegate to a contributor unfamiliar with the rest of the system, since utilities are small and self-contained. Linux porting of Scheduling Infrastructure is a medium-priority post-v1 task that fits the same profile.

## Ubiquitous Language

| Term              | Definition                                                                                                              |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Utility           | A vault-agnostic skill (`utility-*`) performing a pure function (fetch, send, convert).                                 |
| Provider          | An external service exposing data or accepting actions (Google Calendar, Gmail, Oura, Withings, Slack, RSS endpoint).   |
| Source            | A registered data origin in `anatomy/playbooks/<pillar>/sources/` that uses one or more utilities to keep itself synced. |
| State sidecar     | A `_state.json` file that stores per-source incremental sync state (cursors, last-fetch timestamps, pagination tokens). |
| Cadence           | A scheduled trigger declared in `anatomy/preferences.md > ## Cadenze` (cron-like); user-overridable.                    |
| Plist             | A macOS `launchd` user-agent definition under `~/Library/LaunchAgents/com.gilberto.*` generated at bootstrap.            |
| Hook              | An AI-assistant lifecycle event handler (Claude Code SessionStart / PreCompact / SessionEnd).                            |
| Manual fallback   | The user dropping a file into `_ingest/` when an automated utility is unavailable; ingest pipeline treats it identically. |

## Quality Attributes

- **Performance:** utility round-trips bounded by the upstream provider; gilberto adds <100 ms framing overhead. Scheduled triggers fire within 1 minute of the declared cadence in normal load.
- **Scalability:** scales with the number of registered sources × cadence frequency. Single-user constraint keeps the absolute volume small. Rate-limit budgets per provider are enforced at the utility.
- **Reliability:** failures are isolated to the failing utility — never cascade. Retry-with-backoff at the utility; after exhaustion, surface a typed error to the caller. Tokens stored locally only; no token replication across machines means a re-auth is required per machine but mitigates leakage. Linux/macOS scheduling parity tested per release.
