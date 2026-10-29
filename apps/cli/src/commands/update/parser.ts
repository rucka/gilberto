import type { CommandOptions } from '../types.js'

export type UpdateCommandConfig = { command: 'update'; dryRun: boolean }

export const parseUpdateCommand = (
  options: CommandOptions,
  _args: string[],
): UpdateCommandConfig => ({
  command: 'update',
  dryRun: options['dryRun'] === true,
})
