#!/usr/bin/env bash
# Local re-run: pack CLI + bootstrap, install into a temp prefix, run the smoke. Usage: run.sh [base|launchd|path-a]
set -eu
root=$(cd "$(dirname "$0")/../../../.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
(cd "$root" && pnpm build)
(cd "$root/apps/cli" && pnpm pack --pack-destination "$tmp" >/dev/null)
(cd "$root/packages/vault-bootstrap" && pnpm pack --pack-destination "$tmp" >/dev/null)
npm i -g --prefix "$tmp/prefix" "$tmp"/*.tgz >/dev/null
# workspace CLI is 0.0.0; stamp an in-range version so the #48 skill accepts it
(cd "$tmp/prefix/lib/node_modules/gilberto" && npm pkg set version=0.1.0-smoke)
GILBERTO_BIN="$tmp/prefix/bin/gilberto" bash "$root/apps/cli/test/smoke/bootstrap.sh" "${1:-base}"
