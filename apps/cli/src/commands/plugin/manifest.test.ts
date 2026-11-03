import {
  mkdirSync,
  mkdtempSync,
  readdirSync,
  existsSync,
  readFileSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { parseManifest, validateManifest } from './manifest.js'

const base = {
  name: 'p',
  description: 'd',
  skills: ['./skills/a'],
  gilberto: { kind: 'core' },
}

function plugin(manifest: unknown, dirs: string[] = ['skills/a']): string {
  const dir = mkdtempSync(join(tmpdir(), 'manifest-'))
  mkdirSync(join(dir, '.claude-plugin'))
  writeFileSync(
    join(dir, '.claude-plugin', 'plugin.json'),
    typeof manifest === 'string' ? manifest : JSON.stringify(manifest),
  )
  for (const d of dirs) mkdirSync(join(dir, d), { recursive: true })
  return dir
}

const errorsOf = (r: ReturnType<typeof validateManifest>): string =>
  r.ok ? '' : r.errors.join('\n')

describe('parseManifest', () => {
  it('AC-1 valid manifest -> typed result', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', templates: ['./t'] } })
    const r = parseManifest(join(dir, '.claude-plugin', 'plugin.json'))
    expect(r.ok && r.manifest.gilberto.kind).toBe('core')
  })

  it('AC-2 mistyped field -> error names path', () => {
    const dir = plugin({ ...base, gilberto: { kind: 3 } })
    const r = parseManifest(join(dir, '.claude-plugin', 'plugin.json'))
    expect(r.ok).toBe(false)
    expect(!r.ok && r.errors.join()).toContain('gilberto.kind')
  })

  it('AC-2 missing field -> error names path', () => {
    const dir = plugin({ description: 'd', gilberto: { kind: 'core' } })
    const r = parseManifest(join(dir, '.claude-plugin', 'plugin.json'))
    expect(!r.ok && r.errors.join()).toContain('name')
  })

  it('unknown gilberto key rejected', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', bogus: 1 } })
    const r = parseManifest(join(dir, '.claude-plugin', 'plugin.json'))
    expect(!r.ok && r.errors.join()).toContain('gilberto')
    expect(!r.ok && r.errors.join()).toContain('bogus')
  })

  it('unknown top-level Anthropic key tolerated', () => {
    const dir = plugin({ ...base, version: '1.0.0' })
    expect(parseManifest(join(dir, '.claude-plugin', 'plugin.json')).ok).toBe(true)
  })

  it('invalid JSON -> error with file path', () => {
    const dir = plugin('{nope')
    const file = join(dir, '.claude-plugin', 'plugin.json')
    const r = parseManifest(file)
    expect(!r.ok && r.errors[0]).toContain(file)
  })

  it('missing file -> error with file path', () => {
    const file = join(tmpdir(), 'does-not-exist', 'plugin.json')
    const r = parseManifest(file)
    expect(!r.ok && r.errors[0]).toContain(file)
  })

  it('empty skills valid', () => {
    const dir = plugin({ ...base, skills: [] })
    expect(parseManifest(join(dir, '.claude-plugin', 'plugin.json')).ok).toBe(true)
  })
})

describe('validateManifest', () => {
  it('AC-1 valid plugin dir', () => {
    expect(validateManifest(plugin(base)).ok).toBe(true)
  })

  it('schema error propagates', () => {
    expect(errorsOf(validateManifest(plugin({ ...base, gilberto: { kind: 3 } })))).toContain(
      'gilberto.kind',
    )
  })

  it('AC-3 duplicate skill name', () => {
    const dir = plugin({ ...base, skills: ['./skills/a', './other/a'] }, ['skills/a', 'other/a'])
    expect(errorsOf(validateManifest(dir))).toContain('duplicate skill')
  })

  it('AC-3 same path twice', () => {
    const dir = plugin({ ...base, skills: ['./skills/a', 'skills/a/'] })
    expect(errorsOf(validateManifest(dir))).toContain('duplicate skill')
  })

  it('AC-4 pillar required for kind pillar', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'pillar' } })
    expect(errorsOf(validateManifest(dir))).toContain('pillar mismatch')
  })

  it('AC-4 pillar forbidden for kind core', () => {
    const dir = plugin({ ...base, gilberto: { kind: 'core', pillar: 'pulse' } })
    expect(errorsOf(validateManifest(dir))).toContain('pillar mismatch')
  })

  it('AC-4 playbook pillar differs from plugin pillar', () => {
    const dir = plugin({
      ...base,
      gilberto: { kind: 'pillar', pillar: 'pulse', playbooks: { 'projects/daily': './p.md' } },
    })
    expect(errorsOf(validateManifest(dir))).toContain('pillar mismatch')
  })

  it('AC-4 consistent pillar valid', () => {
    const dir = plugin({
      ...base,
      gilberto: { kind: 'pillar', pillar: 'pulse', playbooks: { 'pulse/daily': './p.md' } },
    })
    expect(validateManifest(dir).ok).toBe(true)
  })

  it('AC-5 missing skills path', () => {
    const dir = plugin({ ...base, skills: ['./skills/missing'] })
    expect(errorsOf(validateManifest(dir))).toContain('skills/missing')
  })

  it('AC-5 skills path escaping plugin dir rejected', () => {
    const dir = plugin({ ...base, skills: ['../outside'] })
    expect(errorsOf(validateManifest(dir))).toContain('../outside')
  })

  it('missing manifest -> error with file path', () => {
    const dir = mkdtempSync(join(tmpdir(), 'manifest-'))
    expect(errorsOf(validateManifest(dir))).toContain(join(dir, '.claude-plugin', 'plugin.json'))
  })
})

const repo = resolve(import.meta.dirname, '../../../../..')

describe('shipped artifacts', () => {
  it('AC-6 gilberto-core valid, skills == dirs with SKILL.md (not _lib)', () => {
    const dir = join(repo, 'plugins/gilberto-core')
    const r = validateManifest(dir)
    expect(errorsOf(r)).toBe('')
    const onDisk = readdirSync(join(dir, 'skills'), { withFileTypes: true })
      .filter(e => e.isDirectory() && e.name !== '_lib')
      .filter(e => existsSync(join(dir, 'skills', e.name, 'SKILL.md')))
      .map(e => `./skills/${e.name}`)
      .sort()
    expect(r.ok && [...r.manifest.skills].sort()).toEqual(onDisk)
  })

  it('AC-7 documented example manifest passes validation', () => {
    const doc = readFileSync(join(repo, 'plugins/MANIFEST.md'), 'utf8')
    const json = /```json\n([\s\S]*?)\n```/.exec(doc)?.[1]
    expect(json).toBeDefined()
    const manifest = JSON.parse(json as string) as { skills: string[] }
    const dir = plugin(
      json as string,
      manifest.skills.map(s => s.replace(/^\.\//, '')),
    )
    expect(errorsOf(validateManifest(dir))).toBe('')
  })
})
