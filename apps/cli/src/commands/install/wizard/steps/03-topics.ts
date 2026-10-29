import { DEFAULT_TOPIC_SEEDS, TOPIC_PILLARS, type TopicSeeds } from '../state.js'
import type { WizardStep } from '../types.js'

export const topicsStep: WizardStep = async (draft, { flags, prompts, trace }) => {
  const overrides = flags.seedTopics
  const interactive = !flags.nonInteractive && Object.keys(overrides).length === 0
  const topicSeeds: TopicSeeds = { ...DEFAULT_TOPIC_SEEDS, ...overrides }
  for (const pillar of TOPIC_PILLARS) {
    if (interactive)
      topicSeeds[pillar] = await prompts.checkbox({
        message: `Topic seeds for ${pillar}`,
        choices: DEFAULT_TOPIC_SEEDS[pillar].map(value => ({ value, checked: true })),
      })
    trace(`step=topics pillar=${pillar} selected=${topicSeeds[pillar].join(',')}`)
  }
  return { ...draft, topicSeeds }
}
