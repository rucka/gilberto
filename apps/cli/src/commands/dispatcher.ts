import { commandRegistry, type AnyCommandConfig } from './index.js'
import type { CommandDeps, CommandRegistryEntry } from './types.js'

export const dispatchCommand = async (
  config: AnyCommandConfig,
  deps: CommandDeps,
): Promise<void> => {
  const entry = (commandRegistry as readonly CommandRegistryEntry<AnyCommandConfig>[]).find(
    e => e.name === config.command,
  )
  if (!entry) throw new Error(`unknown command: ${config.command}`)
  return entry.handle(config, deps)
}
