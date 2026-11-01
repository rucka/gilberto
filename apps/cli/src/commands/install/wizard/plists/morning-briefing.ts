import { renderPlist, type PlistInput } from './render.js'

export const MORNING_BRIEFING_LABEL = 'com.foomakers.gilberto.morning-briefing'

export const renderMorningBriefing = ({ claude, root }: PlistInput): string =>
  renderPlist({
    label: MORNING_BRIEFING_LABEL,
    args: [claude, '-p', '/gilberto-process-surface morning-briefing'],
    workingDirectory: root,
    calendar: { hour: 7, minute: 0 },
  })
