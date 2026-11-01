import { chmod, copyFile, mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { WizardExit } from '../exit.js'
import { HOOK_IDS, mergeSettings, type HookId, type OwnedHook } from '../settings-merge.js'
import { quote, type WizardStep } from '../types.js'

type HookDef = { event: string; skill: string; args: string; guard: string; transcript?: true }

const DEFS: Record<HookId, HookDef> = {
  'gilberto.session-start': {
    event: 'SessionStart',
    skill: 'gilberto-process-next',
    args: '',
    guard:
      'grep -qiE "^[[:space:]-]*session-start:[[:space:]]*off" "$ROOT/anatomy/preferences.md" 2>/dev/null && exit 0',
  },
  'gilberto.pre-compact': {
    event: 'PreCompact',
    skill: 'gilberto-process-capture',
    args: '',
    guard: ':',
    transcript: true,
  },
  'gilberto.session-end': {
    event: 'SessionEnd',
    skill: 'gilberto-process-reflect',
    args: ' day',
    guard:
      'STAMP="$ROOT/.claude/hooks/.last-reflect-day"; TODAY="$(date +%F)"; [ "$(cat "$STAMP" 2>/dev/null)" = "$TODAY" ] && exit 0; echo "$TODAY" > "$STAMP"',
  },
}

const sq = (s: string): string => `'${s.replace(/'/g, `'\\''`)}'`

const TRANSCRIPT = (node: string): string => `NODE=${sq(node)}; [ -x "$NODE" ] || NODE=node
INPUT=""; [ -t 0 ] || INPUT="$(cat)"
TP="$(printf %s "$INPUT" | "$NODE" -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{const t=JSON.parse(d).transcript_path;if(typeof t==="string")process.stdout.write(t)}catch{}})' 2>/dev/null)"
`

export const renderDispatcher = (root: string, id: HookId): string => {
  const { skill, args, guard, transcript } = DEFS[id]
  return `#!/bin/sh
# ${id}: owned by gilberto; never blocks the session
[ -n "$GILBERTO_HOOK" ] && exit 0
ROOT=${sq(root)}
${guard}
if [ ! -f "$ROOT/.claude/skills/${skill}/SKILL.md" ]; then
  echo "skill not installed: ${skill}" >&2
  exit 0
fi
${transcript ? TRANSCRIPT(process.execPath) : ''}export GILBERTO_HOOK=1
(cd "$ROOT" && exec claude -p "/${skill}${args}${transcript ? '${TP:+ $TP}' : ''}" >/dev/null 2>&1 </dev/null) &
exit 0
`
}

const invalid = (): WizardExit =>
  new WizardExit(
    65,
    'existing .claude/settings.json is not valid JSON; aborting step 7. fix or remove the file, then re-run with --no-launchd to retry',
  )

const readSettings = async (path: string): Promise<Record<string, unknown> | undefined> => {
  let raw: string
  try {
    raw = await readFile(path, 'utf8')
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return undefined
    throw e
  }
  try {
    const v: unknown = JSON.parse(raw)
    if (typeof v !== 'object' || v === null || Array.isArray(v)) throw invalid()
    return v as Record<string, unknown>
  } catch (e) {
    throw e instanceof WizardExit ? e : invalid()
  }
}

export const hooksStep: WizardStep = async (draft, { flags, trace, now }) => {
  if (!flags.hooks) {
    trace('step=hooks decision=skipped reason=--no-hooks')
    return { ...draft, hooks: 'skipped' }
  }
  const { targetPath } = draft
  if (targetPath === undefined) throw new Error('hooks step requires targetPath')
  const dir = join(targetPath, '.claude')
  const hooksDir = join(dir, 'hooks')
  const settingsPath = join(dir, 'settings.json')

  const existing = await readSettings(settingsPath)
  const owned: OwnedHook[] = HOOK_IDS.map(id => ({
    id,
    event: DEFS[id].event,
    command: sq(join(hooksDir, `${id}.sh`)),
  }))
  const { merged, mergedKeys, conflict } = mergeSettings(existing ?? {}, owned)

  await mkdir(hooksDir, { recursive: true })
  for (const o of owned) {
    const file = join(hooksDir, `${o.id}.sh`)
    await writeFile(file, renderDispatcher(targetPath, o.id))
    await chmod(file, 0o755)
    trace(`wrote file=${quote(file)}`)
  }
  if (existing !== undefined && conflict) {
    const backup = `${settingsPath}.bak-${(now ?? (() => new Date()))().toISOString()}`
    await copyFile(settingsPath, backup)
    trace(`wrote file=${quote(backup)}`)
  }
  const tmp = `${settingsPath}.tmp-${process.pid}`
  await writeFile(tmp, `${JSON.stringify(merged, null, 2)}\n`)
  await rename(tmp, settingsPath)
  trace(`wrote file=${quote(settingsPath)}`)
  trace(`merged-keys=${mergedKeys.join(',')}`)
  return { ...draft, hooks: 'installed' }
}
