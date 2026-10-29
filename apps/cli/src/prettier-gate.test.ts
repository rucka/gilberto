import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const prettierBin = join(repoRoot, 'tools/prettier-config/node_modules/.bin/prettier')
const ignorePath = join(repoRoot, 'tools/prettier-config/.prettierignore')

const listDifferent = (files: string[]) => {
  const r = spawnSync(
    prettierBin,
    ['--list-different', '--ignore-path', ignorePath, '--log-level', 'log', ...files],
    {
      cwd: repoRoot,
      encoding: 'utf8',
    },
  )
  return r.stdout.split('\n').filter(Boolean)
}

const pairManaged = [
  '.claude/workflows/pair-implement-batch.js',
  '.claude/workflows/pair-loop.js',
  '.claude/workflows/pair-refine-batch.js',
  '.pair/.kb-version.json',
  '.pair/adoption/tech/workflow-profiles/economico.json',
]

describe('prettier gate (r0-2)', () => {
  it('does not flag pair-managed files', () => {
    expect(listDifferent(pairManaged)).toEqual([])
  })

  it('still flags an unformatted file outside the ignore list', () => {
    const f = join(mkdtempSync(join(tmpdir(), 'prettier-gate-')), 'probe.js')
    writeFileSync(f, 'const   a =  1\n')
    expect(listDifferent([f]).map(p => resolve(repoRoot, p))).toEqual([f])
  })
})

describe('prettier gate (r1-2)', () => {
  it('does not flag sealer-written red-snapshot manifests', () => {
    const dir = '.pair/red-snapshots'
    const manifests = existsSync(join(repoRoot, dir))
      ? readdirSync(join(repoRoot, dir))
          .filter(f => f.endsWith('.json'))
          .map(f => `${dir}/${f}`)
      : []
    expect(listDifferent(manifests)).toEqual([])
  })
})
