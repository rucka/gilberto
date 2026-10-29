import { withOrigin } from '../helpers.js'
import type { CommandRegistryEntry } from '../types.js'
import { handleUpdateCommand, UPDATE_PLACEHOLDER_MESSAGE } from './handler.js'
import { updateMetadata } from './metadata.js'
import { parseUpdateCommand, type UpdateCommandConfig } from './parser.js'

export const updateCommand: CommandRegistryEntry<UpdateCommandConfig> = withOrigin(
  import.meta.url,
  {
    name: 'update',
    metadata: updateMetadata,
    parse: parseUpdateCommand,
    handle: handleUpdateCommand,
  },
)

export { handleUpdateCommand, parseUpdateCommand, UPDATE_PLACEHOLDER_MESSAGE, updateMetadata }
export type { UpdateCommandConfig }
