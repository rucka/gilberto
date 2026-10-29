import type { CommandDeps } from '../types.js'
import type { UpdateCommandConfig } from './parser.js'

export const UPDATE_PLACEHOLDER_MESSAGE =
  'update not yet implemented — Initiative #5 EP Lifecycle (issue #25)'

export const handleUpdateCommand = async (
  _config: UpdateCommandConfig,
  _deps: CommandDeps,
): Promise<void> => {
  console.error(UPDATE_PLACEHOLDER_MESSAGE)
}
