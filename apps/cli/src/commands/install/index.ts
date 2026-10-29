import { withOrigin } from '../helpers.js'
import type { CommandRegistryEntry } from '../types.js'
import { handleInstallCommand, INSTALL_PLACEHOLDER_MESSAGE } from './handler.js'
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

export { handleInstallCommand, INSTALL_PLACEHOLDER_MESSAGE, installMetadata, parseInstallCommand }
export type { InstallCommandConfig }
