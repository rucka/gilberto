import { EventEmitter } from 'node:events'
import { readFile, readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import * as bootstrap from '@foomakers/gilberto-vault-bootstrap'
import { describe, expect, it } from 'vitest'
import type { WizardExit } from '../exit.js'
import { runWizard } from '../orchestrator.js'
import type { StepContext } from '../types.js'
import { makeCtx, tmpRoot } from '../test-utils/index.js'

const exists = (p: string) =>
  stat(p).then(
    () => true,
    () => false,
  )

// getSeedRoot call 1 = step 4 (CLAUDE.md), later calls = step 6 (anatomy)
const setup = async (step6Seed: () => string = bootstrap.getSeedRoot) => {
  let calls = 0
  const getSeedRoot = () => (++calls === 1 ? bootstrap.getSeedRoot() : step6Seed())
  const tmp = await tmpRoot()
  const target = join(await tmpRoot(), 'vault')
  const signals = new EventEmitter()
  const h = makeCtx({
    flags: {
      target,
      nonInteractive: true,
      hooks: false,
      verbose: true,
      seedTopics: { pulse: ['sleep'] },
    },
    env: { HOME: '/home/u', TMPDIR: tmp },
  })
  const ctx: StepContext = {
    ...h.ctx,
    signals,
    now: () => new Date('2026-10-29T10:00:00Z'),
    loadBootstrap: async () => ({ ...bootstrap, getSeedRoot }),
  }
  return { ctx, tmp, target, signals, out: h.out, lines: h.lines }
}

const tempLeft = async (tmp: string) => (await readdir(tmp)).filter(n => n.startsWith('gilberto-'))

const failWith = (ctx: StepContext) =>
  runWizard(ctx).then(
    () => {
      throw new Error('expected failure')
    },
    (e: unknown) => e as WizardExit,
  )

describe('steps 5-6 via orchestrator', () => {
  it('AC1-AC4: plugins printed, anatomy seeded into the committed vault', async () => {
    const { ctx, target, out } = await setup()
    await runWizard(ctx)
    expect(out.join('\n')).toContain('gilberto-core — ')
    expect(await exists(join(target, 'anatomy', 'anatomy.md'))).toBe(true)
    expect(await exists(join(target, 'anatomy', 'registries.md'))).toBe(false)
    const topics = await readFile(join(target, 'anatomy', 'topics.md'), 'utf8')
    expect(topics).toContain('| sleep | |')
    expect(await readFile(join(target, 'anatomy', 'anatomy.md'), 'utf8')).toContain('2026-10-29')
  })

  it('AC6: verbose trace has wrote lines for anatomy items', async () => {
    const { ctx, lines } = await setup()
    await runWizard(ctx)
    expect(lines).toContain('wrote file="anatomy/topics.md"')
    expect(lines).toContain('wrote dir="anatomy/playbooks"')
  })

  it('AC5: missing seed → exit 70, message, target untouched, temp removed', async () => {
    const { ctx, tmp, target } = await setup(() => '/nonexistent-seed')
    expect(await failWith(ctx)).toMatchObject({
      code: 70,
      message: 'vault-bootstrap content package not found; reinstall gilberto',
    })
    expect(await exists(target)).toBe(false)
    expect(await tempLeft(tmp)).toEqual([])
  })

  it('AC7: SIGINT during step 6 → exit 130, temp removed, target untouched', async () => {
    const box: { signals?: EventEmitter } = {}
    const s = await setup(() => {
      box.signals?.emit('SIGINT')
      return bootstrap.getSeedRoot()
    })
    box.signals = s.signals
    expect(await failWith(s.ctx)).toMatchObject({
      code: 130,
      message: 'aborted by user, target path left untouched',
    })
    expect(await exists(s.target)).toBe(false)
    expect(await tempLeft(s.tmp)).toEqual([])
    expect(s.signals.listenerCount('SIGINT')).toBe(0)
  })
})
