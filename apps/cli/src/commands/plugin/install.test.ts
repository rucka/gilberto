import { existsSync, readdirSync, readFileSync, statSync, symlinkSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { installPlugin, PluginInstallError } from './install.js'
import { readRows, registryPath } from './registry.js'
import { makePlugin, makeVault, pillarFiles, pillarManifest, write } from './testkit.js'

const opts = { force: false, dryRun: false, now: () => '2026-01-02' }

const snapshot = (root: string): string[] =>
  (readdirSync(root, { recursive: true, withFileTypes: true }) as import('node:fs').Dirent[])
    .map(e => join(e.parentPath, e.name))
    .map(p => `${p}:${statSync(p).isFile() ? readFileSync(p, 'utf8') : 'dir'}`)
    .sort()

const errorsOf = (fn: () => unknown): string => {
  try {
    fn()
  } catch (e) {
    expect(e).toBeInstanceOf(PluginInstallError)
    return (e as Error).message
  }
  throw new Error('expected throw')
}

describe('installPlugin', () => {
  it('AC1 playbook + templates land, row appended', () => {
    const vault = makeVault()
    const dir = makePlugin(pillarManifest('pulse-health'), pillarFiles)
    const r = installPlugin(vault, dir, opts)
    expect(readFileSync(join(vault, 'anatomy/playbooks/pulse/daily/pulse-health.md'), 'utf8')).toBe(
      'PLAYBOOK',
    )
    expect(readFileSync(join(vault, 'anatomy/templates/pulse/habit/sub/b.md'), 'utf8')).toBe('B')
    expect(readRows(vault)).toEqual([
      { name: 'pulse-health', version: '1.2.3', installed: '2026-01-02' },
    ])
    expect(r.files).toContain('anatomy/templates/pulse/habit/a.md')
    expect(readdirSync(join(vault, 'anatomy')).some(n => n.startsWith('.stage-'))).toBe(false)
  })

  it('version defaults to 0.0.0 when manifest has none', () => {
    const vault = makeVault()
    const m = { name: 'core-x', description: 'd', gilberto: { kind: 'core' } }
    installPlugin(vault, makePlugin(m), opts)
    expect(readRows(vault)[0]?.version).toBe('0.0.0')
  })

  it('AC4 invalid manifest -> nothing written, errors named', () => {
    const vault = makeVault()
    const before = snapshot(vault)
    const dir = makePlugin({ name: 'bad', gilberto: { kind: 'x' } })
    expect(errorsOf(() => installPlugin(vault, dir, opts))).toContain('gilberto.kind')
    expect(snapshot(vault)).toEqual(before)
  })

  it('AC5 already installed -> refused; --force overwrites contributions', () => {
    const vault = makeVault()
    installPlugin(vault, makePlugin(pillarManifest('p'), pillarFiles), opts)
    const dir2 = makePlugin(pillarManifest('p', { templates: [] }), {
      'playbooks/daily.md': 'NEW',
    })
    expect(errorsOf(() => installPlugin(vault, dir2, opts))).toMatch(/already installed/)
    installPlugin(vault, dir2, { ...opts, force: true })
    expect(readFileSync(join(vault, 'anatomy/playbooks/pulse/daily/p.md'), 'utf8')).toBe('NEW')
    expect(existsSync(join(vault, 'anatomy/templates/pulse/habit/a.md'))).toBe(false)
    expect(readRows(vault)).toHaveLength(1)
  })

  it('AC6 skills never copied; reported', () => {
    const vault = makeVault()
    const m = { name: 's', description: 'd', skills: ['./skills/x'], gilberto: { kind: 'core' } }
    const r = installPlugin(vault, makePlugin(m, { 'skills/x/SKILL.md': 'S' }), opts)
    expect(r.skills).toEqual(['./skills/x'])
    expect(r.files).toEqual([])
    expect(existsSync(join(vault, 'skills'))).toBe(false)
  })

  it('AC9 dry-run -> plan returned, no fs change', () => {
    const vault = makeVault()
    const before = snapshot(vault)
    const r = installPlugin(vault, makePlugin(pillarManifest('p'), pillarFiles), {
      ...opts,
      dryRun: true,
    })
    expect(r.dryRun).toBe(true)
    expect(r.files.length).toBeGreaterThan(0)
    expect(snapshot(vault)).toEqual(before)
  })

  it('not a vault -> error', () => {
    const dir = makePlugin(pillarManifest('p'), pillarFiles)
    expect(() => installPlugin(join(dir, 'nowhere'), dir, opts)).toThrow(/not a vault/)
  })

  it('collision with another contributor file -> refused, even with --force', () => {
    const vault = makeVault()
    write(vault, 'anatomy/playbooks/pulse/daily/p.md', 'USER')
    const dir = makePlugin(pillarManifest('p'), pillarFiles)
    expect(errorsOf(() => installPlugin(vault, dir, opts))).toMatch(/collision/)
    expect(errorsOf(() => installPlugin(vault, dir, { ...opts, force: true }))).toMatch(/collision/)
    expect(readFileSync(join(vault, 'anatomy/playbooks/pulse/daily/p.md'), 'utf8')).toBe('USER')
  })

  it('failure injection mid-move -> vault byte-identical, stage removed', () => {
    const vault = makeVault()
    const before = snapshot(vault)
    const dir = makePlugin(pillarManifest('p'), pillarFiles)
    expect(() =>
      installPlugin(vault, dir, {
        ...opts,
        onMove: i => {
          if (i === 2) throw new Error('boom')
        },
      }),
    ).toThrow('boom')
    expect(snapshot(vault)).toEqual(before)
  })

  it('failure injection on --force -> previous install restored', () => {
    const vault = makeVault()
    installPlugin(vault, makePlugin(pillarManifest('p'), pillarFiles), opts)
    const before = snapshot(vault)
    const dir = makePlugin(pillarManifest('p', { templates: [] }), { 'playbooks/daily.md': 'NEW' })
    expect(() =>
      installPlugin(vault, dir, {
        ...opts,
        force: true,
        onMove: () => {
          throw new Error('boom')
        },
      }),
    ).toThrow('boom')
    expect(snapshot(vault)).toEqual(before)
    expect(readFileSync(registryPath(vault), 'utf8')).toContain('| p | 1.2.3 | 2026-01-02 |')
  })

  it('traversal: playbook path/key escaping plugin dir -> refused', () => {
    const vault = makeVault()
    const before = snapshot(vault)
    const bad = makePlugin(
      pillarManifest('p', { playbooks: { 'pulse/daily': '../../etc/passwd' } }),
    )
    expect(errorsOf(() => installPlugin(vault, bad, opts))).toMatch(/playbook path not found/)
    const key = makePlugin(pillarManifest('p', { playbooks: { 'pulse/../x': './a.md' } }), {
      'a.md': 'x',
    })
    expect(errorsOf(() => installPlugin(vault, key, opts))).toMatch(
      /pillar mismatch|invalid playbook key/,
    )
    expect(snapshot(vault)).toEqual(before)
  })

  it('symlink inside template -> refused', () => {
    const vault = makeVault()
    const dir = makePlugin(pillarManifest('p', { playbooks: {} }), { 'templates/habit/a.md': 'A' })
    symlinkSync('/etc/hosts', join(dir, 'templates/habit/link'))
    expect(errorsOf(() => installPlugin(vault, dir, opts))).toMatch(/symlink/)
  })

  it('templates without pillar -> refused', () => {
    const m = { name: 'c', description: 'd', gilberto: { kind: 'core', templates: ['./t/x'] } }
    const dir = makePlugin(m, { 't/x/a.md': 'A' })
    expect(errorsOf(() => installPlugin(makeVault(), dir, opts))).toMatch(
      /requires gilberto.pillar/,
    )
  })

  it('unsafe plugin name -> refused', () => {
    const m = { name: '../evil', description: 'd', gilberto: { kind: 'core' } }
    expect(errorsOf(() => installPlugin(makeVault(), makePlugin(m), opts))).toMatch(
      /invalid plugin name/,
    )
  })
})
