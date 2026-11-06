import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { makeVault, SEED_PLUGINS as SEED } from './testkit.js'
import { addRow, assertVault, hasPlugin, readRows, registryPath, removeRow } from './registry.js'

const row = (name: string) => ({ name, version: '1.0.0', installed: '2026-01-01' })

describe('registry', () => {
  it('not a vault -> error', () => {
    const dir = mkdtempSync(join(tmpdir(), 'novault-'))
    expect(() => assertVault(dir)).toThrow(/not a vault/)
    expect(() => readRows(dir)).toThrow(/not a vault/)
  })

  it('empty seed -> no rows', () => {
    expect(readRows(makeVault())).toEqual([])
  })

  it('add/has/read row; rest byte-exact', () => {
    const vault = makeVault()
    addRow(vault, row('a'))
    addRow(vault, row('b'))
    expect(hasPlugin(vault, 'a')).toBe(true)
    expect(hasPlugin(vault, 'c')).toBe(false)
    expect(readRows(vault).map(r => r.name)).toEqual(['a', 'b'])
    expect(readFileSync(registryPath(vault), 'utf8')).toBe(
      `${SEED}| a | 1.0.0 | 2026-01-01 |\n| b | 1.0.0 | 2026-01-01 |\n`.replace(/\n\n$/, '\n'),
    )
  })

  it('remove row keeps others byte-exact; unknown -> false', () => {
    const vault = makeVault()
    addRow(vault, row('a'))
    addRow(vault, row('b'))
    expect(removeRow(vault, 'a')).toBe(true)
    expect(readFileSync(registryPath(vault), 'utf8')).toBe(`${SEED}| b | 1.0.0 | 2026-01-01 |\n`)
    expect(removeRow(vault, 'zzz')).toBe(false)
  })

  it('file without table -> row appended at end', () => {
    const vault = makeVault('# Plugins\n')
    addRow(vault, row('a'))
    expect(readRows(vault)).toHaveLength(1)
  })
})
