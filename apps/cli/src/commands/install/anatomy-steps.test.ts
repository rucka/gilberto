import {
  mkdirSync,
  mkdtempSync,
  existsSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { getSeedRoot } from '@foomakers/gilberto-vault-bootstrap'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  BUNDLED_PLUGINS,
  MISSING_PACKAGE_MESSAGE,
  printBundledPlugins,
  runAnatomySteps,
} from './anatomy-steps.js'

let tmp: string
let out: string[]
let err: string[]

const run = (over: Partial<Parameters<typeof runAnatomySteps>[0]> = {}) =>
  runAnatomySteps({
    tmp,
    date: '2026-10-29',
    topics: [],
    verbose: false,
    write: t => out.push(t),
    error: t => err.push(t),
    loadSeedRoot: async () => getSeedRoot(),
    ...over,
  })

const tree = (dir: string, base = dir): string[] =>
  readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? tree(join(dir, e.name), base) : [join(dir, e.name).slice(base.length + 1)],
  )

beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), 'gilberto-install-test-'))
  out = []
  err = []
})
afterEach(() => rmSync(tmp, { recursive: true, force: true }))

describe('step 5 — printBundledPlugins (AC1)', () => {
  it('prints the five first-party plugins, one line each, no install', () => {
    printBundledPlugins(t => out.push(t))
    const text = out.join('')
    expect(BUNDLED_PLUGINS.map(p => p.name)).toEqual([
      'gilberto-core',
      'pulse-health-tracking',
      'pulse-ratko',
      'projects-venture',
      'projects-editorial',
    ])
    for (const p of BUNDLED_PLUGINS) {
      expect(p.description.length).toBeGreaterThan(0)
      expect(text).toContain(`${p.name} — ${p.description}`)
    }
    expect(text.trimEnd().split('\n')).toHaveLength(5)
  })
})

describe('step 6 — runAnatomySteps', () => {
  it('AC2: copies the anatomy files into <tmp>/anatomy, no registries/types', async () => {
    expect(await run()).toBe(0)
    const files = tree(join(tmp, 'anatomy')).sort()
    expect(files).toEqual(
      [
        'anatomy.md',
        'gilberto.md',
        'playbooks/.gitkeep',
        'plugins.md',
        'preferences.md',
        'scopes.md',
        'templates/.gitkeep',
        'topics.md',
      ].sort(),
    )
    expect(existsSync(join(tmp, 'anatomy', 'registries.md'))).toBe(false)
    expect(existsSync(join(tmp, 'anatomy', 'types.md'))).toBe(false)
  })

  it('AC3: replaces only {{DATE}}; every other byte equals source', async () => {
    await run()
    const src = join(getSeedRoot(), 'anatomy')
    for (const f of tree(src).filter(f => f !== 'topics.md')) {
      const expected = readFileSync(join(src, f), 'utf8').replaceAll('{{DATE}}', '2026-10-29')
      expect(readFileSync(join(tmp, 'anatomy', f), 'utf8')).toBe(expected)
    }
    expect(readFileSync(join(tmp, 'anatomy', 'gilberto.md'), 'utf8')).not.toContain('{{DATE}}')
    expect(readFileSync(join(tmp, 'anatomy', 'anatomy.md'), 'utf8')).toContain(
      "created: '2026-10-29'",
    )
  })

  it('AC4: appends one row per unique topic in input order', async () => {
    await run({ topics: ['health', 'work', 'health', 'travel'] })
    const src = readFileSync(join(getSeedRoot(), 'anatomy', 'topics.md'), 'utf8').replaceAll(
      '{{DATE}}',
      '2026-10-29',
    )
    const got = readFileSync(join(tmp, 'anatomy', 'topics.md'), 'utf8')
    expect(got).toBe(`${src.trimEnd()}\n| health | |\n| work | |\n| travel | |\n`)
  })

  it('AC4: no seeds → header only (equals dated source)', async () => {
    await run()
    const src = readFileSync(join(getSeedRoot(), 'anatomy', 'topics.md'), 'utf8').replaceAll(
      '{{DATE}}',
      '2026-10-29',
    )
    expect(readFileSync(join(tmp, 'anatomy', 'topics.md'), 'utf8')).toBe(src)
  })

  it.each([
    [
      'import throws',
      async () => {
        throw new Error('boom')
      },
    ],
    ['seed/anatomy missing', async () => join(tmp, 'no-seed')],
  ])('AC5: %s → message, tmp removed, exit 70', async (_n, loadSeedRoot) => {
    expect(await run({ loadSeedRoot })).toBe(70)
    expect(err.join('')).toContain(MISSING_PACKAGE_MESSAGE)
    expect(MISSING_PACKAGE_MESSAGE).toBe(
      'vault-bootstrap content package not found; reinstall gilberto',
    )
    expect(existsSync(tmp)).toBe(false)
  })

  it('edge: unreadable seed file → failed to seed anatomy: <path>, exit 70, tmp removed', async () => {
    const seed = mkdtempSync(join(tmpdir(), 'gilberto-seed-test-'))
    try {
      mkdirSync(join(seed, 'anatomy'))
      writeFileSync(join(seed, 'anatomy', 'a.md'), 'x')
      const bad = join(seed, 'anatomy', 'topics.md')
      symlinkSync(join(seed, 'nope'), bad)
      expect(await run({ loadSeedRoot: async () => seed })).toBe(70)
      expect(err.join('')).toContain(`failed to seed anatomy: ${bad}`)
      expect(existsSync(tmp)).toBe(false)
    } finally {
      rmSync(seed, { recursive: true, force: true })
    }
  })

  it('AC6: --verbose prints one wrote line per item; silent otherwise', async () => {
    await run()
    expect(out).toEqual([])
    await run({ verbose: true })
    const lines = out.join('').trimEnd().split('\n')
    const root = join(tmp, 'anatomy')
    expect(lines).toContain(`wrote dir=${root}`)
    expect(lines).toContain(`wrote dir=${join(root, 'playbooks')}`)
    expect(lines).toContain(`wrote file=${join(root, 'topics.md')}`)
    expect(lines).toContain(`wrote file=${join(root, 'playbooks', '.gitkeep')}`)
    expect(lines.every(l => /^wrote (file|dir)=/.test(l))).toBe(true)
    expect(lines).toHaveLength(3 + 8)
  })
})
