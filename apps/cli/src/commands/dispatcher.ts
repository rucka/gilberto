import type { AnyCommandConfig } from './index.js'
import type { CommandDeps } from './types.js'
import { handleHelloCommand } from './_hello/index.js'

export const dispatchCommand = async (
  config: AnyCommandConfig,
  deps: CommandDeps,
): Promise<void> => {
  switch (config.command) {
    case '_hello':
      return handleHelloCommand(config, deps)
    default: {
      const unreachable: never = config.command
      throw new Error(`unknown command: ${String(unreachable)}`)
    }
  }
}
