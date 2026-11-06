import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { CommandDeps } from '../types.js'
import { handlePluginCommand } from './handler.js'
import { readRows } from './registry.js'
import { parsePluginCommand } from './parser.js'
import { gitRepo, makePlugin, makeVault, pillarFiles, pillarManifest, write } from './testkit.js'

type Ctx = { deps: CommandDeps; out: string[]; warn: string[]; err: string[] }

const ctx = (cwd: string, env: NodeJS.ProcessEnv = {}): Ctx => {
  const c: Ctx = { out: [], warn: [], err: [], deps: undefined as never }
  const noop = (): void => undefined
  c.deps = {
    cwd,
    env,
    write: t => c.out.push(t),
    logger: { debug: noop, info: noop, warn: m => c.warn.push(m), error: m => c.err.push(m) },
  }
  return c
}

const run = (c: Ctx, args: string[], options: Record<string, unknown> = {}) =>
  handlePluginCommand(parsePluginCommand(options, args), c.deps)

const bundledRoot = (): string => {
  const root = mkdtempSync(join(tmpdir(), 'bundled-'))
  makePlugin(pillarManifest('pulse-health'), pillarFiles, root, 'pulse-health')
  makePlugin(
    { name: 'sk', description: 'd', skills: ['./skills/x'], gilberto: { kind: 'core' } },
    { 'skills/x/SKILL.md': 'S' },
    root,
    'sk',
  )
  return root
}

describe('plugin install/remove handler', () => {
  it('AC1 bundled name via GILBERTO_PLUGINS_DIR; AC7 remove', async () => {
    const vault = makeVault()
    const c = ctx(vault, { GILBERTO_PLUGINS_DIR: bundledRoot() })
    await run(c, ['install', 'pulse-health'])
    expect(readRows(vault).map(r => r.name)).toEqual(['pulse-health'])
    expect(c.out.join('')).toContain('installed pulse-health 1.2.3')
    await run(c, ['remove', 'pulse-health'])
    expect(readRows(vault)).toEqual([])
  })

  it('AC2 single-plugin repo url, temp removed', async () => {
    const vault = makeVault()
    const url = gitRepo(makePlugin(pillarManifest('remote'), pillarFiles))
    await run(ctx(vault), ['install', url])
    expect(readRows(vault).map(r => r.name)).toEqual(['remote'])
  })

  it('AC3 multi repo: valid installed, invalid named, exit non-zero', async () => {
    const vault = makeVault()
    const parent = mkdtempSync(join(tmpdir(), 'multi-'))
    makePlugin(pillarManifest('good'), pillarFiles, parent, 'good')
    makePlugin({ name: 'bad', gilberto: { kind: 'zzz' } }, {}, parent, 'bad')
    const c = ctx(vault)
    await expect(run(c, ['install', gitRepo(parent)])).rejects.toThrow(/1 plugin\(s\) failed/)
    expect(readRows(vault).map(r => r.name)).toEqual(['good'])
    expect(c.err.join('')).toContain('bad')
  })

  it('AC4 invalid manifest -> rejects, nothing written', async () => {
    const vault = makeVault()
    const root = mkdtempSync(join(tmpdir(), 'bundled-'))
    makePlugin({ name: 'bad' }, {}, root, 'bad')
    await expect(
      run(ctx(vault, { GILBERTO_PLUGINS_DIR: root }), ['install', 'bad']),
    ).rejects.toThrow(/bad/)
    expect(readRows(vault)).toEqual([])
  })

  it('AC5 already installed refused, --force ok', async () => {
    const vault = makeVault()
    const c = ctx(vault, { GILBERTO_PLUGINS_DIR: bundledRoot() })
    await run(c, ['install', 'pulse-health'])
    await expect(run(c, ['install', 'pulse-health'])).rejects.toThrow(/already installed/)
    await run(c, ['install', 'pulse-health'], { force: true })
    expect(readRows(vault)).toHaveLength(1)
  })

  it('AC6 skills hint: not detected -> /plugin install; detected -> present', async () => {
    const root = bundledRoot()
    const home = mkdtempSync(join(tmpdir(), 'home-'))
    const c1 = ctx(makeVault(), { GILBERTO_PLUGINS_DIR: root, HOME: home })
    await run(c1, ['install', 'sk'])
    expect(c1.out.join('')).toContain('/plugin install sk')
    write(home, '.claude/plugins/installed_plugins.json', '{"plugins":{"sk@mk":[]}}')
    const c2 = ctx(makeVault(), { GILBERTO_PLUGINS_DIR: root, HOME: home })
    await run(c2, ['install', 'sk'])
    expect(c2.out.join('')).toContain('skills present')
  })

  it('AC8 remove unknown -> rejects "not installed"', async () => {
    await expect(run(ctx(makeVault()), ['remove', 'nope'])).rejects.toThrow('not installed')
  })

  it('AC9 dry-run install/remove -> no writes', async () => {
    const vault = makeVault()
    const c = ctx(vault, { GILBERTO_PLUGINS_DIR: bundledRoot() })
    await run(c, ['install', 'pulse-health'], { dryRun: true })
    expect(c.out.join('')).toContain('would install pulse-health')
    expect(readRows(vault)).toEqual([])
    expect(existsSync(join(vault, 'anatomy/playbooks/pulse'))).toBe(false)
    await run(c, ['install', 'pulse-health'])
    const c2 = ctx(vault)
    await run(c2, ['remove', 'pulse-health'], { dryRun: true })
    expect(c2.out.join('')).toContain('would remove pulse-health')
    expect(readRows(vault)).toHaveLength(1)
  })

  it('edge: unknown name lists bundled; missing args', async () => {
    const c = ctx(makeVault(), { GILBERTO_PLUGINS_DIR: bundledRoot() })
    await expect(run(c, ['install', 'zzz'])).rejects.toThrow(/bundled: .*pulse-health/)
    await expect(run(c, ['install'])).rejects.toThrow(/missing/)
    await expect(run(c, ['remove'])).rejects.toThrow(/missing/)
  })

  it('edge: modified file kept with warning', async () => {
    const vault = makeVault()
    const c = ctx(vault, { GILBERTO_PLUGINS_DIR: bundledRoot() })
    await run(c, ['install', 'pulse-health'])
    write(vault, 'anatomy/playbooks/pulse/daily/pulse-health.md', 'EDIT')
    await run(c, ['remove', 'pulse-health'])
    expect(c.warn.join('')).toContain('kept modified file')
  })
})
