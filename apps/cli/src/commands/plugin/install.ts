import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { basename, dirname, join } from 'node:path'
import { validateManifest, type Manifest } from './manifest.js'
import { planContributions, SAFE, type Entry } from './plan.js'
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

export class PluginInstallError extends Error {
  constructor(readonly errors: string[]) {
    super(errors.join('\n'))
  }
}

const versionOf = (m: Manifest): string =>
  typeof m['version'] === 'string' ? m['version'] : '0.0.0'

const today = (): string => new Date().toISOString().slice(0, 10)

const topMissing = (path: string): string | undefined => {
  let top: string | undefined
  for (let p = path; !existsSync(p); p = dirname(p)) top = p
  return top
}

const collisions = (
  vault: string,
  name: string,
  entries: Entry[],
  own: Record<string, string>,
): string[] =>
  entries
    .filter(({ dest }) => existsSync(join(vault, dest)) && !(dest in own))
    .map(
      ({ dest }) => `${name}: collision, ${dest} already exists and is not contributed by ${name}`,
    )

type Prepared = { manifest: Manifest; entries: Entry[]; own: Record<string, string> }

function prepare(vault: string, dir: string, opts: InstallOptions): Prepared {
  const label = basename(dir)
  const parsed = validateManifest(dir)
  if (!parsed.ok) throw new PluginInstallError(parsed.errors.map(e => `${label}: ${e}`))
  const { manifest } = parsed
  const name = manifest.name
  if (!SAFE.test(name)) throw new PluginInstallError([`${label}: invalid plugin name: ${name}`])
  const version = versionOf(manifest)
  if (/[|\r\n]/.test(version))
    throw new PluginInstallError([
      `${label}: invalid version (no '|' or newline): ${JSON.stringify(version)}`,
    ])
  const installed = hasPlugin(vault, name)
  if (installed && !opts.force)
    throw new PluginInstallError([`${name}: already installed (use --force to overwrite)`])
  const { entries, errors } = planContributions(dir, name, manifest)
  const own = installed ? (readRecord(vault, name)?.files ?? {}) : {}
  errors.push(...collisions(vault, name, entries, own))
  if (errors.length) throw new PluginInstallError(errors)
  return { manifest, entries, own }
}

type Undo = (() => void)[]
type Tx = { undo: Undo; onMove: InstallOptions['onMove'] }

function backup(vault: string, stage: string, dests: string[], undo: Undo): void {
  dests.forEach((d, i) => {
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
}

function move(vault: string, stage: string, dests: string[], tx: Tx): void {
  dests.forEach((d, i) => {
    const live = join(vault, d)
    const created = topMissing(dirname(live))
    mkdirSync(dirname(live), { recursive: true })
    tx.undo.push(() => {
      rmSync(live, { force: true })
      if (created) rmSync(created, { recursive: true, force: true })
    })
    renameSync(join(stage, 'new', String(i)), live)
    tx.onMove?.(i)
  })
}

function apply(vault: string, p: Prepared, version: string, opts: InstallOptions): void {
  const name = p.manifest.name
  const stage = mkdtempSync(join(vault, 'anatomy', '.stage-'))
  const undo: Undo = []
  const registry = readFileSync(registryPath(vault), 'utf8')
  try {
    const files = p.entries.map(e => e.dest)
    const record = {
      files: Object.fromEntries(p.entries.map(e => [e.dest, sha256(readFileSync(e.src))])),
    }
    writeFileSync(join(stage, 'record.json'), JSON.stringify(record, null, 2))
    const staged = [...p.entries, { src: join(stage, 'record.json'), dest: recordRel(name) }]
    staged.forEach((e, i) => cpSync(e.src, join(stage, 'new', String(i))))
    const dests = staged.map(e => e.dest)
    const stale = Object.keys(p.own).filter(d => !files.includes(d))
    backup(vault, stage, [...dests, ...stale], undo)
    move(vault, stage, dests, { undo, onMove: opts.onMove })
    undo.push(() => writeFileSync(registryPath(vault), registry))
    removeRow(vault, name)
    addRow(vault, { name, version, installed: (opts.now ?? today)() })
  } catch (e) {
    for (const u of undo.reverse()) u()
    throw e
  } finally {
    rmSync(stage, { recursive: true, force: true })
  }
}

export function installPlugin(vault: string, dir: string, opts: InstallOptions): InstallResult {
  assertVault(vault)
  const prepared = prepare(vault, dir, opts)
  const { manifest } = prepared
  const result: InstallResult = {
    name: manifest.name,
    version: versionOf(manifest),
    files: prepared.entries.map(e => e.dest),
    skills: [...manifest.skills, ...(manifest.gilberto.skills ?? [])],
    dryRun: opts.dryRun,
  }
  if (!opts.dryRun) apply(vault, prepared, result.version, opts)
  return result
}
