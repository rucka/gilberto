# @gilberto/prettier-config

Shared Prettier configuration for the gilberto monorepo. All packages use these rules by default unless they provide their own config.

## Usage

Add to your package's `package.json`:

```json
"prettier": "@gilberto/prettier-config"
```

Scripts (via bin wrappers):

```json
"scripts": {
  "prettier:check": "prettier-check",
  "prettier:fix": "prettier-fix"
}
```

### Extending in a Package

Create a `.prettierrc.js` in your package root:

```js
module.exports = {
  ...require('@gilberto/prettier-config/.prettierrc.json'),
  // package-specific overrides
}
```

## Files

- `.prettierrc.json` — formatting rules
- `bin/` — wrapper scripts (`prettier-check`, `prettier-fix`)
- `.prettierignore` — ignored patterns

## Scope

The bin wrappers glob `{**/*,*}.{ts,tsx,js,jsx,json,html}` only. Markdown is handled by `@gilberto/markdownlint-config` (avoids the well-known Prettier ↔ markdownlint stylistic overlap). YAML files (`pnpm-workspace.yaml`, GitHub Actions, etc.) are intentionally out of scope of the bin wrappers — invoke `prettier --check '**/*.{yml,yaml}'` directly from a workspace if you need to gate them.
