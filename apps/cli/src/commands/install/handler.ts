import type { CommandDeps } from '../types.js'
import type { InstallCommandConfig } from './parser.js'

export const INSTALL_PLACEHOLDER_MESSAGE =
  'install not yet implemented — Initiative #1 EP Bootstrap process (issue #10)'

export const handleInstallCommand = async (
  _config: InstallCommandConfig,
  _deps: CommandDeps,
): Promise<void> => {
  console.error(INSTALL_PLACEHOLDER_MESSAGE)
}
