#!/bin/sh
# Usage: dispatch.sh <skill> [args...]
# Runs the skill via claude; exits 0 with "skill not installed" when missing.
skill="${1:-}"
[ -n "$skill" ] || { echo "usage: dispatch.sh <skill> [args...]" >&2; exit 2; }
shift
dir="${GILBERTO_SKILLS_DIR:-$HOME/.claude/plugins}"
if [ ! -d "$dir" ] || [ -z "$(find "$dir" -type d -name "$skill" -path '*/skills/*' 2>/dev/null | head -n 1)" ]; then
  echo "skill not installed"
  exit 0
fi
exec claude -p "/$skill $*"
