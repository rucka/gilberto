#!/usr/bin/env bash
# Quality-gate dispatcher. Dev mode auto-fixes; CI mode (CI=true) verifies only.
set -euo pipefail

cd "$(dirname "$0")/.."

pnpm exec turbo run ts:check test lint

if [ "${CI:-}" = "true" ]; then
  pnpm prettier:check
  pnpm mdlint:check
else
  pnpm prettier:fix
  pnpm mdlint:fix
fi

pnpm hygiene:check
