import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { MANIFEST_PATH } from './manifest.js'

export type PluginSource = { dirs: string[]; cleanup: () => void }

export const defaultBundledRoot = (): string =>
  resolve(dirname(fileURLToPath(import.meta.url)), '../../../../../plugins')

const URL_RE = /^(https?:\/\/|ssh:\/\/|git:\/\/|file:\/\/|git@)|\.git$/

const hasManifest = (dir: string): boolean => existsSync(join(dir, MANIFEST_PATH))

const subdirs = (dir: string): string[] =>
  readdirSync(dir, { withFileTypes: true })
    .filter(e => e.isDirectory() && !e.name.startsWith('.'))
    .map(e => join(dir, e.name))

function bundledNames(root: string): string[] {
  try {
    return subdirs(root)
      .filter(hasManifest)
      .map(d => d.slice(root.length + 1))
  } catch {
    return []
  }
}

function clone(url: string, tmp: string): void {
  try {
    execFileSync(
      'git',
      ['-c', 'protocol.ext.allow=never', 'clone', '--depth', '1', '--quiet', '--', url, tmp],
      { stdio: 'pipe' },
    )
  } catch (e) {
    const stderr = (e as { stderr?: Buffer }).stderr?.toString().trim()
    throw new Error(`git clone failed for ${url}: ${stderr || String(e)}`)
  }
}

export function resolveSource(arg: string, bundledRoot = defaultBundledRoot()): PluginSource {
  if (!URL_RE.test(arg)) {
    const dir = join(bundledRoot, arg)
    if (/^[\w.-]+$/.test(arg) && !arg.startsWith('.') && hasManifest(dir))
      return { dirs: [dir], cleanup: () => undefined }
    throw new Error(
      `unknown plugin "${arg}": not a bundled plugin nor a repo url (bundled: ${bundledNames(bundledRoot).join(', ') || 'none'})`,
    )
  }
  const tmp = mkdtempSync(join(tmpdir(), 'gilberto-plugin-'))
  const cleanup = (): void => rmSync(tmp, { recursive: true, force: true })
  try {
    clone(arg, tmp)
    const dirs = hasManifest(tmp) ? [tmp] : subdirs(tmp).filter(hasManifest)
    if (!dirs.length) throw new Error(`no plugin found in ${arg} (no ${MANIFEST_PATH})`)
    return { dirs, cleanup }
  } catch (e) {
    cleanup()
    throw e
  }
}
