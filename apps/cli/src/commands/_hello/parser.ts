import type { CommandOptions } from '../types.js'

export type HelloCommandConfig = { command: '_hello'; name: string }

export const parseHelloCommand = (options: CommandOptions, _args: string[]): HelloCommandConfig => {
  if (typeof options['name'] !== 'string' || !options['name']) throw new Error('--name is required')
  return { command: '_hello', name: options['name'] }
}
