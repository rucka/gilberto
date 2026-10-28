import { execFileSync, spawnSync } from 'node:child_process'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { parse } from 'yaml'
import { PILLARS, getSeedRoot } from './index.js'

const seed = getSeedRoot()
const read = (p: string) => readFileSync(join(seed, p), 'utf8')

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? walk(join(dir, e.name)) : [relative(seed, join(dir, e.name))],
  )
}

const frontmatter = (p: string): Record<string, unknown> => {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(read(p))
  expect(m, `${p} has frontmatter`).not.toBeNull()
  return parse(m![1]!) as Record<string, unknown>
}

const headings = (p: string) => [...read(p).matchAll(/^## (.+)$/gm)].map(m => m[1])

describe('seed file list', () => {
  it('matches the contract', () => {
    expect(walk(seed).sort()).toEqual(
      [
        'anatomy/anatomy.md',
        'anatomy/gilberto.md',
        'anatomy/playbooks/.gitkeep',
        'anatomy/plugins.md',
        'anatomy/preferences.md',
        'anatomy/scopes.md',
        'anatomy/templates/.gitkeep',
        'anatomy/topics.md',
        'hooks/dispatch.sh',
        'launchd/ingest-watch.plist',
        'launchd/morning-briefing.plist',
        'launchd/reflect-day.plist',
        'skeleton/CLAUDE.md',
        'skeleton/_ingest/.gitkeep',
        ...PILLARS.map(p => `skeleton/${p}/${p}.md`),
        'skeleton/network/companies/.gitkeep',
        'skeleton/network/people/.gitkeep',
      ].sort(),
    )
  })

  it('has no registries.md / types.md', () => {
    const files = walk(join(seed, 'anatomy'))
    expect(files).not.toContain('anatomy/registries.md')
    expect(files).not.toContain('anatomy/types.md')
  })
})

describe('anatomy', () => {
  it('has required headings', () => {
    expect(headings('anatomy/anatomy.md')).toEqual(['Types', 'Relationship levels'])
    expect(headings('anatomy/preferences.md')).toEqual([
      'Silence',
      'Thresholds',
      'Cadences',
      'Integrations',
    ])
  })

  it('scopes registry is an empty placeholder', () => {
    const rows = read('anatomy/scopes.md')
      .split('\n')
      .filter(l => l.startsWith('|'))
    expect(rows).toHaveLength(2)
  })

  it.each(walk(join(seed, 'anatomy')).filter(f => f.endsWith('.md')))(
    '%s frontmatter parses',
    f => {
      expect(frontmatter(f)).toHaveProperty('type')
    },
  )
})

describe('skeleton', () => {
  it.each(PILLARS)('%s folder-note', pillar => {
    const fm = frontmatter(`skeleton/${pillar}/${pillar}.md`)
    expect(fm['type']).toBe(`${pillar}-index`)
    expect(fm['topics']).toEqual([])
    expect(fm).toHaveProperty('created')
    expect(fm).toHaveProperty('updated')
  })

  it('pillar dirs equal PILLARS', () => {
    const dirs = readdirSync(join(seed, 'skeleton'), { withFileTypes: true })
      .filter(e => e.isDirectory() && e.name !== '_ingest')
      .map(e => e.name)
    expect(dirs.sort()).toEqual([...PILLARS].sort())
  })
})

describe('hooks', () => {
  const hook = join(seed, 'hooks/dispatch.sh')

  it('is executable and POSIX-valid', () => {
    expect(statSync(hook).mode & 0o111).not.toBe(0)
    expect(spawnSync('sh', ['-n', hook]).status).toBe(0)
  })

  it('exits 0 printing "skill not installed" when skill missing', () => {
    const r = spawnSync(hook, ['no-such-skill'], {
      encoding: 'utf8',
      env: { ...process.env, GILBERTO_SKILLS_DIR: '/nonexistent' },
    })
    expect(r.status).toBe(0)
    expect(r.stdout.trim()).toBe('skill not installed')
  })
})

describe('launchd', () => {
  it.each(['morning-briefing', 'reflect-day', 'ingest-watch'])('%s has placeholders', name => {
    const s = read(`launchd/${name}.plist`)
    expect(s).toContain('{{VAULT_ROOT}}')
    expect(s).toContain('{{LABEL_PREFIX}}')
    expect(s).not.toContain('RunAtLoad')
  })

  it('ingest-watch watches _ingest', () => {
    expect(read('launchd/ingest-watch.plist')).toMatch(
      /<key>WatchPaths<\/key>\s*<array>\s*<string>\{\{VAULT_ROOT\}\}\/_ingest<\/string>/,
    )
  })
})

describe('npm pack', () => {
  it('ships dist + seed (dotfiles, hook mode), excludes tests', () => {
    const pkgDir = fileURLToPath(new URL('..', import.meta.url))
    const out = execFileSync('npm', ['pack', '--dry-run', '--json'], {
      cwd: pkgDir,
      encoding: 'utf8',
    })
    const files = (JSON.parse(out) as [{ files: { path: string; mode: number }[] }])[0].files
    const paths = files.map(f => f.path)
    expect(paths).toContain('dist/index.js')
    expect(paths).toContain('seed/anatomy/playbooks/.gitkeep')
    expect(paths).toContain('seed/skeleton/_ingest/.gitkeep')
    expect(paths.filter(p => /\.test\./.test(p))).toEqual([])
    for (const f of walk(seed)) expect(paths).toContain(`seed/${f}`)
    expect(files.find(f => f.path === 'seed/hooks/dispatch.sh')!.mode & 0o111).not.toBe(0)
  })
})
