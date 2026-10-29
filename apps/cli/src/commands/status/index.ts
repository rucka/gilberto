import { withOrigin } from '../helpers.js'
import type { CommandRegistryEntry } from '../types.js'
import { handleStatusCommand, STATUS_PLACEHOLDER_MESSAGE } from './handler.js'
import { statusMetadata } from './metadata.js'
import { parseStatusCommand, type StatusCommandConfig } from './parser.js'

export const statusCommand: CommandRegistryEntry<StatusCommandConfig> = withOrigin(
  import.meta.url,
  {
    name: 'status',
    metadata: statusMetadata,
    parse: parseStatusCommand,
    handle: handleStatusCommand,
  },
)

export { handleStatusCommand, parseStatusCommand, STATUS_PLACEHOLDER_MESSAGE, statusMetadata }
export type { StatusCommandConfig }
