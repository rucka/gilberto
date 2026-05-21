# @gilberto/ts-config

Shared TypeScript configuration presets for the gilberto monorepo.

## Presets

| Preset | File | Use Case |
|--------|------|----------|
| Base | `base.json` | Common compiler options (strict mode, ESM, path resolution) |
| Node | `node.json` | CLI and server packages (extends base + Node types) |
| UI | `ui.json` | React/Next.js packages (extends base + JSX + DOM types) — lands with `apps/website/` (Phase 5, Initiative #5) |

## Usage

Extend a preset in your package's `tsconfig.json`:

```json
{
  "extends": "@gilberto/ts-config/node.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```
