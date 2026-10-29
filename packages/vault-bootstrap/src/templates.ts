import type { Pillar } from './index.js'

const isoDate = (d: Date): string => d.toISOString().slice(0, 10)

const note = (type: string, title: string, date: Date): string =>
  `---\ntype: ${type}\ntopics: []\ncreated: ${isoDate(date)}\nupdated: ${isoDate(date)}\n---\n\n# ${title}\n`

export const renderPillarNote = (pillar: Pillar, date: Date): string =>
  note(`${pillar}-index`, pillar, date)

export const renderTopicNote = (topic: string, date: Date): string =>
  note('topic-index', topic, date)
