#!/usr/bin/env bash
# Smoke for `gilberto install` (Path B). Usage: bootstrap.sh [base|launchd]
# Env: GILBERTO_BIN (default: gilberto), SMOKE_BUDGET_SECONDS (default 180).
set -u
here=$(cd "$(dirname "$0")" && pwd)
. "$here/assertions.sh"
BIN=${GILBERTO_BIN:-gilberto}
BUDGET=${SMOKE_BUDGET_SECONDS:-180}
mode=${1:-base}
work=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/gilberto-smoke.XXXXXX")
PLISTS=(com.foomakers.gilberto.morning-briefing com.foomakers.gilberto.reflect-day)
cleanup() {
  if [ "$mode" = launchd ]; then
    for l in "${PLISTS[@]}"; do rm -f "$HOME/Library/LaunchAgents/$l.plist"; done
  fi
  rm -rf "$work"
}
trap cleanup EXIT

pillars=(me pulse projects intelligence journey)
core=(me/me.md pulse/pulse.md projects/projects.md intelligence/intelligence.md journey/journey.md
  network/network.md network/people network/companies _ingest/.gitkeep .claude/skills CLAUDE.md
  anatomy intelligence/ai/ai.md intelligence/product/product.md
  anatomy/anatomy.md anatomy/gilberto.md anatomy/topics.md anatomy/plugins.md anatomy/preferences.md
  anatomy/playbooks)
steps=(path overwrite topics plugins skeleton anatomy hooks launchd)

if [ "$mode" = launchd ]; then
  [ "$(uname)" = Darwin ] || { echo "launchd mode requires macOS" >&2; exit 2; }
  export HOME="$work/home"; mkdir -p "$HOME"
  vault="$work/vault"
  "$BIN" install "$vault" --no-hooks --launchd-in-ci --non-interactive --no-banner >"$work/out" 2>&1
  assert_exit 0 $? "install --launchd-in-ci"
  for l in "${PLISTS[@]}"; do
    p="$HOME/Library/LaunchAgents/$l.plist"
    assert_file "$p"
    plutil -lint "$p" >/dev/null 2>&1 || _fail "plutil -lint failed: $p"
  done
  finish; rc=$?; exit $rc
fi

vault="$work/test-vault"
real_home=$HOME
export HOME="$work/home"; mkdir -p "$HOME"

# AC-1/3/8/9: full install, verbose, timed
start=$SECONDS
"$BIN" install "$vault" --no-launchd --no-hooks --non-interactive --verbose --no-banner \
  --seed-topics 'intelligence=ai,product' >"$work/out" 2>"$work/err"
rc=$?
dur=$((SECONDS - start))
out=$(cat "$work/out" "$work/err")
echo "metric: install_duration_seconds=$dur"
assert_exit 0 $rc "install"
[ "$dur" -lt "$BUDGET" ] || _fail "install took ${dur}s, budget ${BUDGET}s"
assert_tree "$vault" "${core[@]}"
for s in "${steps[@]}"; do assert_contains "$out" "step=$s" "verbose output"; done
# AC-8: logger writes everything to stderr with no level prefix; under --verbose the happy path
# emits only `step=` / `wrote ` trace lines, so any other stderr line is an error/warn event.
bad=$(grep -vE '^(step=[a-z]+ |wrote (file|dir)=)' "$work/err")
[ -z "$bad" ] || _fail "unexpected stderr on happy path: $bad"
assert_absent "$HOME/Library"

# AC-6: re-run on existing vault => exit 2
"$BIN" install "$vault" --no-launchd --no-hooks --non-interactive --no-banner >"$work/out2" 2>&1
assert_exit 2 $? "second install"
assert_contains "$(cat "$work/out2")" "gilberto update" "second install upgrade hint"

# AC-7: help lists flags and 8-step inventory
help=$("$BIN" install --help --no-banner 2>&1)
for f in --seed-topics --no-hooks --no-launchd --launchd-in-ci --non-interactive --verbose; do
  assert_contains "$help" "$f" "help"
done
for n in "1 target path" "2 overwrite" "3 topic" "4 vault skeleton" "5 plugins" "6 anatomy" "7 .claude hooks" "8 launchd"; do
  assert_contains "$help" "$n" "help"
done

# AC-10: Linux scheduling stub, nothing written to $HOME/Library nor any cron/systemd location
if [ "$(uname)" = Linux ]; then
  marker="$work/before-stub"; : >"$marker"; cron0=$(crontab -l 2>/dev/null); sleep 1
  "$BIN" install "$work/stub-vault" --no-hooks --non-interactive --no-banner >"$work/out3" 2>&1
  assert_exit 0 $? "install (linux stub)"
  assert_contains "$(cat "$work/out3")" "linux scheduling stub" "stdout"
  assert_absent "$HOME/Library"
  for d in "$HOME/.config/systemd" "$HOME/.local/share/systemd" /etc/systemd/system /etc/systemd/user \
    /etc/cron.d /etc/cron.daily /etc/cron.hourly /var/spool/cron /var/spool/cron/crontabs; do
    [ -d "$d" ] || continue
    new=$(find "$d" -newer "$marker" 2>/dev/null)
    [ -z "$new" ] || _fail "scheduler file written: $new"
  done
  [ "$(crontab -l 2>/dev/null)" = "$cron0" ] || _fail "user crontab changed by install"
  new=$(find "$HOME" -newer "$marker" \( -name '*.service' -o -name '*.timer' -o -name '*cron*' \) 2>/dev/null)
  [ -z "$new" ] || _fail "scheduler file written under HOME: $new"
fi

HOME=$real_home
finish; rc=$?; exit $rc
