# @gilberto/eslint-config

Shared ESLint flat-config for the gilberto monorepo. All packages use these rules by default unless they provide their own config.

## Usage

Reference in your package's `package.json` scripts (via the `lint` / `lint-fix` bin wrappers):

```json
"scripts": {
  "lint": "lint",
  "lint:fix": "lint-fix"
}
```

Or extend directly in a custom flat config:

```js
const base = require('@gilberto/eslint-config')

module.exports = [
  ...base,
  {
    rules: {
      // package-specific overrides
    },
  },
]
```

### Available Configs

| Config | Import | Use Case | Status |
|--------|--------|----------|--------|
| Base | `@gilberto/eslint-config` | TypeScript packages | Available |
| React | `@gilberto/eslint-config/react` | React packages | Deferred — lands with `apps/website/` (Phase 5, Initiative #5) |
| React + a11y | `@gilberto/eslint-config/react-a11y` | React with accessibility rules | Deferred — lands with `apps/website/` (Phase 5, Initiative #5) |

## Files

- `eslint.config.cjs` — base flat config (TypeScript + general rules); also encodes the ignore patterns inline
- `bin/` — wrapper scripts (`lint`, `lint-fix`, `eslint`)
