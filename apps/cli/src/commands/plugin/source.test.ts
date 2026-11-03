import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { resolveSource } from './source.js'
import { gitRepo, makePlugin, write } from './testkit.js'

const m = (name: string) => ({ name, description: 'd', gilberto: { kind: 'core' } })

const bundled = (): string => {
  const root = mkdtempSync(join(tmpdir(), 'bundled-'))
  makePlugin(m('alpha'), {}, root, 'alpha')
  makePlugin(m('beta'), {}, root, 'beta')
  return root
}

describe('resolveSource', () => {
  it('bundled name -> plugin dir, no-op cleanup', () => {
    const root = bundled()
    const s = resolveSource('alpha', root)
    expect(s.dirs).toEqual([join(root, 'alpha')])
    s.cleanup()
    expect(existsSync(join(root, 'alpha'))).toBe(true)
  })

  it('unknown name -> error lists bundled names', () => {
    expect(() => resolveSource('nope', bundled())).toThrow(/bundled: alpha, beta/)
  })

  it('traversal-like name -> error, never resolved', () => {
    expect(() => resolveSource('../x', bundled())).toThrow(/unknown plugin/)
  })

  it('single-plugin repo url -> clone, cleanup removes temp', () => {
    const url = gitRepo(makePlugin(m('single')))
    const s = resolveSource(url, bundled())
    expect(s.dirs).toHaveLength(1)
    expect(existsSync(join(s.dirs[0]!, '.claude-plugin', 'plugin.json'))).toBe(true)
    s.cleanup()
    expect(existsSync(s.dirs[0]!)).toBe(false)
  })

  it('multi-plugin repo -> every subdir with manifest', () => {
    const parent = mkdtempSync(join(tmpdir(), 'multi-'))
    makePlugin(m('a'), {}, parent, 'a')
    makePlugin(m('b'), {}, parent, 'b')
    makePlugin(m('c'), {}, parent, 'docs-only/nested')
    const s = resolveSource(gitRepo(parent), bundled())
    expect(s.dirs.map(d => d.split('/').pop()).sort()).toEqual(['a', 'b'])
    s.cleanup()
  })

  it('repo without any manifest -> error', () => {
    const parent = mkdtempSync(join(tmpdir(), 'empty-'))
    write(parent, 'README.md', 'x')
    expect(() => resolveSource(gitRepo(parent), bundled())).toThrow(/no plugin found/)
  })

  it('clone failure -> error, no temp left', () => {
    expect(() => resolveSource('file:///does/not/exist.git', bundled())).toThrow(
      /git clone failed/,
    )
  })
})
