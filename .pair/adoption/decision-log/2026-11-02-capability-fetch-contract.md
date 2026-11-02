# ADL — capability-fetch dispatcher contract

**Date:** 2026-11-02
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** `plugins/gilberto-core/skills/gilberto-capability-fetch`

## Context

Story #71 implements the ADR-0003 dispatcher before the connector contract/resolver (#60) and the utilities (#72, #73) exist. The ADR fixes routing (`provider:` else `type`), `fallback: mcp|none`, `_state.json` per source and typed errors; it leaves the utility call shape, state location and fallback delivery open.

## Decision

- **Precedence**: `provider:` wins over `type`.
- **Utility name**: `utility-<provider|type>-read`; core table only for `rss`/`atom` → `utility-fetch-rss`, `http` → `utility-download-html`. Search path: core skills dir + `$GILBERTO_UTILITY_PATH`. Provider/type is _known_ when its utility exists, `anatomy/integrations/<key>.md` exists or the entry sets `fallback:`; else `UNKNOWN_PROVIDER` / `UNKNOWN_TYPE`. No provider list in core.
- **Call**: `script.py --url=<url> [--profile=<p>]`, stdout `{items:[{id, markdown}]}`, failure → exit ≠ 0 + `{errors:[{code}]}` (surfaced as `UTILITY_ERROR`, `utility_code`). Items carry normalized markdown + canonical frontmatter (ADR-0003 anti-corruption); core writes it as-is.
- **Profile**: entry `profile:` passed through; omitted → `resolve_profile()` seam, stubbed (`None`) until #60 merges — swap the body, signature unchanged.
- **Fallback**: entry `fallback:`, else `anatomy/integrations/<provider>.md` frontmatter, default `none`. A script cannot call MCP, so `mcp` is delivered as a `skipped` entry (`reason: mcp-fallback`) the assistant acts on; `none` → `reason: manual` + `_ingest/` hint. Neither counts as failure.
- **State**: `anatomy/playbooks/<pillar>/sources/<contributor>/_state.json` = `{url: {fetched: [ids]}}`; one file per source file, keyed per entry url (overturn: single global file).
- **Output files**: `_ingest/<contributor>-<sha1(url,id)[:12]>.md`.

## Alternatives Considered

- Hard-coded provider list in core: rejected — violates "no provider code in core".
- State inside `_ingest/`: rejected — story rule keeps `_state.json` apart from ingested content.

## Consequences

- #60/#72/#73 must honour the call shape or amend this log.
