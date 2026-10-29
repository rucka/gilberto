import { EventEmitter } from 'node:events'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import * as bootstrap from '@foomakers/gilberto-vault-bootstrap'
import { describe, expect, it } from 'vitest'
import { parseSeedTopics } from './parser.js'
import { WizardExit } from './wizard/exit.js'
import { runWizard } from './wizard/orchestrator.js'
import { skeletonStep } from './wizard/steps/04-skeleton.js'
import { DEFAULT_TOPIC_SEEDS, TOPIC_PILLARS } from './wizard/state.js'
import type { StepContext } from './wizard/types.js'
import { listing, makeCtx, tmpRoot } from './wizard/test-utils/index.js'

const wizard = async (nonInteractive: boolean, prepare: (target: string) => Promise<void>) => {
  const tmp = await tmpRoot()
  const target = join(await tmpRoot(), 'vault')
  await prepare(target)
  const h = makeCtx({
    flags: { target, nonInteractive },
    env: { HOME: '/home/u', TMPDIR: tmp },
    script: { confirm: true },
  })
  const ctx: StepContext = {
    ...h.ctx,
    signals: new EventEmitter(),
    loadBootstrap: async () => bootstrap,
  }
  const error = await runWizard(ctx).then(
    () => undefined,
    (e: unknown) => e as WizardExit,
  )
  return { ...h, error, target, tmp }
}

const withFile = async (target: string) => {
  await mkdir(target, { recursive: true })
  await writeFile(join(target, 'notes.txt'), 'keep')
}
const withDotfile = async (target: string) => {
  await mkdir(target, { recursive: true })
  await writeFile(join(target, '.DS_Store'), 'keep')
}
const withEmptySubdir = async (target: string) => {
  await mkdir(join(target, 'sub'), { recursive: true })
}
const NON_EMPTY = [
  ['file', withFile, ['notes.txt']],
  ['dotfile only', withDotfile, ['.DS_Store']],
  ['empty subdir only', withEmptySubdir, ['sub']],
] as const

describe('r0-1 non-empty target agreed by steps 2 and 4', () => {
  const refused = (r: Awaited<ReturnType<typeof wizard>>) => {
    expect(r.error).toBeInstanceOf(WizardExit)
    expect(r.error?.code).toBe(1)
    expect(r.error?.message).toMatch(/not empty/)
    expect(r.lines.join('\n')).not.toContain('decision=continue')
    expect(r.calls.filter(c => c.startsWith('confirm:'))).toEqual([])
    expect(r.lines.some(l => l.startsWith('wrote '))).toBe(false)
  }

  it.each(NON_EMPTY)(
    'r0-1-w1 non-interactive, target holds %s: refused up-front, nothing materialized',
    async (_n, prep, entries) => {
      const r = await wizard(true, prep)
      refused(r)
      expect(await readdir(r.target)).toEqual(entries)
    },
  )

  it.each(NON_EMPTY)(
    'r0-1-w2 interactive, target holds %s: refused before the confirm prompt',
    async (_n, prep, entries) => {
      const r = await wizard(false, prep)
      refused(r)
      expect(await readdir(r.target)).toEqual(entries)
    },
  )

  const untouched = async (r: Awaited<ReturnType<typeof wizard>>) => {
    expect(r.error).toBeInstanceOf(WizardExit)
    expect(r.error?.code).toBe(2)
    expect(r.error?.message).toMatch(/vault already exists/)
    expect(r.calls.filter(c => c.startsWith('confirm:'))).toEqual([])
    expect(r.lines.some(l => l.startsWith('wrote '))).toBe(false)
  }
  const withAnatomy = async (target: string) => {
    await mkdir(join(target, 'anatomy'), { recursive: true })
    await writeFile(join(target, 'anatomy', 'anatomy.md'), 'keep')
  }
  const withSkill = async (target: string) => {
    await mkdir(join(target, '.claude', 'skills', 'gilberto-x'), { recursive: true })
  }

  it.each([
    ['anatomy', withAnatomy, ['anatomy']],
    ['skill', withSkill, ['.claude']],
  ] as const)(
    'r0-1-c3 control: vault present (%s) keeps exit 2, both modes',
    async (_n, prep, entries) => {
      for (const nonInteractive of [true, false]) {
        const r = await wizard(nonInteractive, prep)
        await untouched(r)
        expect(await readdir(r.target)).toEqual(entries)
      }
    },
  )

  it.each([true, false])(
    'r0-1-w3 target is a regular file (nonInteractive=%s): clean exit 1, file untouched',
    async nonInteractive => {
      const r = await wizard(nonInteractive, t => writeFile(t, 'keep'))
      expect(r.error).toBeInstanceOf(WizardExit)
      expect(r.error?.code).toBe(1)
      expect(r.error?.message).toContain(r.target)
      expect(r.error?.message).not.toMatch(/ENOTDIR/)
      expect(r.lines.join('\n')).not.toContain('decision=continue')
      expect(r.calls.filter(c => c.startsWith('confirm:'))).toEqual([])
      expect(r.lines.some(l => l.startsWith('wrote '))).toBe(false)
      expect(await readFile(r.target, 'utf8')).toBe('keep')
    },
  )

  it('r0-1-c1 control: existing empty dir installs', async () => {
    const r = await wizard(true, async t => {
      await mkdir(t, { recursive: true })
    })
    expect(r.error).toBeUndefined()
    expect(await readdir(r.target)).toContain('CLAUDE.md')
  })

  it('r0-1-c2 control: missing target installs', async () => {
    const r = await wizard(true, async () => {})
    expect(r.error).toBeUndefined()
    expect(await readdir(r.target)).toContain('CLAUDE.md')
  })
})

