import { readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { WizardExit } from '../exit.js'
import { quote, type WizardStep } from '../types.js'

const exists = (p: string): Promise<boolean> =>
  stat(p).then(
    () => true,
    () => false,
  )

export const hasVault = async (target: string): Promise<boolean> => {
  if (await exists(join(target, 'anatomy', 'anatomy.md'))) return true
  const skills = await readdir(join(target, '.claude', 'skills')).catch(() => [])
  return skills.some(name => name.startsWith('gilberto-'))
}

export const overwriteStep: WizardStep = async (draft, { flags, prompts, trace }) => {
  const { targetPath } = draft
  if (targetPath === undefined) throw new Error('overwrite step requires targetPath')
  if (!(await exists(targetPath))) {
    trace('step=overwrite decision=continue reason=missing')
    return draft
  }
  if (await hasVault(targetPath))
    throw new WizardExit(
      2,
      `vault already exists at ${quote(targetPath)}; use \`gilberto update\` (coming Initiative #5)`,
    )
  const info = await stat(targetPath)
  if (!info.isDirectory())
    throw new WizardExit(1, `target path is not a directory: ${quote(targetPath)}`)
  if ((await readdir(targetPath)).length > 0)
    throw new WizardExit(1, `target path is not empty: ${quote(targetPath)}`)
  if (flags.nonInteractive) {
    trace('step=overwrite decision=continue reason=non-interactive')
    return draft
  }
  const proceed = await prompts.confirm({
    message: 'Target path exists. Continue?',
    default: false,
  })
  trace(`step=overwrite decision=${proceed ? 'continue' : 'abort'}`)
  if (!proceed) throw new WizardExit(0, 'aborted: target path left untouched')
  return draft
}
