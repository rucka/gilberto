import { cp, lstat, mkdir, realpath, rename, rm } from 'node:fs/promises'
import { homedir, tmpdir } from 'node:os'
import { dirname, join, relative, isAbsolute } from 'node:path'
import { WizardExit } from './exit.js'
import { quote } from './types.js'

export type TempDirOptions = {
  tmp?: string | undefined
  pid?: number | undefined
  home?: string | undefined
}

export type TempDir = {
  path: string
  commitTo: (target: string) => Promise<void>
  cleanup: () => Promise<void>
}

const code = (e: unknown): string | undefined => (e as NodeJS.ErrnoException).code

export const toExit = (err: unknown, target: string): unknown => {
  if (err instanceof WizardExit) return err
  switch (code(err)) {
    case 'EACCES':
    case 'EPERM':
      return new WizardExit(13, `target became unwritable: ${target}`)
    case 'ENOSPC':
      return new WizardExit(28, `disk full while writing vault for: ${target}`)
    case 'ENOTEMPTY':
    case 'EEXIST':
      return new WizardExit(1, `target path is not empty: ${quote(target)}`)
    default:
      return err
  }
}

const isInside = (child: string, parent: string): boolean => {
  const rel = relative(parent, child)
  return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))
}

const resolveDest = async (target: string, home: string): Promise<string> => {
  const info = await lstat(target).catch((e: unknown) => {
    if (code(e) === 'ENOENT') return undefined
    throw e
  })
  if (!info?.isSymbolicLink()) return target
  const real = await realpath(target).catch(() => undefined)
  if (real === undefined || !isInside(real, await realpath(home).catch(() => home)))
    throw new WizardExit(
      1,
      `refusing to overwrite symlink ${quote(target)} resolving outside home: ${quote(real ?? 'unresolvable')}`,
    )
  return real
}

export const createTempDir = async (opts: TempDirOptions = {}): Promise<TempDir> => {
  const pid = opts.pid ?? process.pid
  const path = join(opts.tmp ?? tmpdir(), `gilberto-install-${pid}`)
  const home = opts.home ?? homedir()
  const cleanup = (): Promise<void> => rm(path, { recursive: true, force: true })
  await cleanup()
  await mkdir(path, { recursive: true })

  const commitTo = async (target: string): Promise<void> => {
    await mkdir(dirname(target), { recursive: true })
    const dest = await resolveDest(target, home)
    try {
      await rename(path, dest)
    } catch (e) {
      if (code(e) !== 'EXDEV') throw e
      const staging = join(dirname(dest), `.gilberto-install-${pid}`)
      try {
        await cp(path, staging, { recursive: true })
        await rename(staging, dest)
      } catch (inner) {
        await rm(staging, { recursive: true, force: true })
        throw inner
      }
    }
  }

  return { path, commitTo, cleanup }
}
