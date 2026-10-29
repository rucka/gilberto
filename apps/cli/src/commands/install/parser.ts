import type { CommandOptions } from '../types.js'

export type InstallCommandConfig = {
  command: 'install'
  target?: string
  seedTopics: boolean
  hooks: boolean
  launchd: boolean
  verbose: boolean
}

export const parseInstallCommand = (
  options: CommandOptions,
  args: string[],
): InstallCommandConfig => ({
  command: 'install',
  ...(args[0] === undefined ? {} : { target: args[0] }),
  seedTopics: options['seedTopics'] === true,
  hooks: options['hooks'] !== false,
  launchd: options['launchd'] !== false,
  verbose: options['verbose'] === true,
})
