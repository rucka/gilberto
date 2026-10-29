import { readFile, readdir } from 'node:fs/promises'
import { join } from 'node:path'
import { getSeedRoot, renderPillarNote, renderTopicNote } from '@foomakers/gilberto-vault-bootstrap'
import { describe, expect, it } from 'vitest'
import { DEFAULT_TOPIC_SEEDS } from '../state.js'
import { listing, makeCtx, tmpRoot } from '../test-utils/index.js'
import { WizardExit } from '../exit.js'
import { loadBootstrap, skeletonStep } from './04-skeleton.js'

const NOW = new Date('2026-10-29T00:00:00Z')

const run = async (topicSeeds = DEFAULT_TOPIC_SEEDS, targetPath = '/final/vault') => {
  const root = await tmpRoot()
  const h = makeCtx()
  h.ctx.now = () => NOW
  await skeletonStep({ targetPath, topicSeeds }, h.ctx, {
    root,
    signal: new AbortController().signal,
  })
  return { root, ...h }
}

const files = async (root: string) =>
  (await listing(root)).sort().filter(p => p.endsWith('.md') || p.endsWith('.gitkeep'))

describe('step 4 skeleton', () => {
  it('AC1: pillars, folder-notes, network, _ingest, anatomy, .claude/skills, CLAUDE.md', async () => {
    const { root } = await run({ pulse: [], intelligence: [], projects: [] })
    expect((await files(root)).sort()).toEqual(
      [
        'CLAUDE.md',
        '_ingest/.gitkeep',
        'intelligence/intelligence.md',
        'journey/journey.md',
        'me/me.md',
        'network/network.md',
        'projects/projects.md',
        'pulse/pulse.md',
      ].sort(),
    )
    const all = await listing(root)
    for (const d of ['network/people', 'network/companies', 'anatomy', '.claude/skills'])
      expect(all).toContain(d)
    expect(all).not.toContain('.claude/settings.json')
    expect(await readdir(join(root, '.claude', 'skills'))).toEqual([])
    expect(await readdir(join(root, 'anatomy'))).toEqual([])
  })

  it('AC1: pillar note content comes from the bootstrap templates', async () => {
    const { root } = await run()
    expect(await readFile(join(root, 'journey', 'journey.md'), 'utf8')).toBe(
      renderPillarNote('journey', NOW),
    )
  })

  it('AC1: root CLAUDE.md is the seed skeleton with the vault root filled in', async () => {
    const { root } = await run(DEFAULT_TOPIC_SEEDS, '/final/My Vault')
    const seed = await readFile(join(getSeedRoot(), 'skeleton', 'CLAUDE.md'), 'utf8')
    const out = await readFile(join(root, 'CLAUDE.md'), 'utf8')
    expect(out).toBe(seed.replaceAll('{{VAULT_ROOT}}', '/final/My Vault'))
    expect(out).toContain('anatomy/')
    expect(out).not.toContain('{{')
  })

  it('AC2: topics get <topic>/<topic>.md; pulse topics also get history/', async () => {
    const { root } = await run({ pulse: ['health'], intelligence: ['ai', 'product'], projects: [] })
    const all = await listing(root)
    expect(all).toEqual(
      expect.arrayContaining([
        'intelligence/ai/ai.md',
        'intelligence/product/product.md',
        'pulse/health/health.md',
        'pulse/health/history',
      ]),
    )
    expect(all).not.toContain('intelligence/ai/history')
    expect(await readFile(join(root, 'intelligence/ai/ai.md'), 'utf8')).toBe(
      renderTopicNote('ai', NOW),
    )
  })

  it('AC6: only the given topics are seeded (no PRD defaults)', async () => {
    const { root } = await run({ ...DEFAULT_TOPIC_SEEDS, intelligence: ['x'] })
    const all = await listing(root)
    expect(all).toContain('intelligence/x/x.md')
    expect(all).not.toContain('intelligence/ai')
  })

  it('AC3: one wrote dir/file line per item, stable order, relative quoted paths', async () => {
    const { lines } = await run({ pulse: ['a b'], intelligence: [], projects: [] })
    expect(lines.slice(0, 6)).toEqual([
      'wrote dir="me"',
      'wrote file="me/me.md"',
      'wrote dir="pulse"',
      'wrote file="pulse/pulse.md"',
      'wrote dir="pulse/a b"',
      'wrote file="pulse/a b/a b.md"',
    ])
    expect(lines.at(-1)).toBe('wrote file="CLAUDE.md"')
  })

  it('aborted signal stops before writing', async () => {
    const ac = new AbortController()
    ac.abort(new WizardExit(130, 'x'))
    const root = await tmpRoot()
    await expect(
      skeletonStep({ targetPath: '/t', topicSeeds: DEFAULT_TOPIC_SEEDS }, makeCtx().ctx, {
        root,
        signal: ac.signal,
      }),
    ).rejects.toMatchObject({ code: 130 })
    expect(await listing(root)).toEqual([])
  })

  it('requires targetPath and topicSeeds', async () => {
    await expect(
      skeletonStep({}, makeCtx().ctx, { root: '/x', signal: new AbortController().signal }),
    ).rejects.toThrow('requires targetPath')
  })

  it('loadBootstrap resolves the workspace package', async () => {
    expect((await loadBootstrap()).getSeedRoot()).toBe(getSeedRoot())
  })
})
