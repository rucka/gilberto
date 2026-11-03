import {
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, join, relative, resolve } from 'node:path'
import { insidePluginDir, validateManifest, type Manifest } from './manifest.js'
import { readRecord, recordRel, sha256 } from './record.js'
import { addRow, assertVault, hasPlugin, registryPath, removeRow } from './registry.js'

export type InstallOptions = {
  force: boolean
  dryRun: boolean
  now?: () => string
  onMove?: (index: number) => void
}

export type InstallResult = {
  name: string
  version: string
  files: string[]
  skills: string[]
  dryRun: boolean
}

type Entry = { src: string; dest: string }

const SAFE = /^[A-Za-z0-9][\w.-]*$/

export class PluginInstallError extends Error {
  constructor(readonly errors: string[]) {
    super(errors.join('\n'))
  }
}

const versionOf = (m: Manifest): string =>
  typeof m['version'] === 'string' ? m['version'] : '0.0.0'

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

function plan(dir: string, name: string, m: Manifest): { entries: Entry[]; errors: string[] } {
  const errors: string[] = []
  const entries: Entry[] = []
  const { playbooks = {}, templates = [], pillar } = m.gilberto
  for (const [key, rel] of Object.entries(playbooks)) {
    const parts = key.split('/')
    const src = resolve(dir, rel)
    if (parts.length !== 2 || !parts.every(p => SAFE.test(p)))
      errors.push(`invalid playbook key: ${key}`)
    else if (!insidePluginDir(dir, rel) || !statSync(src).isFile())
      errors.push(`playbook path not found under plugin dir: ${rel}`)
    else if (lstatSync(src).isSymbolicLink()) errors.push(`symlink not allowed: ${rel}`)
    else entries.push({ src, dest: join('anatomy', 'playbooks', ...parts, `${name}.md`) })
  }
  for (const rel of templates) {
    const src = resolve(dir, rel)
    const tname = basename(src)
    if (!pillar) errors.push(`template "${rel}" requires gilberto.pillar`)
    else if (!SAFE.test(tname)) errors.push(`invalid template name: ${rel}`)
    else if (!insidePluginDir(dir, rel) || !statSync(src).isDirectory())
      errors.push(`template path not found under plugin dir: ${rel}`)
    else
      for (const f of walk(src, errors))
        entries.push({
          src: f,
          dest: join('anatomy', 'templates', pillar, tname, relative(src, f)),
        })
  }
  const seen = new Set<string>()
  for (const { dest } of entries) {
    if (seen.has(dest)) errors.push(`duplicate contribution path: ${dest}`)
    seen.add(dest)
  }
  return { entries, errors }
}

const topMissing = (path: string): string | undefined => {
  let top: string | undefined
  for (let p = path; !existsSync(p); p = dirname(p)) top = p
  return top
}

export function installPlugin(vault: string, dir: string, opts: InstallOptions): InstallResult {
  assertVault(vault)
  const label = basename(dir)
  const parsed = validateManifest(dir)
  if (!parsed.ok) throw new PluginInstallError(parsed.errors.map(e => `${label}: ${e}`))
  const { manifest } = parsed
  const name = manifest.name
  if (!SAFE.test(name)) throw new PluginInstallError([`${label}: invalid plugin name: ${name}`])
  const installed = hasPlugin(vault, name)
  if (installed && !opts.force)
    throw new PluginInstallError([`${name}: already installed (use --force to overwrite)`])

  const { entries, errors } = plan(dir, name, manifest)
  const own = installed ? (readRecord(vault, name)?.files ?? {}) : {}
  for (const { dest } of entries)
    if (existsSync(join(vault, dest)) && !(dest in own))
      errors.push(`${name}: collision, ${dest} already exists and is not contributed by ${name}`)
  if (errors.length) throw new PluginInstallError(errors)

  const skills = [...manifest.skills, ...(manifest.gilberto.skills ?? [])]
  const files = entries.map(e => e.dest)
  const result: InstallResult = {
    name,
    version: versionOf(manifest),
    files,
    skills,
    dryRun: opts.dryRun,
  }
  if (opts.dryRun) return result

  const stage = mkdtempSync(join(vault, 'anatomy', '.stage-'))
  const undo: (() => void)[] = []
  const registry = readFileSync(registryPath(vault), 'utf8')
  try {
    const record = {
      files: Object.fromEntries(entries.map(e => [e.dest, sha256(readFileSync(e.src))])),
    }
    const staged: Entry[] = [...entries, { src: join(stage, 'record.json'), dest: recordRel(name) }]
    writeFileSync(join(stage, 'record.json'), JSON.stringify(record, null, 2))
    staged.forEach((e, i) => cpSync(e.src, join(stage, 'new', String(i))))

    const stale = Object.keys(own).filter(d => !files.includes(d))
    ;[...staged.map(e => e.dest), ...stale].forEach((d, i) => {
      const live = join(vault, d)
      if (!existsSync(live)) return
      const bak = join(stage, 'backup', String(i))
      mkdirSync(dirname(bak), { recursive: true })
      renameSync(live, bak)
      undo.push(() => {
        mkdirSync(dirname(live), { recursive: true })
        renameSync(bak, live)
      })
    })
    staged.forEach((e, i) => {
      const live = join(vault, e.dest)
      const created = topMissing(dirname(live))
      mkdirSync(dirname(live), { recursive: true })
      undo.push(() => {
        rmSync(live, { force: true })
        if (created) rmSync(created, { recursive: true, force: true })
      })
      renameSync(join(stage, 'new', String(i)), live)
      opts.onMove?.(i)
    })
    undo.push(() => writeFileSync(registryPath(vault), registry))
    removeRow(vault, name)
    addRow(vault, {
      name,
      version: result.version,
      installed: (opts.now ?? (() => new Date().toISOString().slice(0, 10)))(),
    })
  } catch (e) {
    for (const u of undo.reverse()) u()
    throw e
  } finally {
    rmSync(stage, { recursive: true, force: true })
  }
  return result
}
