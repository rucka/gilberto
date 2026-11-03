import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { installPlugin, PluginInstallError } from './install.js'
import { readRows, registryPath } from './registry.js'
import { makePlugin, makeVault, pillarFiles, pillarManifest } from './testkit.js'

const NOW = '2026-01-02'

function attempt(version: string) {
  const vault = makeVault()
  const before = readFileSync(registryPath(vault), 'utf8')
  const dir = makePlugin({ ...pillarManifest('p'), version }, pillarFiles)
  let refused: unknown
  try {
    installPlugin(vault, dir, { force: false, dryRun: false, now: () => NOW })
  } catch (e) {
    refused = e
  }
  return {
    refused,
    before,
    after: readFileSync(registryPath(vault), 'utf8'),
    rows: readRows(vault),
  }
}

function expectRefusedOrSingleRow(version: string): void {
  const { refused, before, after, rows } = attempt(version)
  if (refused) {
    expect(refused).toBeInstanceOf(PluginInstallError)
    expect(after).toBe(before)
    return
  }
  expect(rows.map(r => r.name)).toEqual(['p'])
  expect(rows[0]?.installed).toBe(NOW)
}

function forceReinstall(version: string) {
  const vault = makeVault()
  const first = installPlugin(vault, makePlugin(pillarManifest('p'), pillarFiles), {
    force: false,
    dryRun: false,
    now: () => '2025-12-31',
  })
  const snap = () => first.files.map(f => readFileSync(join(vault, f), 'utf8'))
  const before = readFileSync(registryPath(vault), 'utf8')
  const files = snap()
  const dir = makePlugin({ ...pillarManifest('p'), version }, pillarFiles)
  let refused: unknown
  try {
    installPlugin(vault, dir, { force: true, dryRun: false, now: () => NOW })
  } catch (e) {
    refused = e
  }
  const after = readFileSync(registryPath(vault), 'utf8')
  return { refused, before, after, files, filesAfter: snap(), rows: readRows(vault) }
}

describe('r0-1 untrusted manifest version in plugins.md row', () => {
  it('W-r0-1a pipe + newline injecting a ghost row: refused or single row', () => {
    expectRefusedOrSingleRow('1.0 | x |\n| ghost | 9 | 2020-01-01')
  })

  it('W-r0-1b pipe shifting installed column: refused or single row with real date', () => {
    expectRefusedOrSingleRow('1.0 | evil')
  })

  it('B-r0-1c newline only splitting the row: refused or single row', () => {
    expectRefusedOrSingleRow('1.0\n| ghost | 9 | 2020-01-01 |')
  })

  it('C-r0-1d plain version installs as one row', () => {
    const { refused, rows } = attempt('1.2.3')
    expect(refused).toBeUndefined()
    expect(rows).toEqual([{ name: 'p', version: '1.2.3', installed: NOW }])
  })

  it('W-r0-1e force reinstall with injecting version: refused keeps prior row+files, or single row', () => {
    const r = forceReinstall('1.0 | x |\n| ghost | 9 | 2020-01-01')
    if (r.refused) {
      expect(r.refused).toBeInstanceOf(PluginInstallError)
      expect(r.after).toBe(r.before)
      expect(r.filesAfter).toEqual(r.files)
      return
    }
    expect(r.rows.map(x => x.name)).toEqual(['p'])
    expect(r.rows[0]?.installed).toBe(NOW)
  })
})
