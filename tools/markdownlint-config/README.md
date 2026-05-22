# @gilberto/markdownlint-config

Shared markdownlint configuration for the gilberto monorepo.

## Usage

Scripts (via bin wrappers):

```json
"scripts": {
  "mdlint:check": "markdownlint-check",
  "mdlint:fix": "markdownlint-fix"
}
```

The bin scripts auto-discover `.markdownlint.jsonc` and `.markdownlintignore` from this package.

## Files

- `.markdownlint.jsonc` — lint rules (strict JSON; comments stripped due to a `markdownlint-cli` parser limitation — see Rule rationale below)
- `.markdownlintignore` — ignored patterns (node_modules, dist, CHANGELOG.md, etc.)
- `bin/` — wrapper scripts (`markdownlint-check`, `markdownlint-fix`)

## Rule rationale

Documentation kept here because `markdownlint-cli@0.47.0` routes config through `run-con`, which uses strict `JSON.parse` and rejects `//` comments inside the JSONC file. Until upstream supports proper JSONC, rules live in pure JSON and their justification lives here.

| Rule | Setting | Why |
| --- | --- | --- |
| `default` | `true` | Base: enable every rule, opt out below per justification. |
| `MD003` | `{ "style": "atx" }` | Heading style — ATX only (`#`), not setext-underline. |
| `MD004` | `{ "style": "consistent" }` | Unordered list style — consistent within file. |
| `MD013` | `false` | Line length — disabled; prose wraps naturally in our docs. |
| `MD033` | `false` | Allow inline HTML — needed for some KB content. |
| `MD036` | `false` | Emphasis as heading — used intentionally in skill files. |
| `MD041` | `false` | First line should be heading — disabled (YAML frontmatter files). |
| `MD026` | `false` | Trailing punctuation in heading — KB uses `Step 1:`, `Prerequisites:`, etc. |
| `MD060` | `false` | Table column style — non-aligned tables are the norm in KB. |
| `MD001` | `false` | Heading increment — KB guidelines intentionally skip levels (`##` → `####`). |
| `MD024` | `false` | Duplicate headings — KB uses repeated section names across guideline files. |
| `MD025` | `false` | Multiple top-level headings — some docs use multiple `#` headings for structure. |
| `MD046` | `false` | Code block style — KB mixes fenced and indented intentionally. |
