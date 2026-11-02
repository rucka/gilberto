import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const DOCS = join(__dirname, '..', 'content', 'docs')
const SKILLS = join(__dirname, '..', '..', '..', 'plugins', 'gilberto-core', 'skills')

const metaDirs = (dir: string): string[] =>
  readdirSync(dir)
    .filter(n => statSync(join(dir, n)).isDirectory())
    .flatMap(n => metaDirs(join(dir, n)))
    .concat(existsSync(join(dir, 'meta.json')) ? [dir] : [])

describe('docs content tree', () => {
  it.each(metaDirs(DOCS))('every meta.json page exists in %s', dir => {
    const { pages } = JSON.parse(readFileSync(join(dir, 'meta.json'), 'utf8')) as {
      pages: string[]
    }
    for (const p of pages.filter(p => !p.startsWith('---'))) {
      expect(existsSync(join(dir, `${p}.mdx`)) || existsSync(join(dir, p)), `${dir}/${p}`).toBe(
        true,
      )
    }
  })

  it('skills catalog lists every gilberto-core skill', () => {
    const catalog = readFileSync(join(DOCS, 'reference', 'skills.mdx'), 'utf8')
    const skills = readdirSync(SKILLS).filter(n => existsSync(join(SKILLS, n, 'SKILL.md')))
    expect(skills.length).toBeGreaterThan(0)
    for (const s of skills) expect(catalog, s).toContain(`\`${s}\``)
  })
})
