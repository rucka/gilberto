import type { CommandDeps } from '../types.js'
import type { PluginAction, PluginCommandConfig } from './parser.js'

export const pluginPlaceholderMessage = (action: PluginAction): string =>
  `plugin ${action} not yet implemented — Initiative #3 EP Plugin protocol (issue #15)`

export const handlePluginCommand = async (
  config: PluginCommandConfig,
  _deps: CommandDeps,
): Promise<void> => {
  switch (config.action) {
    case 'list':
    case 'enable':
    case 'disable':
    case 'install':
    case 'update':
    case 'remove':
      console.error(pluginPlaceholderMessage(config.action))
      return
    default: {
      const unreachable: never = config.action
      throw new Error(`unknown plugin action: ${String(unreachable)}`)
    }
  }
}
