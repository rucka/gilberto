import type { CommandDeps } from '../types.js'
import type { StatusCommandConfig } from './parser.js'

export const STATUS_PLACEHOLDER_MESSAGE =
  'status not yet implemented — Initiative #5 EP Lifecycle (issue #25)'

export const handleStatusCommand = async (
  _config: StatusCommandConfig,
  _deps: CommandDeps,
): Promise<void> => {
  console.error(STATUS_PLACEHOLDER_MESSAGE)
}
