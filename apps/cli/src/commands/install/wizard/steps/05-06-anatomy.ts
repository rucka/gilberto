import { relative } from 'node:path'
import { printBundledPlugins, runAnatomySteps } from '../../anatomy-steps.js'
import { WizardExit } from '../exit.js'
import { quote, type TempStep } from '../types.js'
import { loadBootstrap } from './04-skeleton.js'

export const anatomyStep: TempStep = async (draft, ctx, { root, signal }) => {
  printBundledPlugins(t => ctx.print(t.trimEnd()))
  ctx.trace('step=plugins decision=listed')
  const errors: string[] = []
  const code = await runAnatomySteps({
    tmp: root,
    date: (ctx.now ?? (() => new Date()))().toISOString().slice(0, 10),
    topics: Object.values(draft.topicSeeds ?? {}).flat(),
    verbose: true,
    write: t => {
      const [, kind, path] = /^wrote (file|dir)=(.*)\n$/.exec(t) ?? []
      if (kind !== undefined && path !== undefined)
        ctx.trace(`wrote ${kind}=${quote(relative(root, path))}`)
    },
    error: t => errors.push(t.trimEnd()),
    loadSeedRoot: async () => (await (ctx.loadBootstrap ?? loadBootstrap)()).getSeedRoot(),
    signal,
  })
  if (code !== 0) throw new WizardExit(code, errors.join('\n'))
  ctx.trace('step=anatomy decision=seeded')
}
