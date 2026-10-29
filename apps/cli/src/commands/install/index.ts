import { withOrigin } from '../helpers.js'
import type { CommandRegistryEntry } from '../types.js'
import { handleInstallCommand } from './handler.js'
import { installMetadata } from './metadata.js'
import { parseInstallCommand, type InstallCommandConfig } from './parser.js'

export const installCommand: CommandRegistryEntry<InstallCommandConfig> = withOrigin(
  import.meta.url,
  {
    name: 'install',
    metadata: installMetadata,
    parse: parseInstallCommand,
    handle: handleInstallCommand,
  },
)

export { handleInstallCommand, installMetadata, parseInstallCommand }
export type { InstallCommandConfig }
