import { spawnSync } from 'node:child_process'
import { cpSync, mkdtempSync, rmSync, symlinkSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterAll, describe, expect, it } from 'vitest'

const pkg = join(import.meta.dirname, '..')
const NESTED = 'GILBERTO_CLEAN_CHECKOUT'
const tmp = mkdtempSync(join(tmpdir(), 'vb-clean-'))

afterAll(() => rmSync(tmp, { recursive: true, force: true }))

describe.skipIf(process.env[NESTED])('package test script on a clean checkout (no dist)', () => {
  it('builds first: pnpm run test exits 0 without a prebuilt dist/', () => {
    for (const f of [
      'package.json',
      'tsconfig.json',
      'tsconfig.build.json',
      'vitest.config.ts',
      'src',
      'seed',
    ]) {
      cpSync(join(pkg, f), join(tmp, f), { recursive: true })
    }
    symlinkSync(join(pkg, 'node_modules'), join(tmp, 'node_modules'))
    const r = spawnSync('pnpm', ['run', 'test', 'src/index.test.ts', 'src/seed.test.ts'], {
      cwd: tmp,
      encoding: 'utf8',
      env: { ...process.env, [NESTED]: '1', CI: '1' },
    })
    expect(r.status, `${r.stdout}\n${r.stderr}`).toBe(0)
  }, 120_000)
})
