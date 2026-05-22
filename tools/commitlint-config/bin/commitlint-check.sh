#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMITLINT_BIN="$SCRIPT_DIR/../node_modules/.bin/commitlint"
COMMITLINT_CONFIG="$SCRIPT_DIR/../commitlint.config.cjs"
"$COMMITLINT_BIN" --config "$COMMITLINT_CONFIG" "$@"
