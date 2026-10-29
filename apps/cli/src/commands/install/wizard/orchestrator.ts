import { WizardExit } from './exit.js'
import { WizardStateSchema, type WizardState } from './state.js'
import { pathStep } from './steps/01-path.js'
import { overwriteStep } from './steps/02-overwrite.js'
import { topicsStep } from './steps/03-topics.js'
import { skeletonStep } from './steps/04-skeleton.js'
import { createTempDir, toExit } from './temp.js'
import type { StepContext, TempStep, WizardDraft, WizardStep } from './types.js'

const STEPS: readonly WizardStep[] = [pathStep, overwriteStep, topicsStep]

const TEMP_STEPS: readonly TempStep[] = [skeletonStep]

const ABORTED = 'aborted by user, target path left untouched'

const materialize = async (draft: WizardDraft, ctx: StepContext): Promise<WizardDraft> => {
  const { targetPath } = draft
  if (targetPath === undefined) throw new Error('materialize requires targetPath')
  const signals = ctx.signals ?? process
  const abort = new AbortController()
  let committing = false
  let deferred = false
  const onSigint = (): void => {
    if (committing) deferred = true
    else abort.abort(new WizardExit(130, ABORTED))
  }
  signals.on('SIGINT', onSigint)
  const temp = await createTempDir({ tmp: ctx.env['TMPDIR'], home: ctx.env['HOME'] }).catch(
    (e: unknown) => {
      signals.off('SIGINT', onSigint)
      throw toExit(e, targetPath)
    },
  )
  try {
    for (const step of TEMP_STEPS) await step(draft, ctx, { root: temp.path, signal: abort.signal })
    abort.signal.throwIfAborted()
    committing = true
    await temp.commitTo(targetPath)
    signals.off('SIGINT', onSigint)
    if (deferred)
      throw new WizardExit(130, `aborted by user after the vault was written: "${targetPath}"`)
    return { ...draft, materialized: true }
  } catch (e) {
    throw toExit(e, targetPath)
  } finally {
    signals.off('SIGINT', onSigint)
    await temp.cleanup()
  }
}

export const runWizard = async (ctx: StepContext): Promise<WizardState> => {
  let draft: WizardDraft = {}
  for (const step of STEPS) draft = await step(draft, ctx)
  return WizardStateSchema.parse(await materialize(draft, ctx))
}
