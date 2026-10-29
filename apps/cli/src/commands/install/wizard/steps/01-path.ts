import { constants } from 'node:fs'
import { access, stat } from 'node:fs/promises'
import { homedir } from 'node:os'
import { resolve } from 'node:path'
import { WizardExit } from '../exit.js'
import { quote, type WizardStep } from '../types.js'

export const DEFAULT_TARGET_PATH = '~/Dropbox/Gilberto/'

export const expandHome = (input: string, env: NodeJS.ProcessEnv): string => {
  const home = env['HOME'] ?? homedir()
  if (input === '~' || input.startsWith('~/')) return home + input.slice(1)
  if (input === '$HOME' || input.startsWith('$HOME/')) return home + input.slice(5)
  return input
}

const statOrUndefined = async (p: string) =>
  stat(p).catch((e: NodeJS.ErrnoException) => {
    if (e.code === 'ENOENT') return undefined
    throw e
  })

export const pathStep: WizardStep = async (draft, { flags, prompts, cwd, env, trace }) => {
  const raw =
    flags.target ??
    (flags.nonInteractive
      ? undefined
      : await prompts.input({
          message: 'Where should the vault be installed?',
          default: DEFAULT_TARGET_PATH,
        }))
  if (!raw?.trim()) throw new WizardExit(64, 'missing required input: path')
  const targetPath = resolve(cwd, expandHome(raw.trim(), env))
  const info = await statOrUndefined(targetPath)
  if (info && !info.isDirectory())
    throw new WizardExit(1, `target path is a file, not a directory: ${quote(targetPath)}`)
  if (info) {
    try {
      await access(targetPath, constants.W_OK)
    } catch {
      throw new WizardExit(13, `target path is not writable: ${quote(targetPath)}`)
    }
  }
  trace(`step=path resolved=${quote(targetPath)}`)
  return { ...draft, targetPath }
}
