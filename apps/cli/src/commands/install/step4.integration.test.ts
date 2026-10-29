import { existsSync, readdirSync } from 'node:fs'
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import { EventEmitter } from 'node:events'
import { join } from 'node:path'
import * as bootstrap from '@foomakers/gilberto-vault-bootstrap'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { WizardExit } from './wizard/exit.js'
import { runWizard } from './wizard/orchestrator.js'
import type { Bootstrap, StepContext } from './wizard/types.js'
import { makeCtx, tmpRoot } from './wizard/test-utils/index.js'

const exists = (p: string) =>
  stat(p).then(
    () => true,
    () => false,
  )

const setup = async (over: { bootstrap?: Partial<Bootstrap>; target?: string } = {}) => {
  const tmp = await tmpRoot()
  const target = over.target ?? join(await tmpRoot(), 'vault')
  const signals = new EventEmitter()
  const h = makeCtx({
    flags: { target, nonInteractive: true },
    env: { HOME: '/home/u', TMPDIR: tmp },
  })
  const ctx: StepContext = {
    ...h.ctx,
    signals,
    loadBootstrap: async () => ({ ...bootstrap, ...over.bootstrap }),
  }
  return { ctx, tmp, target, signals, lines: h.lines }
}

const tempLeft = async (tmp: string) => (await readdir(tmp)).filter(n => n.startsWith('gilberto-'))

const failWith = async (ctx: StepContext) =>
  runWizard(ctx).then(
    () => {
      throw new Error('expected failure')
    },
    (e: unknown) => e as WizardExit,
  )

afterEach(() => {
  vi.doUnmock('node:fs/promises')
  vi.resetModules()
})

describe('step 4 via orchestrator', () => {
  it('AC1: success → full vault at target, materialized, temp gone', async () => {
    const { ctx, tmp, target } = await setup()
    const state = await runWizard(ctx)
    expect(state.materialized).toBe(true)
    for (const p of ['me/me.md', 'network/people', 'anatomy', '_ingest/.gitkeep', 'CLAUDE.md'])
      expect(await exists(join(target, p))).toBe(true)
    expect(await readFile(join(target, 'CLAUDE.md'), 'utf8')).toContain(target)
    expect(await tempLeft(tmp)).toEqual([])
  })

  it('AC1: temp dir is $TMPDIR/gilberto-install-<pid> while writing; target absent until commit', async () => {
    const { ctx, tmp, target } = await setup({
      bootstrap: {
        renderTopicNote: (t, d) => {
          expect(readdirSync(tmp)).toContain(`gilberto-install-${process.pid}`)
          return bootstrap.renderTopicNote(t, d)
        },
      },
    })
    const seen: boolean[] = []
    const orig = ctx.trace
    ctx.trace = l => {
      if (l === 'wrote file="CLAUDE.md"') seen.push(!existsSync(target))
      orig(l)
    }
    await runWizard(ctx)
    expect(seen).toEqual([true])
  })

  it('failure after partial write → target missing, temp removed, error propagated', async () => {
    const boom = Object.assign(new Error('x'), { code: 'EIO' })
    const { ctx, tmp, target } = await setup({
      bootstrap: {
        renderTopicNote: () => {
          throw boom
        },
      },
    })
    expect(await failWith(ctx)).toBe(boom)
    expect(await exists(target)).toBe(false)
    expect(await tempLeft(tmp)).toEqual([])
  })

  it('failure leaves an existing empty target unchanged', async () => {
    const target = join(await tmpRoot(), 'v')
    await mkdir(target)
    const { ctx } = await setup({
      target,
      bootstrap: {
        renderTopicNote: () => {
          throw new Error('boom')
        },
      },
    })
    await failWith(ctx)
    expect(await readdir(target)).toEqual([])
  })

  it('disk full (ENOSPC) → exit 28, cleanup', async () => {
    const { ctx, tmp, target } = await setup({
      bootstrap: {
        renderTopicNote: () => {
          throw Object.assign(new Error('x'), { code: 'ENOSPC' })
        },
      },
    })
    expect((await failWith(ctx)).code).toBe(28)
    expect(await exists(target)).toBe(false)
    expect(await tempLeft(tmp)).toEqual([])
  })

  it('AC4: SIGINT before commit → cleanup, exit 130, message, target untouched, handler removed', async () => {
    const { ctx, tmp, target, signals } = await setup({
      bootstrap: {
        renderTopicNote: (t, d) => {
          signals.emit('SIGINT')
          return bootstrap.renderTopicNote(t, d)
        },
      },
    })
    const e = await failWith(ctx)
    expect(e).toMatchObject({
      code: 130,
      message: 'aborted by user, target path left untouched',
    })
    expect(await exists(target)).toBe(false)
    expect(await tempLeft(tmp)).toEqual([])
    expect(signals.listenerCount('SIGINT')).toBe(0)
  })

  it('handler is deregistered after a successful commit', async () => {
    const { ctx, signals } = await setup()
    await runWizard(ctx)
    expect(signals.listenerCount('SIGINT')).toBe(0)
  })

  it('AC4: SIGINT during commit is deferred; vault written, exit 130 reported honestly', async () => {
    const real = await import('node:fs/promises')
    const signals = new EventEmitter()
    vi.resetModules()
    vi.doMock('node:fs/promises', () => ({
      ...real,
      rename: async (a: string, b: string) => {
        signals.emit('SIGINT')
        return real.rename(a, b)
      },
    }))
    const { runWizard: run } = await import('./wizard/orchestrator.js')
    const s = await setup()
    const e = await run({ ...s.ctx, signals }).then(
      () => undefined,
      (x: unknown) => x as WizardExit,
    )
    expect(e?.code).toBe(130)
    expect(e?.message).toContain('after the vault was written')
    expect(await exists(join(s.target, 'anatomy'))).toBe(true)
    expect(await tempLeft(s.tmp)).toEqual([])
  })

  it('AC5: missing parent directories are created', async () => {
    const root = await tmpRoot()
    const { ctx } = await setup({ target: join(root, 'a b', 'c', 'my vault') })
    await runWizard(ctx)
    expect(await exists(join(root, 'a b', 'c', 'my vault', 'me', 'me.md'))).toBe(true)
  })

  it('missing @foomakers/gilberto-vault-bootstrap → exit 70, target untouched, temp removed', async () => {
    const { ctx, tmp, target } = await setup()
    delete ctx.loadBootstrap
    vi.resetModules()
    vi.doMock('node:module', async () => {
      const real = await vi.importActual<typeof import('node:module')>('node:module')
      return {
        ...real,
        createRequire: () => ({
          resolve: () => {
            throw Object.assign(new Error('Cannot find module'), { code: 'MODULE_NOT_FOUND' })
          },
        }),
      }
    })
    const { runWizard: run } = await import('./wizard/orchestrator.js')
    const e = await run(ctx).then(
      () => undefined,
      (x: unknown) => x as WizardExit,
    )
    vi.doUnmock('node:module')
    expect(e?.code).toBe(70)
    expect(e?.message).toContain('@foomakers/gilberto-vault-bootstrap')
    expect(await exists(target)).toBe(false)
    expect(await tempLeft(tmp)).toEqual([])
  })

  it('non-empty confirmed target → exit 1, existing files kept', async () => {
    const target = join(await tmpRoot(), 'v')
    await mkdir(target)
    await writeFile(join(target, 'mine.txt'), 'm')
    const { ctx, tmp } = await setup({ target })
    expect((await failWith(ctx)).code).toBe(1)
    expect(await readdir(target)).toEqual(['mine.txt'])
    expect(await tempLeft(tmp)).toEqual([])
  })
})
