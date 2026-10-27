# ADR-0003: Connectors as Installable Plugins with a Uniform Utility Contract

## Status

Accepted

## Date

2026-10-27

## Context

- Gilberto needs basic I/O tools: Gmail, Google Calendar, Google Workspace (Drive/Docs/Sheets), Slack, Notion, GitHub, Telegram, WhatsApp, Meta (Facebook/Instagram), LinkedIn, Reddit, YouTube (video + transcript), RSS/HTML.
- Today only a few are specified (`utility-fetch-{rss,gmail,oura,withings}`, `utility-calendar-gcalcli`, `utility-{email,slack}-send`, `utility-transcript-from-video`), all placed in core (`dataset/skills/utility/`, obsolete per ADR-0002).
- Credentials are inconsistent: `anatomy/preferences.md > ## Integrations` (infrastructure.md) vs `_secrets/google.env` (epic #27). Tokens in a synced markdown file are a leak risk.
- Most connectors are opt-in, provider-specific, and volatile (APIs change, ToS restrict scraping: LinkedIn, Meta, WhatsApp). Shipping all in core bloats it and couples releases to provider churn.
- Many assistants already expose MCP connectors (Gmail, Calendar, Slack, Notion, GitHub, Drive). Reimplementing them is waste; depending only on them breaks assistant-agnosticism (ADR-0002, PRD constraints).

## Options Considered

### Option 1: All connectors as core utilities

- **Pros**: one install; no plugin protocol dependency.
- **Cons**: bloated core; provider churn forces core releases; users carry unused credentials surface.

### Option 2: One plugin per provider

- **Pros**: maximal granularity.
- **Cons**: ~15 plugins; shared auth (Google OAuth, Meta Graph) duplicated; release overhead.

### Option 3: Connector plugins grouped by auth/provider family, uniform contract, API-first resolution

- **Pros**: opt-in; shared auth per family; core stays provider-free; deterministic scripts on official APIs keep agnosticism; MCP only as fallback.
- **Cons**: contract + resolution layer to design; two code paths (MCP, script) per connector.

## Decision

**Chosen: Option 3.**

### Packaging

| Plugin                  | Providers / utilities                                            | Notes                                   |
| ----------------------- | ---------------------------------------------------------------- | --------------------------------------- |
| `gilberto-core`         | `gilberto-capability-fetch` dispatcher, `utility-fetch-rss`, `utility-download-html` | only provider-free connectors |
| `connector-google`      | Gmail, Calendar, Drive/Docs/Sheets                               | shared Google OAuth; suggested at bootstrap (M5) |
| `connector-slack`       | Slack read/write                                                 |                                         |
| `connector-notion`      | Notion read/write                                                |                                         |
| `connector-github`      | GitHub issues/PR/repos read/write                                | `gh` CLI backend                        |
| `connector-messaging`   | Telegram (Bot/MTProto), WhatsApp (Business Cloud API)            | WhatsApp personal: unsupported (ToS)    |
| `connector-social`      | LinkedIn, Meta (Facebook/Instagram Graph), Reddit                | write = official APIs only; no scraping |
| `connector-media`       | YouTube video download + transcript, local video transcript      | `yt-dlp` + captions/Whisper fallback    |

v1.0 scope: `connector-google`, `connector-media`, `connector-slack`. Others backlog P2 (one epic each). Alternative providers (`caldav`, `icalbuddy`, Outlook/Graph, IMAP, Apple Mail) backlog P2.
| `pulse-health-tracking` | Oura, Withings                                                   | unchanged (domain plugin)               |

Source: `plugins/connector-<family>/` (marketplace plugins per ADR-0002). Enabled via `/plugin install` + registered in `anatomy/plugins.md`.

### Utility contract

- Naming: `utility-<provider>-<op>` with `op ∈ {read, search, write, send, delete}` (e.g. `utility-gmail-read`, `utility-slack-send`).
- Output: normalized markdown + canonical frontmatter (`type, source, created, ...`); provider payloads never leave the utility (anti-corruption layer).
- Writes: always go through `gilberto-process-act`; explicit user confirmation unless the op is allowlisted in `anatomy/integrations/<provider>.md > auto_write` (never for message sends).
- Errors: typed (`auth`, `rate-limit`, `not-found`, `provider`); retry+backoff inside the utility.
- Idempotent reads with incremental state in `_state.json` per source.

### Resolution order

1. Plugin script (Python/Bash) on official API or CLI (`gcalcli`, `gh`, `yt-dlp`) — deterministic, default.
2. Assistant MCP connector, only if the script is unavailable/unconfigured and `anatomy/integrations/<provider>.md` declares `fallback: mcp`.
3. Manual fallback: drop into `_ingest/`.

### Configuration and secrets

- Non-secret config (accounts, scopes, channels, cadence, `fallback: mcp|none`): `anatomy/integrations/<provider>.md` (supersedes `preferences.md > ## Integrations` for per-provider detail; preferences keeps only global switches).
- Secrets: OS keychain (macOS Keychain / libsecret) by default; fallback `~/.config/gilberto/secrets/<provider>.env` (`chmod 600`), **outside the vault** (vault is cloud-synced). Vault holds only references (`secret: keychain:gilberto/<provider>`). Never in markdown.
- Machine migration: `utility-secrets-export` / `utility-secrets-import` (age-encrypted bundle, passphrase; bundle never stored in the vault).
- Unattended runs (launchd/cron) never perform external writes: proposed actions land in `journey/tasks.md` as pending confirmation, approved via `next`. `auto_write` allowlists specific ops per provider (e.g. `calendar:create-event`), never message sends.
- Sources (what to pull, when) stay in `anatomy/playbooks/<pillar>/sources/` and reference a connector by `provider:`.

## Consequences

- New epic "Connector framework" (contract, resolution, secrets, dispatcher wiring) in Initiative #2, before #11 ingest beyond RSS.
- New epics per connector plugin; `connector-google` replaces utility scope in epic #27; `connector-media` absorbs `utility-transcript-from-video`.
- Adoption files aligned 2026-10-27: `subdomain/external-integrations.md`, `boundedcontext/external-connectivity.md`, `infrastructure.md`, `architecture.md`, PRD §8; epic #27 rescoped to `connector-google`.
- ToS-restricted operations (LinkedIn/Meta scraping, WhatsApp personal) explicitly out of scope.

## References

- [ADR-0001](0001-vault-self-sufficiency.md) · [ADR-0002](0002-distribution-and-dual-entry-bootstrap.md)
- [`../../product/subdomain/external-integrations.md`](../../product/subdomain/external-integrations.md)
- [`../boundedcontext/external-connectivity.md`](../boundedcontext/external-connectivity.md)
