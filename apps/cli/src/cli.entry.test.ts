import { execFileSync, spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { beforeAll, describe, expect, it } from 'vitest'

const cliDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const version = (
  JSON.parse(readFileSync(resolve(cliDir, 'package.json'), 'utf8')) as { version: string }
).version
const run = (script: string, ...a: string[]) =>
  spawnSync(process.execPath, [script, ...a], { encoding: 'utf8' })

describe('entry detection', () => {
  beforeAll(() => {
    execFileSync('pnpm', ['run', 'build'], { cwd: cliDir, stdio: 'ignore' })
  }, 60_000)

  it('r0-2 W1: extensionless path runs the CLI (--version)', () => {
    const r = run(resolve(cliDir, 'dist/cli'), '--version')
    expect(r.stderr).not.toContain('ENOENT')
    expect(r.status).toBe(0)
    expect(r.stdout.trim()).toBe(version)
  })

  it('r0-2 W2: extensionless path runs the CLI (--help)', () => {
    const r = run(resolve(cliDir, 'dist/cli'), '--help')
    expect(r.status).toBe(0)
    expect(r.stdout).toContain('--no-banner')
  })

  it('r0-2 C1: explicit .js path runs the CLI', () => {
    const r = run(resolve(cliDir, 'dist/cli.js'), '--version')
    expect(r.status).toBe(0)
    expect(r.stdout.trim()).toBe(version)
  })

  it('r0-2 C2: symlinked bin shim runs the CLI (--version)', () => {
    const dir = mkdtempSync(resolve(tmpdir(), 'gilberto-shim-'))
    try {
      const link = resolve(dir, 'gilberto')
      symlinkSync(resolve(cliDir, 'dist/cli.js'), link)
      const r = run(link, '--version')
      expect(r.status).toBe(0)
      expect(r.stdout.trim()).toBe(version)
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })

  it('r0-2 C3: nonexistent argv[1] of another module importing dist/cli.js does not run the CLI', () => {
    const dir = mkdtempSync(resolve(tmpdir(), 'gilberto-importer-'))
    try {
      const target = pathToFileURL(resolve(cliDir, 'dist/cli.js')).href
      writeFileSync(
        resolve(dir, 'other.js'),
        `import('${target}').then(() => console.log('imported-ok'))\n`,
      )
      const r = run(resolve(dir, 'other'))
      expect(r.stderr).not.toContain('ENOENT')
      expect(r.status).toBe(0)
      expect(r.stdout.trim()).toBe('imported-ok')
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
