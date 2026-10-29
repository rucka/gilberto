import type { CommandDeps } from '../types.js'
import type { HelloCommandConfig } from './parser.js'

export const handleHelloCommand = async (
  config: HelloCommandConfig,
  deps: CommandDeps,
): Promise<void> => {
  deps.logger.debug(`_hello: greeting '${config.name}'`)
  deps.write(`Hello, ${config.name}!\n`)
}
