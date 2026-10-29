import type { CommandOptions } from '../types.js'
import { WizardExit } from './wizard/exit.js'
import { isTopicPillar, TOPIC_PILLARS, type TopicPillar } from './wizard/state.js'

export type SeedOverrides = Partial<Record<TopicPillar, string[]>>

export type InstallCommandConfig = {
  command: 'install'
  target?: string
  seedTopics: SeedOverrides
  nonInteractive: boolean
  hooks: boolean
  launchd: boolean
  verbose: boolean
}

const invalidSeeds = (reason: string, raw: string): WizardExit =>
  new WizardExit(
    64,
    `invalid --seed-topics: ${reason}; expected "pillar=a,b;pillar=c" with pillar in ${TOPIC_PILLARS.join('|')}; got "${raw}"`,
  )

export const parseSeedTopics = (raw: string): SeedOverrides => {
  const out: SeedOverrides = {}
  for (const entry of raw.split(';').filter(e => e.trim())) {
    const [pillar = '', list, ...extra] = entry.split('=').map(s => s.trim())
    if (!isTopicPillar(pillar)) throw invalidSeeds(`unknown pillar "${pillar}"`, raw)
    const topics = (list ?? '')
      .split(',')
      .map(t => t.trim())
      .filter(Boolean)
    if (extra.length || !topics.length) throw invalidSeeds(`malformed entry "${entry}"`, raw)
    out[pillar] = topics
  }
  return out
}

export const parseInstallCommand = (
  options: CommandOptions,
  args: string[],
): InstallCommandConfig => ({
  command: 'install',
  ...(args[0] === undefined ? {} : { target: args[0] }),
  seedTopics:
    typeof options['seedTopics'] === 'string' ? parseSeedTopics(options['seedTopics']) : {},
  nonInteractive: options['nonInteractive'] === true,
  hooks: options['hooks'] !== false,
  launchd: options['launchd'] !== false,
  verbose: options['verbose'] === true,
})
