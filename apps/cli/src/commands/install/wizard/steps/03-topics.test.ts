import { describe, expect, it } from 'vitest'
import { makeCtx } from '../test-utils/index.js'
import { DEFAULT_TOPIC_SEEDS } from '../state.js'
import { topicsStep } from './03-topics.js'

describe('step 3 topics', () => {
  it('AC5: one checkbox per topic pillar, defaults pre-checked, none for me/journey/network', async () => {
    const { ctx, calls, lines } = makeCtx()
    const out = await topicsStep({}, ctx)
    expect(calls).toEqual([
      'checkbox:Topic seeds for pulse',
      'checkbox:Topic seeds for intelligence',
      'checkbox:Topic seeds for projects',
    ])
    expect(out.topicSeeds).toEqual(DEFAULT_TOPIC_SEEDS)
    expect(lines).toContain('step=topics pillar=intelligence selected=ai,product')
  })

  it('AC5: toggled selection is recorded', async () => {
    const { ctx } = makeCtx({ script: { checkbox: { intelligence: ['ai'], pulse: [] } } })
    expect((await topicsStep({}, ctx)).topicSeeds).toEqual({
      ...DEFAULT_TOPIC_SEEDS,
      intelligence: ['ai'],
      pulse: [],
    })
  })

  it('AC6: --seed-topics replaces named pillars, keeps defaults for the rest, no prompt', async () => {
    const { ctx, calls } = makeCtx({
      flags: { seedTopics: { intelligence: ['x', 'y'], pulse: ['health'] } },
    })
    expect((await topicsStep({}, ctx)).topicSeeds).toEqual({
      pulse: ['health'],
      intelligence: ['x', 'y'],
      projects: DEFAULT_TOPIC_SEEDS.projects,
    })
    expect(calls).toEqual([])
  })

  it('--non-interactive keeps defaults, no prompt', async () => {
    const { ctx, calls } = makeCtx({ flags: { nonInteractive: true } })
    expect((await topicsStep({}, ctx)).topicSeeds).toEqual(DEFAULT_TOPIC_SEEDS)
    expect(calls).toEqual([])
  })

  it('does not mutate DEFAULT_TOPIC_SEEDS', async () => {
    const snap = structuredClone(DEFAULT_TOPIC_SEEDS)
    await topicsStep({}, makeCtx({ script: { checkbox: { pulse: [] } } }).ctx)
    expect(DEFAULT_TOPIC_SEEDS).toEqual(snap)
  })
})
