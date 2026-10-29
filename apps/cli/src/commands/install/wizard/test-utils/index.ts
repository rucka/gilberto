import { mkdtemp, readdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import type { InstallCommandConfig } from '../../parser.js'
import type { WizardPrompts } from '../prompts.js'
import type { StepContext } from '../types.js'

export const baseFlags = (over: Partial<InstallCommandConfig> = {}): InstallCommandConfig => ({
  command: 'install',
  seedTopics: {},
  nonInteractive: false,
  hooks: true,
  launchd: true,
  verbose: false,
  ...over,
})

export type PromptScript = {
  input?: string
  confirm?: boolean
  checkbox?: Partial<Record<string, string[]>>
}

export const stubPrompts = (script: PromptScript = {}) => {
  const calls: string[] = []
  const prompts: WizardPrompts = {
    input: async o => (calls.push(`input:${o.message}`), script.input ?? o.default ?? ''),
    confirm: async o => (calls.push(`confirm:${o.message}`), script.confirm ?? o.default ?? false),
    checkbox: async o => {
      calls.push(`checkbox:${o.message}`)
      const key = o.message.replace('Topic seeds for ', '')
      return script.checkbox?.[key] ?? o.choices.filter(c => c.checked).map(c => c.value)
    },
  }
  return { prompts, calls }
}

type CtxOverrides = Partial<Pick<StepContext, 'cwd' | 'env'>> & {
  script?: PromptScript
  flags?: Partial<InstallCommandConfig>
}

export const makeCtx = (over: CtxOverrides = {}) => {
  const { prompts, calls } = stubPrompts(over.script)
  const lines: string[] = []
  const ctx: StepContext = {
    flags: baseFlags(over.flags),
    prompts,
    cwd: '/nonexistent-cwd',
    env: { HOME: '/home/u' },
    trace: l => lines.push(l),
    ...(over.cwd === undefined ? {} : { cwd: over.cwd }),
    ...(over.env === undefined ? {} : { env: over.env }),
  }
  return { ctx, calls, lines }
}

export const tmpRoot = (): Promise<string> => mkdtemp(join(tmpdir(), 'gilberto-wizard-'))

export const listing = (dir: string): Promise<string[]> => readdir(dir, { recursive: true })
