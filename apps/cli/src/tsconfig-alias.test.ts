import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const cliDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const tsc = resolve(cliDir, 'node_modules/.bin/tsc')

interface ShowConfig {
  compilerOptions: { baseUrl?: string; paths?: Record<string, string[]> }
}

const showConfig = (): ShowConfig =>
  JSON.parse(
    execFileSync(tsc, ['--showConfig', '-p', resolve(cliDir, 'tsconfig.json')], {
      encoding: 'utf8',
    }),
  )

describe('apps/cli tsconfig path aliases (AC-7)', () => {
  it('resolves baseUrl to apps/cli so "#config" maps to apps/cli/src/config', () => {
    const { baseUrl } = showConfig().compilerOptions
    expect(baseUrl).toBeDefined()
    expect(resolve(cliDir, baseUrl as string)).toBe(cliDir)
  })

  it('keeps alias targets relative to src', () => {
    expect(showConfig().compilerOptions.paths?.['#config']).toEqual(['src/config/index.ts'])
  })
})
