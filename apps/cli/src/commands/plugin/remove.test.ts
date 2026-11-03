import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { installPlugin } from './install.js'
import { readRows } from './registry.js'
import { removePlugin } from './remove.js'
import { makePlugin, makeVault, pillarFiles, pillarManifest, write } from './testkit.js'

const opts = { purge: false, dryRun: false }
const setup = () => {
  const vault = makeVault()
  installPlugin(vault, makePlugin(pillarManifest('p'), pillarFiles), {
    force: false,
    dryRun: false,
  })
  return vault
}
const PB = 'anatomy/playbooks/pulse/daily/p.md'

describe('removePlugin', () => {
  it('AC7 deletes contributions, record, row; prunes empty dirs', () => {
    const vault = setup()
    const r = removePlugin(vault, 'p', opts)
    expect(r.removed).toContain(PB)
    expect(existsSync(join(vault, PB))).toBe(false)
    expect(existsSync(join(vault, 'anatomy/templates/pulse'))).toBe(false)
    expect(existsSync(join(vault, 'anatomy/playbooks/pulse'))).toBe(false)
    expect(existsSync(join(vault, 'anatomy/templates'))).toBe(true)
    expect(existsSync(join(vault, 'anatomy/.plugins/p.json'))).toBe(false)
    expect(readRows(vault)).toEqual([])
  })

  it('AC7 other contributors and core.md untouched', () => {
    const vault = setup()
    write(vault, 'anatomy/playbooks/pulse/daily/core.md', 'CORE')
    write(vault, 'anatomy/playbooks/pulse/daily/other.md', 'OTHER')
    removePlugin(vault, 'p', opts)
    expect(readFileSync(join(vault, 'anatomy/playbooks/pulse/daily/core.md'), 'utf8')).toBe('CORE')
    expect(readFileSync(join(vault, 'anatomy/playbooks/pulse/daily/other.md'), 'utf8')).toBe(
      'OTHER',
    )
  })

  it('AC8 unknown name -> error, nothing changed', () => {
    const vault = setup()
    expect(() => removePlugin(vault, 'zzz', opts)).toThrow('plugin "zzz" not installed')
    expect(readRows(vault)).toHaveLength(1)
    expect(existsSync(join(vault, PB))).toBe(true)
  })

  it('modified file kept unless --purge', () => {
    const vault = setup()
    write(vault, PB, 'EDITED')
    const r = removePlugin(vault, 'p', opts)
    expect(r.kept).toEqual([PB])
    expect(readFileSync(join(vault, PB), 'utf8')).toBe('EDITED')
    expect(readRows(vault)).toEqual([])
    const v2 = setup()
    write(v2, PB, 'EDITED')
    removePlugin(v2, 'p', { ...opts, purge: true })
    expect(existsSync(join(v2, PB))).toBe(false)
  })

  it('AC9 dry-run -> plan, no writes', () => {
    const vault = setup()
    const r = removePlugin(vault, 'p', { ...opts, dryRun: true })
    expect(r.removed).toContain(PB)
    expect(existsSync(join(vault, PB))).toBe(true)
    expect(readRows(vault)).toHaveLength(1)
  })

  it('row without record -> row removed only', () => {
    const vault = makeVault()
    installPlugin(vault, makePlugin({ name: 'c', description: 'd', gilberto: { kind: 'core' } }), {
      force: false,
      dryRun: false,
    })
    expect(removePlugin(vault, 'c', opts).removed).toEqual([])
    expect(readRows(vault)).toEqual([])
  })

  it('not a vault -> error', () => {
    expect(() => removePlugin('/nonexistent-vault', 'p', opts)).toThrow(/not a vault/)
  })
})
