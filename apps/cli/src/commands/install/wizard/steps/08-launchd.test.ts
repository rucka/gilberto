import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { WizardExit } from '../exit.js'
import { makeCtx, tmpRoot } from '../test-utils/index.js'
import type { RunResult } from '../types.js'
import { launchdStep } from './08-launchd.js'

const OK: RunResult = { status: 0, stderr: '' }

const setup = async (
  over: {
    platform?: NodeJS.Platform
    flags?: object
    env?: NodeJS.ProcessEnv
    run?: RunResult
  } = {},
) => {
  const home = await tmpRoot()
  const vault = await tmpRoot()
  const h = makeCtx({
    flags: { launchd: true, ...over.flags },
    env: { HOME: home, PATH: '', ...over.env },
  })
  h.ctx.platform = over.platform ?? 'darwin'
  const calls: string[][] = []
  h.ctx.run = (cmd, args) => (calls.push([cmd, ...args]), over.run ?? OK)
  return { home, vault, h, calls, agents: join(home, 'Library/LaunchAgents') }
}
const fail = (p: Promise<unknown>) =>
  p.then(
    () => undefined,
    (e: unknown) => e as WizardExit,
  )

describe('step 8 launchd', () => {
  it('AC4/5/11/12: darwin writes 3 plists, lints each, prints inactive, no launchctl', async () => {
    const { vault, h, calls, agents } = await setup()
    const out = await launchdStep({ targetPath: vault }, h.ctx)
    expect(out.launchd).toBe('installed')
    expect((await readdir(agents)).sort()).toEqual([
      'com.foomakers.gilberto.ingest.plist',
      'com.foomakers.gilberto.morning-briefing.plist',
      'com.foomakers.gilberto.reflect-day.plist',
    ])
    expect(calls.map(c => c.slice(0, 2))).toEqual(Array(3).fill(['plutil', '-lint']))
    expect(calls.flat()).not.toContain('launchctl')
    const mb = await readFile(join(agents, 'com.foomakers.gilberto.morning-briefing.plist'), 'utf8')
    expect(mb).toContain('<integer>7</integer>')
    expect(mb).toContain('/gilberto-process-surface morning-briefing')
    expect(h.out.join('\n')).toContain('inactive')
    expect(h.out.join('\n')).toContain('gilberto status')
    for (const f of await readdir(agents)) expect(h.out).toContain(`  ${join(agents, f)}`)
    expect(h.lines.filter(l => l.startsWith('wrote file='))).toHaveLength(3)
  })

  it('uses claude from PATH when present', async () => {
    const bin = await tmpRoot()
    await writeFile(join(bin, 'claude'), '#!/bin/sh\n', { mode: 0o755 })
    const { vault, h, agents } = await setup({ env: { PATH: bin } })
    await launchdStep({ targetPath: vault }, h.ctx)
    expect(
      await readFile(join(agents, 'com.foomakers.gilberto.reflect-day.plist'), 'utf8'),
    ).toContain(join(bin, 'claude'))
  })

  it('AC6: linux → stub, nothing written', async () => {
    const { vault, h, home } = await setup({ platform: 'linux' })
    const out = await launchdStep({ targetPath: vault }, h.ctx)
    expect(out.launchd).toBe('stubbed')
    expect(h.out).toEqual(['linux scheduling stub: cron/systemd timers land in Initiative #5'])
    expect(await readdir(home)).toEqual([])
  })

  it('AC7: --no-launchd → skip log, nothing written', async () => {
    const { vault, h, home } = await setup({ flags: { launchd: false } })
    expect((await launchdStep({ targetPath: vault }, h.ctx)).launchd).toBe('skipped')
    expect(h.lines).toContain('step=launchd decision=skipped reason=--no-launchd')
    expect(await readdir(home)).toEqual([])
  })

  it('AC10: CI=true skips on darwin unless --launchd-in-ci', async () => {
    const a = await setup({ env: { CI: 'true' } })
    expect((await launchdStep({ targetPath: a.vault }, a.h.ctx)).launchd).toBe('skipped')
    expect(await readdir(a.home)).toEqual([])
    const b = await setup({ env: { CI: 'true' }, flags: { launchdInCi: true } })
    expect((await launchdStep({ targetPath: b.vault }, b.h.ctx)).launchd).toBe('installed')
  })

  it('AC9: lint failure → plists removed, exit 65 with stderr', async () => {
    const { vault, h, agents } = await setup({ run: { status: 1, stderr: 'bad xml\n' } })
    const e = await fail(launchdStep({ targetPath: vault }, h.ctx))
    expect(e?.code).toBe(65)
    expect(e?.message).toBe('plist validation failed: bad xml')
    expect(await readdir(agents)).toEqual([])
    expect(await readdir(vault)).toEqual([])
  })

  it('plutil missing → exit 65 and cleanup', async () => {
    const err = Object.assign(new Error('x'), { code: 'ENOENT' }) as NodeJS.ErrnoException
    const { vault, h, agents } = await setup({ run: { status: null, stderr: '', error: err } })
    const e = await fail(launchdStep({ targetPath: vault }, h.ctx))
    expect(e?.code).toBe(65)
    expect(e?.message).toContain('plutil not found')
    expect(await readdir(agents)).toEqual([])
  })

  it('non-owned existing plist → exit 1, untouched', async () => {
    const { vault, h, agents } = await setup()
    await mkdir(agents, { recursive: true })
    const p = join(agents, 'com.foomakers.gilberto.ingest.plist')
    await writeFile(p, 'foreign')
    const e = await fail(launchdStep({ targetPath: vault }, h.ctx))
    expect(e?.code).toBe(1)
    expect(e?.message).toBe(`plist already exists and is not owned by gilberto: ${p}`)
    expect(await readFile(p, 'utf8')).toBe('foreign')
    expect(await readdir(agents)).toEqual(['com.foomakers.gilberto.ingest.plist'])
  })

  it('owned existing plist is overwritten (idempotent re-run)', async () => {
    const { vault, h } = await setup()
    await launchdStep({ targetPath: vault }, h.ctx)
    expect((await launchdStep({ targetPath: vault }, h.ctx)).launchd).toBe('installed')
  })

  it.skipIf(process.getuid?.() === 0)('unwritable LaunchAgents → exit 13', async () => {
    const { vault, h, home } = await setup()
    await mkdir(join(home, 'Library'), { mode: 0o500 })
    const e = await fail(launchdStep({ targetPath: vault }, h.ctx))
    expect(e?.code).toBe(13)
  })
})
