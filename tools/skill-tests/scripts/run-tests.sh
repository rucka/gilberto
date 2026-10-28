#!/usr/bin/env bash
set -uo pipefail
cd "${0%/*}/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/ (e.g. 'brew install uv')" >&2
  exit 1
fi

uv run --frozen pytest "$@"
code=$?
# pytest exit 5 = no tests collected
[ "$code" -eq 5 ] && exit 0
exit "$code"
