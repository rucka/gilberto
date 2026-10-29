import type { InstallCommandConfig } from '../parser.js'
import type { WizardPrompts } from './prompts.js'
import type { WizardState } from './state.js'

export type WizardDraft = Partial<WizardState>

export type StepContext = {
  flags: InstallCommandConfig
  prompts: WizardPrompts
  cwd: string
  env: NodeJS.ProcessEnv
  trace: (line: string) => void
}

export type WizardStep = (draft: WizardDraft, ctx: StepContext) => Promise<WizardDraft>

export const quote = (p: string): string => `"${p}"`
