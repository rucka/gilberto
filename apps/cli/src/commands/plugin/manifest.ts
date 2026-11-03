import { readFileSync, realpathSync } from 'node:fs'
import { basename, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { z } from 'zod'

const paths = z.array(z.string().min(1))

const gilbertoBlock = z
  .object({
    kind: z.enum(['core', 'pillar', 'connector']),
    pillar: z.string().min(1).optional(),
    skills: paths.optional(),
    templates: paths.optional(),
    playbooks: z.record(z.string().min(1)).optional(),
    processes: paths.optional(),
    capabilities: paths.optional(),
    preferences: z.string().min(1).optional(),
    routes: z.record(z.string().min(1)).optional(),
  })
  .strict()

export const manifestSchema = z
  .object({
    name: z.string().min(1),
    description: z.string().min(1),
    author: z
      .object({ name: z.string().min(1) })
      .passthrough()
      .optional(),
    skills: paths.default([]),
    gilberto: gilbertoBlock,
  })
  .passthrough()

export type Manifest = z.infer<typeof manifestSchema>
export type ManifestResult = { ok: true; manifest: Manifest } | { ok: false; errors: string[] }

export const MANIFEST_PATH = join('.claude-plugin', 'plugin.json')

const fail = (...errors: string[]): ManifestResult => ({ ok: false, errors })

export function parseManifest(file: string): ManifestResult {
  let raw: unknown
  try {
    raw = JSON.parse(readFileSync(file, 'utf8'))
  } catch (e) {
    return fail(`${file}: ${e instanceof Error ? e.message : String(e)}`)
  }
  const parsed = manifestSchema.safeParse(raw)
  if (parsed.success) return { ok: true, manifest: parsed.data }
  return fail(
    ...parsed.error.issues.map(i => {
      const keys = i.code === 'unrecognized_keys' ? `: ${i.keys.join(', ')}` : ''
      return `${file}: ${i.path.join('.') || '(root)'}: ${i.message}${keys}`
    }),
  )
}

const normalize = (p: string): string => join(p)

function duplicateSkills(skills: string[]): string[] {
  const names = new Set<string>()
  const seen = new Set<string>()
  const errors: string[] = []
  for (const skill of skills) {
    const path = normalize(skill)
    const name = basename(path)
    if (seen.has(path) || names.has(name)) errors.push(`duplicate skill: ${skill}`)
    seen.add(path)
    names.add(name)
  }
  return errors
}

function pillarErrors({ kind, pillar, playbooks = {} }: Manifest['gilberto']): string[] {
  if (kind === 'pillar' && !pillar)
    return ['pillar mismatch: kind "pillar" requires gilberto.pillar']
  if (kind !== 'pillar' && pillar)
    return [`pillar mismatch: kind "${kind}" must not declare gilberto.pillar ("${pillar}")`]
  return Object.keys(playbooks)
    .filter(key => key.split('/')[0] !== pillar)
    .map(key => `pillar mismatch: playbook "${key}" does not belong to pillar "${pillar ?? '(none)'}"`)
}

function insidePluginDir(dir: string, skill: string): boolean {
  try {
    const rel = relative(realpathSync(dir), realpathSync(resolve(dir, skill)))
    return !(rel === '..' || rel.startsWith('..' + sep) || isAbsolute(rel))
  } catch {
    return false
  }
}

function missingSkills(dir: string, skills: string[]): string[] {
  return skills
    .filter(skill => !insidePluginDir(dir, skill))
    .map(skill => `skills path not found under plugin dir: ${skill}`)
}

export function validateManifest(dir: string): ManifestResult {
  const parsed = parseManifest(join(dir, MANIFEST_PATH))
  if (!parsed.ok) return parsed
  const { manifest } = parsed
  const skills = [...manifest.skills, ...(manifest.gilberto.skills ?? [])]
  const errors = [
    ...duplicateSkills(skills),
    ...pillarErrors(manifest.gilberto),
    ...missingSkills(dir, skills),
  ]
  return errors.length ? { ok: false, errors } : parsed
}
