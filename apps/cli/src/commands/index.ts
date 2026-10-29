import type { Command } from 'commander'
import * as logger from '../ui/logger.js'
import { helloCommand } from './_hello/index.js'
import { dispatchCommand } from './dispatcher.js'
import { registerCommandFromMetadata } from './helpers.js'
import type { CommandDeps } from './types.js'

export const commandRegistry = [helloCommand] as const

export type AnyCommandConfig = ReturnType<(typeof commandRegistry)[number]['parse']>

export { dispatchCommand }
export {
  addCommandOptions,
  normalizeOptionKeys,
  onlyStrings,
  registerCommandFromMetadata,
} from './helpers.js'
export type * from './types.js'

export const defaultDeps = (): CommandDeps => ({
  logger,
  cwd: process.cwd(),
  env: process.env,
  write: text => void process.stdout.write(text),
})

export const registerCommandsOnProgram = (
  program: Command,
  deps: CommandDeps = defaultDeps(),
): void => {
  for (const entry of commandRegistry)
    registerCommandFromMetadata(program, entry, deps, dispatchCommand)
}
