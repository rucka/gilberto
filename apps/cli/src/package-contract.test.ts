import { execFileSync } from 'node:child_process'
import { readFileSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const cliDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const pkg = JSON.parse(readFileSync(resolve(cliDir, 'package.json'), 'utf8')) as Record<
  string,
  unknown
>

describe('apps/cli package contract', () => {
  it('AC-6: declares name, bin and module type', () => {
    expect(pkg['name']).toBe('gilberto')
    expect(pkg['bin']).toEqual({ gilberto: 'dist/cli.js' })
    expect(pkg['type']).toBe('module')
  })

  it('AC-3: build emits dist/cli.js with mode 755, idempotently', () => {
    for (let i = 0; i < 2; i++) {
      execFileSync('pnpm', ['run', 'build'], { cwd: cliDir, stdio: 'ignore' })
      expect(statSync(resolve(cliDir, 'dist/cli.js')).mode & 0o777).toBe(0o755)
    }
  }, 60_000)
})
