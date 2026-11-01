import { spawnSync } from 'node:child_process'
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { WizardExit } from '../exit.js'
import { makeCtx, tmpRoot } from '../test-utils/index.js'
import { hooksStep, renderDispatcher } from './07-hooks.js'

const setup = async (settings?: string, flags = {}) => {
  const root = await tmpRoot()
  if (settings !== undefined) {
    await mkdir(join(root, '.claude'), { recursive: true })
    await writeFile(join(root, '.claude/settings.json'), settings)
  }
  return { root, h: makeCtx({ flags }) }
}
const read = async (root: string) =>
  JSON.parse(await readFile(join(root, '.claude/settings.json'), 'utf8')) as {
    hooks: Record<string, { hooks: { command: string }[] }[]>
  }

describe('step 7 hooks', () => {
  it('AC1: fresh → settings.json with 3 hooks pointing to absolute dispatchers', async () => {
    const { root, h } = await setup()
    const out = await hooksStep({ targetPath: root }, h.ctx)
    expect(out.hooks).toBe('installed')
    const s = await read(root)
    for (const [ev, id] of [
      ['SessionStart', 'session-start'],
      ['PreCompact', 'pre-compact'],
      ['SessionEnd', 'session-end'],
    ] as const) {
      const cmd = s.hooks[ev]![0]!.hooks[0]!.command
      expect(cmd).toBe(join(root, `.claude/hooks/gilberto.${id}.sh`))
      expect((await stat(cmd)).mode & 0o111).not.toBe(0)
    }
    expect(h.lines).toContain(
      'merged-keys=gilberto.session-start,gilberto.pre-compact,gilberto.session-end',
    )
  })

  it('AC2: user content preserved; no backup without conflict', async () => {
    const { root, h } = await setup(JSON.stringify({ mcpServers: { a: 1 }, hooks: { Stop: [] } }))
    await hooksStep({ targetPath: root }, h.ctx)
    const s = (await read(root)) as unknown as Record<string, unknown>
    expect(s['mcpServers']).toEqual({ a: 1 })
    expect((await readdir(join(root, '.claude'))).filter(n => n.includes('.bak-'))).toEqual([])
  })

  it('AC2: conflicting gilberto hook → timestamped backup of previous file, overwritten', async () => {
    const prev = JSON.stringify({
      hooks: {
        SessionEnd: [
          { matcher: '', hooks: [{ type: 'command', command: '/old/gilberto.session-end.sh' }] },
        ],
      },
    })
    const { root, h } = await setup(prev)
    h.ctx.now = () => new Date('2026-01-02T03:04:05.000Z')
    await hooksStep({ targetPath: root }, h.ctx)
    expect(
      await readFile(join(root, '.claude/settings.json.bak-2026-01-02T03:04:05.000Z'), 'utf8'),
    ).toBe(prev)
    expect((await read(root)).hooks['SessionEnd']).toHaveLength(1)
  })

  it('AC3: --no-hooks → untouched + skip log', async () => {
    const { root, h } = await setup(undefined, { hooks: false })
    const out = await hooksStep({ targetPath: root }, h.ctx)
    expect(out.hooks).toBe('skipped')
    expect(h.lines).toContain('step=hooks decision=skipped reason=--no-hooks')
    expect(await readdir(root)).toEqual([])
  })

  it('invalid JSON → exit 65, file untouched', async () => {
    const { root, h } = await setup('{nope')
    const e = await hooksStep({ targetPath: root }, h.ctx).catch((x: unknown) => x)
    expect(e).toBeInstanceOf(WizardExit)
    expect((e as WizardExit).code).toBe(65)
    expect((e as WizardExit).message).toContain('not valid JSON')
    expect(await readFile(join(root, '.claude/settings.json'), 'utf8')).toBe('{nope')
    await writeFile(join(root, '.claude/settings.json'), '[]')
    expect(
      ((await hooksStep({ targetPath: root }, h.ctx).catch((x: unknown) => x)) as WizardExit).code,
    ).toBe(65)
  })

  it('requires targetPath', async () => {
    const { h } = await setup()
    await expect(hooksStep({}, h.ctx)).rejects.toThrow('targetPath')
  })

  it('AC13: dispatcher with skill missing exits 0 and logs', async () => {
    const root = await tmpRoot()
    const script = join(root, 'd.sh')
    await writeFile(script, renderDispatcher(root, 'gilberto.pre-compact'))
    const r = spawnSync('sh', [script], { encoding: 'utf8' })
    expect(r.status).toBe(0)
    expect(r.stderr).toContain('skill not installed: gilberto-process-capture')
  })

  it('session-end dispatcher runs once per day; session-start honours preferences off', async () => {
    const root = await tmpRoot()
    await mkdir(join(root, '.claude/hooks'), { recursive: true })
    await mkdir(join(root, 'anatomy'), { recursive: true })
    const end = join(root, 'e.sh')
    await writeFile(end, renderDispatcher(root, 'gilberto.session-end'))
    spawnSync('sh', [end])
    const r = spawnSync('sh', [end], { encoding: 'utf8' })
    expect(r.status).toBe(0)
    expect(r.stderr).toBe('')
    await writeFile(join(root, 'anatomy/preferences.md'), '- session-start: off\n')
    const start = join(root, 's.sh')
    await writeFile(start, renderDispatcher(root, 'gilberto.session-start'))
    expect(spawnSync('sh', [start], { encoding: 'utf8' }).stderr).toBe('')
  })
})
