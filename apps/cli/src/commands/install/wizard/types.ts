import type { InstallCommandConfig } from '../parser.js'
import type { WizardPrompts } from './prompts.js'
import type { WizardState } from './state.js'

export type Bootstrap = typeof import('@foomakers/gilberto-vault-bootstrap')

export type SignalSource = {
  on: (event: 'SIGINT', handler: () => void) => unknown
  off: (event: 'SIGINT', handler: () => void) => unknown
}

export type WizardDraft = Partial<WizardState>

export type StepContext = {
  flags: InstallCommandConfig
  prompts: WizardPrompts
  cwd: string
  env: NodeJS.ProcessEnv
  trace: (line: string) => void
  print: (line: string) => void
  now?: () => Date
  loadBootstrap?: () => Promise<Bootstrap>
  signals?: SignalSource
  platform?: NodeJS.Platform
  run?: (cmd: string, args: string[]) => RunResult
}

export type RunResult = { status: number | null; stderr: string; error?: NodeJS.ErrnoException }

export type TempWork = { root: string; signal: AbortSignal }

export type TempStep = (draft: WizardDraft, ctx: StepContext, work: TempWork) => Promise<void>

export type WizardStep = (draft: WizardDraft, ctx: StepContext) => Promise<WizardDraft>

export const quote = (p: string): string => `"${p}"`
