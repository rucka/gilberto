import { z } from 'zod'

export const TOPIC_PILLARS = ['pulse', 'intelligence', 'projects'] as const

export type TopicPillar = (typeof TOPIC_PILLARS)[number]

export const isTopicPillar = (v: unknown): v is TopicPillar =>
  TOPIC_PILLARS.includes(v as TopicPillar)

const topics = z.array(z.string().min(1))

export const WizardStateSchema = z.object({
  targetPath: z.string().min(1),
  topicSeeds: z.object({ pulse: topics, intelligence: topics, projects: topics }),
})

export type WizardState = z.infer<typeof WizardStateSchema>

export type TopicSeeds = WizardState['topicSeeds']

export const DEFAULT_TOPIC_SEEDS: TopicSeeds = {
  pulse: ['health', 'body', 'finance'],
  intelligence: ['ai', 'product'],
  projects: ['venture', 'editorial'],
}
