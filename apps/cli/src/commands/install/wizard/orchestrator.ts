import { WizardStateSchema, type WizardState } from './state.js'
import { pathStep } from './steps/01-path.js'
import { overwriteStep } from './steps/02-overwrite.js'
import { topicsStep } from './steps/03-topics.js'
import type { StepContext, WizardDraft, WizardStep } from './types.js'

const STEPS: readonly WizardStep[] = [pathStep, overwriteStep, topicsStep]

export const runWizard = async (ctx: StepContext): Promise<WizardState> => {
  let draft: WizardDraft = {}
  for (const step of STEPS) draft = await step(draft, ctx)
  return WizardStateSchema.parse(draft)
}
