import { existsSync, statSync } from 'node:fs'
import { isAbsolute, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { describe, expect, it } from 'vitest'
import { PILLARS, UnknownPillarError, getSeedRoot, resolvePillarPath } from './index.js'

describe('getSeedRoot', () => {
  it('returns an absolute existing seed dir', () => {
    const root = getSeedRoot()
    expect(isAbsolute(root)).toBe(true)
    expect(root.endsWith('seed')).toBe(true)
    expect(statSync(root).isDirectory()).toBe(true)
  })

  it('is independent of process.cwd()', () => {
    const before = getSeedRoot()
    const cwd = process.cwd()
    process.chdir('/')
    try {
      expect(getSeedRoot()).toBe(before)
    } finally {
      process.chdir(cwd)
    }
  })

  it('is identical from built dist', async () => {
    const dist = fileURLToPath(new URL('../dist/index.js', import.meta.url))
    expect(existsSync(dist)).toBe(true)
    const built = (await import(pathToFileURL(dist).href)) as { getSeedRoot: () => string }
    expect(built.getSeedRoot()).toBe(getSeedRoot())
  })
})

describe('resolvePillarPath', () => {
  it.each(PILLARS)('returns vaultRoot/%s without scope', pillar => {
    expect(resolvePillarPath('/v', pillar)).toBe(join('/v', pillar))
  })

  it('ignores scope (root-only v1)', () => {
    expect(resolvePillarPath('/v', 'me', 'work')).toBe(join('/v', 'me'))
  })

  it('throws typed error on unknown pillar', () => {
    expect(() => resolvePillarPath('/v', 'nope' as never)).toThrow(UnknownPillarError)
  })

  it('error keeps actual and expected values distinguishable', () => {
    try {
      resolvePillarPath('/v', 'nope' as never)
      expect.unreachable()
    } catch (e) {
      const err = e as UnknownPillarError
      expect(err.pillar).toBe('nope')
      expect(err.message).toContain('"nope"')
      expect(err.message).toContain(PILLARS.join(', '))
    }
  })
})

describe('PILLARS', () => {
  it('lists the six pillars', () => {
    expect([...PILLARS]).toEqual(['me', 'pulse', 'projects', 'intelligence', 'journey', 'network'])
  })
})
