#!/usr/bin/env bash
# Pure-shell assertion helpers. Source me; failures are collected, `finish` exits non-zero.
FAILS=()
_fail() { FAILS+=("$1"); echo "FAIL: $1" >&2; }
assert_file() { [ -f "$1" ] || _fail "missing file: $1"; }
assert_dir() { [ -d "$1" ] || _fail "missing dir: $1"; }
assert_absent() { [ ! -e "$1" ] || _fail "unexpected path: $1"; }
assert_contains() { # <haystack> <needle> <label>
  case "$1" in *"$2"*) ;; *) _fail "${3:-output} lacks: $2" ;; esac
}
assert_exit() { # <expected> <actual> <label>
  [ "$1" = "$2" ] || _fail "${3:-command} exit $2, expected $1"
}
assert_tree() { # <root> <files...>  prints every missing path
  local root=$1 p; shift
  for p in "$@"; do [ -e "$root/$p" ] || _fail "missing in tree: $p"; done
}
finish() {
  [ ${#FAILS[@]} -eq 0 ] && { echo "smoke ok"; return 0; }
  echo "smoke failed: ${#FAILS[@]} assertion(s)" >&2
  printf '  - %s\n' "${FAILS[@]}" >&2
  return 1
}
