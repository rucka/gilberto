#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRETTIER_BIN="$SCRIPT_DIR/../node_modules/.bin/prettier"
"$PRETTIER_BIN" "{**/*,*}.{ts,tsx,js,jsx,json,html}" --write --ignore-path "$SCRIPT_DIR/../.prettierignore" --log-level log "$@"
