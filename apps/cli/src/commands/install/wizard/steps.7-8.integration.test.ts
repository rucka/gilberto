import { readFile, readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { parseInstallCommand } from '../parser.js'
import { runWizard } from './orchestrator.js'
import { makeCtx, tmpRoot } from './test-utils/index.js'

const run = async (flags: object, platform: NodeJS.Platform = 'darwin') => {
  const home = await tmpRoot()
  const target = join(await tmpRoot(), 'vault')
  const h = makeCtx({
    flags: { target, nonInteractive: true, ...flags },
    env: { HOME: home, TMPDIR: await tmpRoot(), PATH: '' },
  })
  h.ctx.platform = platform
  h.ctx.run = () => ({ status: 0, stderr: '' })
  const state = await runWizard(h.ctx)
  return { state, target, home, h }
}
const has = (p: string) =>
  stat(p).then(
    () => true,
    () => false,
  )

describe('wizard steps 7-8 orchestration', () => {
  it('neither flag: hooks installed, plists written', async () => {
    const { state, target, home } = await run({ launchd: true })
    expect(state).toMatchObject({ hooks: 'installed', launchd: 'installed' })
    expect(await has(join(target, '.claude/settings.json'))).toBe(true)
    expect(await readdir(join(home, 'Library/LaunchAgents'))).toHaveLength(3)
  })

  it('--no-hooks only', async () => {
    const { state, target, home } = await run({ hooks: false, launchd: true })
    expect(state).toMatchObject({ hooks: 'skipped', launchd: 'installed' })
    expect(await has(join(target, '.claude/settings.json'))).toBe(false)
    expect(await has(join(home, 'Library'))).toBe(true)
  })

  it('--no-launchd only', async () => {
    const { state, home } = await run({ launchd: false })
    expect(state).toMatchObject({ hooks: 'installed', launchd: 'skipped' })
    expect(await has(join(home, 'Library'))).toBe(false)
  })

  it('both skipped: logs, no diff', async () => {
    const { state, h, target } = await run({ hooks: false, launchd: false })
    expect(state).toMatchObject({ hooks: 'skipped', launchd: 'skipped' })
    expect(h.lines).toContain('step=hooks decision=skipped reason=--no-hooks')
    expect(h.lines).toContain('step=launchd decision=skipped reason=--no-launchd')
    expect(await has(join(target, '.claude/settings.json'))).toBe(false)
  })

  it('linux: stub, vault intact', async () => {
    const { state, h, target } = await run({ launchd: true }, 'linux')
    expect(state.launchd).toBe('stubbed')
    expect(h.out[0]).toContain('linux scheduling stub')
    expect(await readFile(join(target, '.claude/settings.json'), 'utf8')).toContain('SessionEnd')
  })
})

describe('parser flags', () => {
  it('--launchd-in-ci / --no-hooks / --no-launchd', () => {
    expect(
      parseInstallCommand({ launchdInCi: true, hooks: false, launchd: false }, []),
    ).toMatchObject({
      launchdInCi: true,
      hooks: false,
      launchd: false,
    })
    expect(parseInstallCommand({}, [])).toMatchObject({
      launchdInCi: false,
      hooks: true,
      launchd: true,
    })
  })
})
