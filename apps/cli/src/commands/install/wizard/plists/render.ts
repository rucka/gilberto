export type PlistSpec = {
  label: string
  args: readonly string[]
  workingDirectory: string
  calendar?: { hour: number; minute: number }
  watchPaths?: readonly string[]
}

export const escapeXml = (s: string): string =>
  s
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')

const str = (s: string, pad: string): string => `${pad}<string>${escapeXml(s)}</string>`

export const renderPlist = (spec: PlistSpec): string => {
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
    '<plist version="1.0">',
    '<dict>',
    '  <key>Label</key>',
    str(spec.label, '  '),
    '  <key>ProgramArguments</key>',
    '  <array>',
    ...spec.args.map(a => str(a, '    ')),
    '  </array>',
    '  <key>WorkingDirectory</key>',
    str(spec.workingDirectory, '  '),
    '  <key>EnvironmentVariables</key>',
    '  <dict>',
    '    <key>GILBERTO_ROOT</key>',
    str(spec.workingDirectory, '    '),
    '  </dict>',
    '  <key>RunAtLoad</key>',
    '  <false/>',
  ]
  if (spec.calendar)
    lines.push(
      '  <key>StartCalendarInterval</key>',
      '  <dict>',
      '    <key>Hour</key>',
      `    <integer>${spec.calendar.hour}</integer>`,
      '    <key>Minute</key>',
      `    <integer>${spec.calendar.minute}</integer>`,
      '  </dict>',
    )
  if (spec.watchPaths)
    lines.push(
      '  <key>WatchPaths</key>',
      '  <array>',
      ...spec.watchPaths.map(p => str(p, '    ')),
      '  </array>',
    )
  lines.push('</dict>', '</plist>', '')
  return lines.join('\n')
}

export type PlistInput = { claude: string; root: string }
