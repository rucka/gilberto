# UX / UI

## Surfaces

- CLI (`gilberto`) — install / update / manage
- AI assistant skills (Claude Code primary, Codex / others) — daily interaction
- Vault filesystem rendered in Obsidian (optional)
- Website (`apps/website/`) — landing + docs

## Interaction Principles

- Conversational over procedural — no path/pillar/type/frontmatter exposed to user
- Confirm + silence-learned — silence persisted in `anatomy/preferences.md > ## Silence`
- Semantic feedback (user terms, not paths)
- On-demand always available — process skills invocable in 4 modes (scheduled / event / on-demand procedural / on-demand conversational)
- Tone: personal assistant / butler; warmth + structure

## CLI

- Structured + color-aware output; respects `NO_COLOR`; degrades on non-TTY
- Confirmations for destructive ops (`update`, `plugin remove`, `vault-migrate`)
- `--verbose` / `-v`: prints every file written and skill installed
- ASCII banner ≤80 cols, brand-consistent
- `gilberto --help`, `gilberto <command> --help`

## Vault (Obsidian-Native)

- Folder-notes: `<name>/<name>.md` for entities; `index.md` for containers
- Wikilinks: bare basename when unique; path otherwise
- Frontmatter: `type`, `topics`, `created`, `updated` mandatory
- `topics` constrained (`anatomy/topics.md`); `tags` free kebab-case (Obsidian nesting OK)
- Daily journey sections: `## Journal`, `## Sunto`, `## Agenda`, `## Link del giorno`, `## Sparks`
- No required Obsidian plugins

## Website

- Fumadocs (Next.js + MDX)
- Sections: hero + install CTA · features · install · quickstart · architecture · plugin gallery · releases · glossary · FAQ
- Sidebar by topic
- Custom theme on brand identity (not vanilla Fumadocs)
- OG card 1200×630

## Brand Identity

- Tone: alive, expressive, warmth + structure (not corporate/sterile)
- Delivery: dedicated Claude Design study (curated brief; ≥2 concept iterations; rationale documented)
- Outputs: logo system (mark + wordmark, light/dark) · palette · type pair · hero illustration · OG card · CLI ASCII banner
- Tokens exported as CSS variables + JSON
- Applied cross-surface: website · CLI banner · GitHub social preview · README header

## Accessibility

- Logo readability ≥16px; light + dark variants
- Website WCAG 2.1 AA
- CLI: `NO_COLOR` honored; non-TTY graceful

## Device & Browser Support

- Website: latest 2 majors of Chrome / Firefox / Safari / Edge; mobile-first responsive
- CLI: macOS primary, Linux supported; Windows out of v1
- Obsidian: desktop official; mobile best-effort

## I18n

- UI language: English (CLI, website, skill descriptions)
- User content: vault is user-language; EN↔IT translation via `utility-translate`
- No website i18n in v1

## Out of v1

Web UI for vault · mobile companion · custom Obsidian plugin · visual builder.

## References

- [`../product/PRD.md`](../product/PRD.md) §9
- Peers: [`architecture.md`](architecture.md) · [`tech-stack.md`](tech-stack.md) · [`infrastructure.md`](infrastructure.md)
