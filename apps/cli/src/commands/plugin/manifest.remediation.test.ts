import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { validateManifest } from './manifest.js'

function plugin(manifest: unknown, dirs: string[] = ['skills/a']): string {
  const dir = mkdtempSync(join(tmpdir(), 'manifest-rem-'))
  mkdirSync(join(dir, '.claude-plugin'))
  writeFileSync(join(dir, '.claude-plugin', 'plugin.json'), JSON.stringify(manifest))
  for (const d of dirs) mkdirSync(join(dir, d), { recursive: true })
  return dir
}

const base = { name: 'p', description: 'd', skills: ['./skills/a'] }

describe('r0-1 gilberto.skills', () => {
  it('W-r0-1a duplicate gilberto.skills (paths exist) rejected', () => {
    const dir = plugin({
      ...base,
      gilberto: { kind: 'core', skills: ['./skills/a', './skills/a'] },
    })
    expect(validateManifest(dir).ok).toBe(false)
  })

  it('W-r0-1b missing gilberto.skills path rejected', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', skills: ['./nope'] } })
    expect(validateManifest(dir).ok).toBe(false)
  })

  it('W-r0-1c gilberto.skills duplicating a top-level skills entry rejected', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', skills: ['./skills/a'] } })
    expect(validateManifest(dir).ok).toBe(false)
  })

  it('C-r0-1 top-level skills only stays valid', () => {
    expect(validateManifest(plugin({ ...base, gilberto: { kind: 'core' } })).ok).toBe(true)
  })
})

describe('r0-2 pillar consistency without gilberto.pillar', () => {
  it('W-r0-2 core + playbooks rejected as pillar mismatch', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', playbooks: { 'pulse/daily': './x' } } })
    const r = validateManifest(dir)
    expect(r.ok).toBe(false)
    expect(!r.ok && r.errors.join('\n')).toContain('pillar mismatch')
  })

  it('W-r0-2b connector + playbooks rejected as pillar mismatch', () => {
    const dir = plugin({
      ...base,
      gilberto: { kind: 'connector', playbooks: { 'pulse/daily': './x' } },
    })
    const r = validateManifest(dir)
    expect(r.ok).toBe(false)
    expect(!r.ok && r.errors.join('\n')).toContain('pillar mismatch')
  })

  it('C-r0-2 pillar plugin with matching playbook valid', () => {
    const dir = plugin({
      ...base,
      gilberto: { kind: 'pillar', pillar: 'pulse', playbooks: { 'pulse/daily': './x' } },
    })
    expect(validateManifest(dir).ok).toBe(true)
  })
})

describe('r0-3 symlink containment', () => {
  it('W-r0-3 symlink escaping plugin dir rejected', () => {
    const outside = mkdtempSync(join(tmpdir(), 'manifest-outside-'))
    const dir = plugin({ ...base, skills: ['./skills/evil'], gilberto: { kind: 'core' } }, [
      'skills',
    ])
    symlinkSync(outside, join(dir, 'skills', 'evil'))
    expect(validateManifest(dir).ok).toBe(false)
  })

  it('C-r0-3 symlink staying inside plugin dir valid', () => {
    const dir = plugin({ ...base, skills: ['./skills/link'], gilberto: { kind: 'core' } })
    symlinkSync(join(dir, 'skills', 'a'), join(dir, 'skills', 'link'))
    expect(validateManifest(dir).ok).toBe(true)
  })

  it('C-r0-3b existing ..hidden dir inside plugin accepted', () => {
    const dir = plugin({ ...base, skills: ['./..hidden'], gilberto: { kind: 'core' } }, [
      '..hidden',
    ])
    expect(validateManifest(dir).ok).toBe(true)
  })
})
