import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const prettierBin = join(repoRoot, 'tools/prettier-config/node_modules/.bin/prettier')
const ignorePath = join(repoRoot, 'tools/prettier-config/.prettierignore')

describe('cli.ts formatting (r1-6)', () => {
  it('is prettier-formatted', () => {
    const r = spawnSync(
      prettierBin,
      [
        '--list-different',
        '--ignore-path',
        ignorePath,
        '--log-level',
        'log',
        'apps/cli/src/cli.ts',
      ],
      { cwd: repoRoot, encoding: 'utf8' },
    )
    expect(r.stdout.split('\n').filter(Boolean)).toEqual([])
  })
})
