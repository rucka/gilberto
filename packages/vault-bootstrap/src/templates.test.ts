import { describe, expect, it } from 'vitest'
import { parse } from 'yaml'
import { PILLARS, renderPillarNote, renderTopicNote } from './index.js'

const date = new Date('2026-10-29T10:00:00Z')
const fm = (s: string) => parse(/^---\n([\s\S]*?)\n---\n/.exec(s)![1]!) as Record<string, unknown>

describe('folder-note templates', () => {
  it.each(PILLARS)('%s note: frontmatter + heading, deterministic', pillar => {
    const out = renderPillarNote(pillar, date)
    expect(fm(out)).toEqual({
      type: `${pillar}-index`,
      topics: [],
      created: '2026-10-29',
      updated: '2026-10-29',
    })
    expect(out.endsWith(`\n# ${pillar}\n`)).toBe(true)
    expect(renderPillarNote(pillar, date)).toBe(out)
  })

  it('topic note: topic-index + topic heading', () => {
    const out = renderTopicNote('ai', date)
    expect(fm(out)).toMatchObject({ type: 'topic-index', topics: [] })
    expect(out.endsWith('\n# ai\n')).toBe(true)
  })
})