describe('r0-2 topic seed names as path segments', () => {
  const BAD = ['ai/ml', '..', '.', '../../escaped', 'a\\b']
  const CASES = TOPIC_PILLARS.flatMap(pillar => BAD.map(topic => [pillar, topic] as const))

  it.each(CASES)('r0-2-w1 parser rejects %s=%s with exit 64', (pillar, topic) => {
    const run = () => parseSeedTopics(`${pillar}=${topic}`)
    expect(run).toThrow(WizardExit)
    try {
      run()
    } catch (e) {
      expect((e as WizardExit).code).toBe(64)
      expect((e as WizardExit).message).toContain(topic)
    }
  })

  it.each(CASES)(
    'r0-2-w2 step 4 rejects %s=%s with WizardExit 64 and writes only what a clean run writes',
    async (pillar, topic) => {
      const clean = await tmpRoot()
      await skeletonStep(
        { targetPath: '/final/vault', topicSeeds: DEFAULT_TOPIC_SEEDS },
        makeCtx().ctx,
        { root: clean, signal: new AbortController().signal },
      )
      const allowed = new Set(await listing(clean))
      const base = await tmpRoot()
      const root = join(base, 'a', 'root')
      await mkdir(root, { recursive: true })
      const error = await skeletonStep(
        {
          targetPath: '/final/vault',
          topicSeeds: { ...DEFAULT_TOPIC_SEEDS, [pillar]: [topic] },
        },
        makeCtx().ctx,
        { root, signal: new AbortController().signal },
      ).then(
        () => undefined,
        (e: unknown) => e as WizardExit,
      )
      expect(error).toBeInstanceOf(WizardExit)
      expect(error?.code).toBe(64)
      expect(error?.message).toContain(topic)
      const outside = (await listing(base)).filter(
        p => p !== 'a' && p !== 'a/root' && !p.startsWith('a/root/'),
      )
      expect(outside).toEqual([])
      const inside = (await listing(root)).filter(p => !allowed.has(p))
      expect(inside).toEqual([])
    },
  )

  it('r0-2-c1 control: plain and dotted names parse', () => {
    expect(parseSeedTopics('intelligence=ai,v1.2')).toEqual({ intelligence: ['ai', 'v1.2'] })
  })

  it.each(TOPIC_PILLARS)('r0-2-c2 control: step 4 accepts dotted name v1.2 for %s', async pillar => {
    const root = await tmpRoot()
    await skeletonStep(
      { targetPath: '/final/vault', topicSeeds: { ...DEFAULT_TOPIC_SEEDS, [pillar]: ['v1.2'] } },
      makeCtx().ctx,
      { root, signal: new AbortController().signal },
    )
    const files = await listing(root)
    expect(files).toContain(`${pillar}/v1.2/v1.2.md`)
    if (pillar === 'pulse') expect(files).toContain('pulse/v1.2/history')
  })
})

describe('r0-3 CLAUDE.md root is the target verbatim', () => {
  const render = async (targetPath: string) => {
    const root = await tmpRoot()
    await skeletonStep({ targetPath, topicSeeds: DEFAULT_TOPIC_SEEDS }, makeCtx().ctx, {
      root,
      signal: new AbortController().signal,
    })
    return readFile(join(root, 'CLAUDE.md'), 'utf8')
  }
  const seed = () => readFile(join(bootstrap.getSeedRoot(), 'skeleton', 'CLAUDE.md'), 'utf8')

  it.each(['/p/my$$v$&x', "/p/a$'b", '/p/a$`b'])(
    'r0-3-w1 target %s is inserted verbatim',
    async target => {
      const out = await render(target)
      expect(out).toBe((await seed()).replaceAll('{{VAULT_ROOT}}', () => target))
      expect(out).not.toContain('{{')
    },
  )

  it('r0-3-c1 control: plain target', async () => {
    const out = await render('/p/My Vault')
    expect(out).toContain('/p/My Vault')
    expect(out).not.toContain('{{')
  })
})
