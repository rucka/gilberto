import { withOrigin } from '../helpers.js'
import type { CommandRegistryEntry } from '../types.js'
import { handlePluginCommand, pluginPlaceholderMessage } from './handler.js'
import { pluginMetadata } from './metadata.js'
import {
  parsePluginCommand,
  PLUGIN_ACTIONS,
  type PluginAction,
  type PluginCommandConfig,
} from './parser.js'

export const pluginCommand: CommandRegistryEntry<PluginCommandConfig> = withOrigin(
  import.meta.url,
  {
    name: 'plugin',
    metadata: pluginMetadata,
    parse: parsePluginCommand,
    handle: handlePluginCommand,
  },
)

export {
  handlePluginCommand,
  parsePluginCommand,
  PLUGIN_ACTIONS,
  pluginMetadata,
  pluginPlaceholderMessage,
}
export type { PluginAction, PluginCommandConfig }
