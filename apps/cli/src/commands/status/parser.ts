import type { CommandOptions } from '../types.js'

export type StatusCommandConfig = { command: 'status' }

export const parseStatusCommand = (
  _options: CommandOptions,
  _args: string[],
): StatusCommandConfig => ({
  command: 'status',
})
