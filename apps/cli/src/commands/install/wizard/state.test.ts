import { describe, expect, it } from 'vitest'
import { DEFAULT_TOPIC_SEEDS, TOPIC_PILLARS, WizardStateSchema } from './state.js'

describe('WizardStateSchema', () => {
  it('accepts a complete state', () => {
    const s = { targetPath: '/t', topicSeeds: DEFAULT_TOPIC_SEEDS, materialized: false }
    expect(WizardStateSchema.parse(s)).toEqual(s)
  })

  it.each([
    ['empty path', { targetPath: '', topicSeeds: DEFAULT_TOPIC_SEEDS, materialized: true }],
    ['missing seeds', { targetPath: '/t', materialized: true }],
    ['missing materialized', { targetPath: '/t', topicSeeds: DEFAULT_TOPIC_SEEDS }],
    [
      'missing pillar',
      { targetPath: '/t', topicSeeds: { pulse: [], intelligence: [] }, materialized: true },
    ],
    [
      'non-string topic',
      {
        targetPath: '/t',
        topicSeeds: { ...DEFAULT_TOPIC_SEEDS, pulse: [1] },
        materialized: true,
      },
    ],
  ])('rejects %s', (_n, bad) => {
    expect(WizardStateSchema.safeParse(bad).success).toBe(false)
  })

  it('defaults cover only topic pillars', () => {
    expect(Object.keys(DEFAULT_TOPIC_SEEDS)).toEqual([...TOPIC_PILLARS])
    expect(TOPIC_PILLARS).not.toContain('me')
    for (const p of TOPIC_PILLARS) expect(DEFAULT_TOPIC_SEEDS[p].length).toBeGreaterThan(0)
  })
})
