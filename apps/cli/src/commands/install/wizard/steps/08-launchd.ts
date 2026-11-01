import { spawnSync } from 'node:child_process'
import { constants } from 'node:fs'
import { access, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { delimiter, join } from 'node:path'
import { WizardExit } from '../exit.js'
import { INGEST_LABEL, renderIngest } from '../plists/ingest.js'
import { MORNING_BRIEFING_LABEL, renderMorningBriefing } from '../plists/morning-briefing.js'
import { REFLECT_DAY_LABEL, renderReflectDay } from '../plists/reflect-day.js'
import {
  quote,
  type RunResult,
  type StepContext,
  type WizardDraft,
  type WizardStep,
} from '../types.js'

const STUB = 'linux scheduling stub: cron/systemd timers land in Initiative #5'

const defaultRun = (cmd: string, args: string[]): RunResult => {
  const r = spawnSync(cmd, args, { encoding: 'utf8' })
  return { status: r.status, stderr: r.stderr ?? '', ...(r.error ? { error: r.error } : {}) }
}

const findClaude = async (env: NodeJS.ProcessEnv): Promise<string | undefined> => {
  for (const dir of (env['PATH'] ?? '').split(delimiter).filter(Boolean)) {
    const p = join(dir, 'claude')
    if (
      await access(p, constants.X_OK).then(
        () => true,
        () => false,
      )
    )
      return p
  }
  return undefined
}

const exists = (p: string): Promise<string | undefined> =>
  readFile(p, 'utf8').then(
    c => c,
    (e: unknown) => {
      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return undefined
      throw e
    },
  )

const denied = (e: unknown, dir: string): unknown => {
  const c = (e as NodeJS.ErrnoException).code
  return c === 'EACCES' || c === 'EPERM'
    ? new WizardExit(13, `cannot write launch agents in ${quote(dir)}: permission denied`)
    : e
}

const plutilMissing = (): WizardExit =>
  new WizardExit(
    65,
    'plutil not found; macOS install required for step 8. use --no-launchd to skip',
  )

const assertOwnable = async (path: string, label: string): Promise<void> => {
  const prev = await exists(path)
  if (prev !== undefined && !prev.includes(`<string>${label}</string>`))
    throw new WizardExit(1, `plist already exists and is not owned by gilberto: ${path}`)
}

const lintAll = async (run: NonNullable<StepContext['run']>, paths: string[]): Promise<void> => {
  for (const p of paths) {
    const r = run('plutil', ['-lint', p])
    if (r.error === undefined && r.status === 0) continue
    await Promise.all(paths.map(q => rm(q, { force: true })))
    if (r.error?.code === 'ENOENT') throw plutilMissing()
    throw new WizardExit(65, `plist validation failed: ${r.stderr.trim()}`)
  }
}

const write = async (ctx: StepContext, targetPath: string): Promise<void> => {
  const dir = join(ctx.env['HOME'] ?? homedir(), 'Library', 'LaunchAgents')
  const found = await findClaude(ctx.env)
  if (found === undefined)
    ctx.print(
      'warning: claude not found on PATH; launchd jobs will fail to start. install claude, then re-run, or use --no-launchd to skip',
    )
  const input = { claude: found ?? 'claude', root: targetPath }
  const plists = [
    [MORNING_BRIEFING_LABEL, renderMorningBriefing(input)],
    [REFLECT_DAY_LABEL, renderReflectDay(input)],
    [INGEST_LABEL, renderIngest(input)],
  ] as const
  const paths = plists.map(([label]) => join(dir, `${label}.plist`))

  for (const [i, [label]] of plists.entries()) await assertOwnable(paths[i]!, label)
  try {
    await mkdir(dir, { recursive: true })
    for (const [i, [, xml]] of plists.entries()) await writeFile(paths[i]!, xml)
  } catch (e) {
    throw denied(e, dir)
  }
  await lintAll(ctx.run ?? defaultRun, paths)
  for (const p of paths) ctx.trace(`wrote file=${quote(p)}`)
  ctx.print('launchd plists written (inactive, not loaded):')
  for (const p of paths) ctx.print(`  ${p}`)
  ctx.print(
    'each job stays inactive until its process skill is installed and activates it; run `gilberto status` to check job state',
  )
}

export const launchdStep: WizardStep = async (draft, ctx) => {
  const { flags, env, trace, print } = ctx
  const skip = (reason: string): WizardDraft => {
    trace(`step=launchd decision=skipped reason=${reason}`)
    return { ...draft, launchd: 'skipped' }
  }
  if (!flags.launchd) return skip('--no-launchd')
  if ((ctx.platform ?? process.platform) !== 'darwin') {
    print(STUB)
    return { ...draft, launchd: 'stubbed' }
  }
  if (env['CI'] === 'true' && !flags.launchdInCi) return skip('ci')
  if (draft.targetPath === undefined) throw new Error('launchd step requires targetPath')
  await write(ctx, draft.targetPath)
  return { ...draft, launchd: 'installed' }
}
