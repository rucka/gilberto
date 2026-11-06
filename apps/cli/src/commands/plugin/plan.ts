import { lstatSync, readdirSync, statSync } from 'node:fs'
import { basename, join, relative, resolve } from 'node:path'
import { insidePluginDir, type Manifest } from './manifest.js'

export type Entry = { src: string; dest: string }
type Plan = { entries: Entry[]; errors: string[] }

export const SAFE = /^[A-Za-z0-9][\w.-]*$/

function walk(dir: string, errors: string[]): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap(e => {
    const p = join(dir, e.name)
    if (e.isSymbolicLink()) {
      errors.push(`symlink not allowed in plugin contributions: ${p}`)
      return []
    }
    return e.isDirectory() ? walk(p, errors) : [p]
  })
}

function playbook(dir: string, name: string, key: string, rel: string): Entry | string {
  const parts = key.split('/')
  if (parts.length !== 2 || !parts.every(p => SAFE.test(p))) return `invalid playbook key: ${key}`
  const src = resolve(dir, rel)
  if (!insidePluginDir(dir, rel) || !statSync(src).isFile())
    return `playbook path not found under plugin dir: ${rel}`
  if (lstatSync(src).isSymbolicLink()) return `symlink not allowed: ${rel}`
  return { src, dest: join('anatomy', 'playbooks', ...parts, `${name}.md`) }
}

function template(dir: string, pillar: string | undefined, rel: string, errors: string[]): Entry[] {
  const src = resolve(dir, rel)
  const tname = basename(src)
  if (!pillar) errors.push(`template "${rel}" requires gilberto.pillar`)
  else if (!SAFE.test(tname)) errors.push(`invalid template name: ${rel}`)
  else if (!insidePluginDir(dir, rel) || !statSync(src).isDirectory())
    errors.push(`template path not found under plugin dir: ${rel}`)
  else
    return walk(src, errors).map(f => ({
      src: f,
      dest: join('anatomy', 'templates', pillar, tname, relative(src, f)),
    }))
  return []
}

export function planContributions(dir: string, name: string, m: Manifest): Plan {
  const errors: string[] = []
  const { playbooks = {}, templates = [], pillar } = m.gilberto
  const entries: Entry[] = []
  for (const [key, rel] of Object.entries(playbooks)) {
    const r = playbook(dir, name, key, rel)
    if (typeof r === 'string') errors.push(r)
    else entries.push(r)
  }
  for (const rel of templates) entries.push(...template(dir, pillar, rel, errors))
  const dests = entries.map(e => e.dest)
  for (const d of new Set(dests.filter((d, i) => dests.indexOf(d) !== i)))
    errors.push(`duplicate contribution path: ${d}`)
  return { entries, errors }
}
