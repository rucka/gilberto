import { describe, expect, it } from 'vitest'
import { DEFAULT_TOPIC_SEEDS, TOPIC_PILLARS, WizardStateSchema } from './state.js'

describe('WizardStateSchema', () => {
  it('accepts a complete state', () => {
    const s = { targetPath: '/t', topicSeeds: DEFAULT_TOPIC_SEEDS }
    expect(WizardStateSchema.parse(s)).toEqual(s)
  })

  it.each([
    ['empty path', { targetPath: '', topicSeeds: DEFAULT_TOPIC_SEEDS }],
    ['missing seeds', { targetPath: '/t' }],
    ['missing pillar', { targetPath: '/t', topicSeeds: { pulse: [], intelligence: [] } }],
    ['non-string topic', { targetPath: '/t', topicSeeds: { ...DEFAULT_TOPIC_SEEDS, pulse: [1] } }],
  ])('rejects %s', (_n, bad) => {
    expect(WizardStateSchema.safeParse(bad).success).toBe(false)
  })

  it('defaults cover only topic pillars', () => {
    expect(Object.keys(DEFAULT_TOPIC_SEEDS)).toEqual([...TOPIC_PILLARS])
    expect(TOPIC_PILLARS).not.toContain('me')
    for (const p of TOPIC_PILLARS) expect(DEFAULT_TOPIC_SEEDS[p].length).toBeGreaterThan(0)
  })
})
