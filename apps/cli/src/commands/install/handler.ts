import type { CommandDeps } from '../types.js'
import { WizardExit } from './wizard/exit.js'
import { runWizard } from './wizard/orchestrator.js'
import { inquirerPrompts, type WizardPrompts } from './wizard/prompts.js'
import type { InstallCommandConfig } from './parser.js'

export const handleInstallCommand = async (
  config: InstallCommandConfig,
  deps: CommandDeps,
  prompts: WizardPrompts = inquirerPrompts,
): Promise<void> => {
  try {
    await runWizard({
      flags: config,
      prompts,
      cwd: deps.cwd,
      env: deps.env,
      trace: line => {
        if (config.verbose) deps.logger.info(line)
      },
    })
  } catch (err) {
    if (err instanceof Error && err.name === 'ExitPromptError')
      throw new WizardExit(130, 'aborted by user')
    throw err
  }
}
