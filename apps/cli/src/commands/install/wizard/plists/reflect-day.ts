import { renderPlist, type PlistInput } from './render.js'

export const REFLECT_DAY_LABEL = 'com.foomakers.gilberto.reflect-day'

export const renderReflectDay = ({ claude, root }: PlistInput): string =>
  renderPlist({
    label: REFLECT_DAY_LABEL,
    args: [claude, '-p', '/gilberto-process-reflect day'],
    workingDirectory: root,
    calendar: { hour: 22, minute: 0 },
  })
