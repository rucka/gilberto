import { execFileSync } from 'node:child_process'
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { defaultBundledRoot, resolveSource } from './source.js'

const here = dirname(fileURLToPath(import.meta.url))
const cliDir = join(here, '..', '..', '..')
const repoRoot = join(cliDir, '..', '..')
const PLUGIN_JSON = 'plugins/gilberto-core/.claude-plugin/plugin.json'

let tmp: string
let packed: string[]
let pkgDir: string

function listFiles(dir: string, base = dir): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory()
      ? listFiles(join(dir, e.name), base)
      : e.name === '.DS_Store'
        ? []
        : [relative(base, join(dir, e.name)).split(sep).join('/')],
  )
}

function transpileTree(srcDir: string, outDir: string): void {
  for (const e of readdirSync(srcDir, { withFileTypes: true })) {
    const from = join(srcDir, e.name)
    if (e.isDirectory()) transpileTree(from, join(outDir, e.name))
    else if (e.name.endsWith('.ts') && !e.name.endsWith('.test.ts') && !e.name.endsWith('.d.ts')) {
      mkdirSync(outDir, { recursive: true })
      const js = ts.transpileModule(readFileSync(from, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
      }).outputText
      writeFileSync(join(outDir, e.name.replace(/\.ts$/, '.js')), js)
    }
  }
}

function resolveFromPacked(arg: string): { ok: boolean; out: string } {
  const script = join(tmp, 'probe.mjs')
  const entry = join(pkgDir, 'dist', 'commands', 'plugin', 'source.js')
  writeFileSync(
    script,
    `import { resolveSource } from ${JSON.stringify(entry)}
try { console.log(JSON.stringify({ ok: true, out: resolveSource(${JSON.stringify(arg)}).dirs })) }
catch (e) { console.log(JSON.stringify({ ok: false, out: e.message })) }
`,
  )
  const r = JSON.parse(execFileSync('node', [script], { encoding: 'utf8' })) as {
    ok: boolean
    out: unknown
  }
  return { ok: r.ok, out: JSON.stringify(r.out) }
}

beforeAll(() => {
  tmp = mkdtempSync(join(tmpdir(), 'packed-'))
  const cli = join(tmp, 'apps', 'cli')
  mkdirSync(join(cli, 'dist'), { recursive: true })
  for (const f of ['package.json', 'README.md']) cpSync(join(cliDir, f), join(cli, f))
  cpSync(join(cliDir, 'scripts'), join(cli, 'scripts'), { recursive: true })
  cpSync(join(repoRoot, 'plugins'), join(tmp, 'plugins'), { recursive: true })
  transpileTree(join(cliDir, 'src'), join(cli, 'dist'))
  writeFileSync(join(cli, 'dist', 'cli.js'), '#!/usr/bin/env node\n')
  execFileSync('node', ['scripts/postbuild.js'], { cwd: cli, stdio: 'pipe' })
  const dest = join(tmp, 'tarballs')
  mkdirSync(dest)
  const out = execFileSync(
    'npm',
    ['pack', '--json', '--offline', '--ignore-scripts', '--pack-destination', dest],
    { cwd: cli, encoding: 'utf8' },
  )
  const info = JSON.parse(out) as { filename: string; files: { path: string }[] }[]
  packed = info[0]!.files.map(f => f.path)
  rmSync(join(tmp, 'plugins'), { recursive: true, force: true })
  const nm = join(tmp, 'node_modules')
  mkdirSync(nm)
  const cliNm = join(cliDir, 'node_modules')
  for (const e of readdirSync(cliNm)) {
    if (e !== '.bin') symlinkSync(join(cliNm, e), join(nm, e))
  }
  pkgDir = join(nm, 'gilberto')
  mkdirSync(pkgDir)
  execFileSync('tar', ['-xzf', join(dest, info[0]!.filename), '-C', pkgDir, '--strip-components=1'])
}, 120_000)

afterAll(() => rmSync(tmp, { recursive: true, force: true }))

describe('r0-2 bundled plugins ship inside the CLI package', () => {
  it('W-r0-2a packed file list contains the whole repo plugins/ tree', () => {
    expect(packed).toContain(PLUGIN_JSON)
    const missing = listFiles(join(repoRoot, 'plugins'))
      .map(f => `plugins/${f}`)
      .filter(f => !packed.includes(f))
    expect(missing).toEqual([])
  })

  it('W-r0-2b resolveSource(gilberto-core) from the packed layout resolves inside the package', () => {
    const r = resolveFromPacked('gilberto-core')
    expect(r.ok, r.out).toBe(true)
    const [dir] = JSON.parse(r.out) as string[]
    expect(dir).toBeDefined()
    expect(relative(pkgDir, dir!).startsWith('..')).toBe(false)
    expect(existsSync(join(dir!, '.claude-plugin', 'plugin.json'))).toBe(true)
  })

  it('B-r0-2c unknown name from the packed layout lists gilberto-core as bundled', () => {
    const r = resolveFromPacked('nope')
    expect(r.ok).toBe(false)
    expect(r.out).toMatch(/bundled: [^"]*gilberto-core/)
  })

  it('C-r0-2d dist and README still packed, cli.js shipped', () => {
    expect(packed).toContain('dist/cli.js')
    expect(packed).toContain('dist/commands/plugin/source.js')
    expect(packed).toContain('README.md')
  })

  it('C-r0-2e traversal-like name is still rejected from the packed layout', () => {
    const r = resolveFromPacked('../x')
    expect(r.ok).toBe(false)
    expect(r.out).toMatch(/unknown plugin/)
  })

  it('C-r0-2f monorepo layout (src) still resolves gilberto-core with no override', () => {
    const [dir] = resolveSource('gilberto-core').dirs
    expect(dir).toBeDefined()
    expect(
      existsSync(join(defaultBundledRoot(), 'gilberto-core', '.claude-plugin', 'plugin.json')),
    ).toBe(true)
    expect(existsSync(join(dir!, '.claude-plugin', 'plugin.json'))).toBe(true)
  })
})
