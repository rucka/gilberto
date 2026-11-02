#!/usr/bin/env bash
# Container entry. parity: Path A vs Path B tree+HOME diff. npx: no gilberto on PATH -> skill falls back to npx (run with --network none).
set -u
smoke=/repo/apps/cli/test/smoke
case "${1:-}" in
  parity) exec bash "$smoke/bootstrap.sh" path-a ;;
  npx) ;;
  *) echo "usage: run.sh parity|npx" >&2; exit 64 ;;
esac
. "$smoke/assertions.sh"
skill=/repo/plugins/gilberto-core/skills/gilberto-process-vault-bootstrap/script.py
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
command -v gilberto >/dev/null && _fail "gilberto unexpectedly on PATH"
# npx shim records argv then delegates to the real npx
mkdir -p "$work/bin"; real=$(command -v npx)
printf '#!/bin/sh\necho "$*" >>"%s/npx.log"\nexec "%s" "$@"\n' "$work" "$real" >"$work/bin/npx"; chmod +x "$work/bin/npx"
export HOME="$work/home" npm_config_fetch_retries=0 npm_config_fetch_timeout=5000; mkdir -p "$HOME"
PATH="$work/bin:$PATH" python3 "$skill" --target-path="$work/v" --seed-topics='intelligence=ai,product' \
  --disable-launchd >"$work/out" 2>"$work/err"
assert_exit 1 $? "skill (npx, offline)"
log=$(cat "$work/npx.log" 2>/dev/null)
assert_contains "$log" "-y gilberto@>=0.1.0-0 <2 install $work/v" "npx argv"
assert_contains "$log" "--non-interactive" "npx argv"
assert_contains "$(cat "$work/err")" "npm registry unreachable; install gilberto manually" "skill stderr"
assert_absent "$work/v"
finish
