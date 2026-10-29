import { createRequire } from 'node:module'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { WizardExit } from '../exit.js'
import { isTopicPillar } from '../state.js'
import { quote, type Bootstrap, type TempStep } from '../types.js'

const PACKAGE = '@foomakers/gilberto-vault-bootstrap'

export const loadBootstrap = async (): Promise<Bootstrap> => {
  try {
    const entry = createRequire(import.meta.url).resolve(PACKAGE)
    return (await import(pathToFileURL(entry).href)) as Bootstrap
  } catch (cause) {
    throw new WizardExit(70, `${PACKAGE} could not be resolved: ${(cause as Error).message}`)
  }
}

export const skeletonStep: TempStep = async (draft, ctx, { root, signal }) => {
  const { targetPath, topicSeeds } = draft
  if (targetPath === undefined || topicSeeds === undefined)
    throw new Error('skeleton step requires targetPath and topicSeeds')
  const bootstrap = await (ctx.loadBootstrap ?? loadBootstrap)()
  const date = (ctx.now ?? (() => new Date()))()

  const dir = async (rel: string): Promise<void> => {
    signal.throwIfAborted()
    await mkdir(join(root, rel), { recursive: true })
    ctx.trace(`wrote dir=${quote(rel)}`)
  }
  const file = async (rel: string, content: string): Promise<void> => {
    signal.throwIfAborted()
    await writeFile(join(root, rel), content)
    ctx.trace(`wrote file=${quote(rel)}`)
  }

  for (const pillar of bootstrap.PILLARS) {
    await dir(pillar)
    await file(`${pillar}/${pillar}.md`, bootstrap.renderPillarNote(pillar, date))
    if (isTopicPillar(pillar))
      for (const topic of topicSeeds[pillar]) {
        await dir(`${pillar}/${topic}`)
        await file(`${pillar}/${topic}/${topic}.md`, bootstrap.renderTopicNote(topic, date))
        if (pillar === 'pulse') await dir(`${pillar}/${topic}/history`)
      }
    if (pillar === 'network') {
      await dir('network/people')
      await dir('network/companies')
    }
  }
  await dir('_ingest')
  await file('_ingest/.gitkeep', '')
  await dir('anatomy')
  await dir('.claude')
  await dir('.claude/skills')
  const claudeMd = await readFile(join(bootstrap.getSeedRoot(), 'skeleton', 'CLAUDE.md'), 'utf8')
  await file('CLAUDE.md', claudeMd.replaceAll('{{VAULT_ROOT}}', targetPath))
}
