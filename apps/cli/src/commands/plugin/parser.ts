import type { CommandOptions } from '../types.js'

export const PLUGIN_ACTIONS = ['list', 'enable', 'disable', 'install', 'update', 'remove'] as const

export type PluginAction = (typeof PLUGIN_ACTIONS)[number]

export type PluginCommandConfig = {
  command: 'plugin'
  action: PluginAction
  args: string[]
  force: boolean
  dryRun: boolean
  purge: boolean
}

const isAction = (v: string | undefined): v is PluginAction => PLUGIN_ACTIONS.some(a => a === v)

export const parsePluginCommand = (
  options: CommandOptions,
  args: string[],
): PluginCommandConfig => {
  const [action, ...rest] = args
  if (!isAction(action)) throw new Error(`unknown plugin action: ${action ?? '(none)'}`)
  return {
    command: 'plugin',
    action,
    args: rest,
    force: options['force'] === true,
    dryRun: options['dryRun'] === true,
    purge: options['purge'] === true,
  }
}
