import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { renderIngest } from './ingest.js'
import { renderMorningBriefing } from './morning-briefing.js'
import { renderPlist, escapeXml } from './render.js'
import { renderReflectDay } from './reflect-day.js'

const fx = (n: string): string =>
  readFileSync(
    fileURLToPath(new URL(`../../../../../test/__fixtures__/plists/${n}`, import.meta.url)),
    'utf8',
  )

const input = { claude: '/opt/bin/claude', root: '/Users/me/My Vault' }

describe('plist renderers', () => {
  it('morning-briefing matches fixture (07:00, no CLI binary)', () => {
    expect(renderMorningBriefing(input)).toBe(fx('morning-briefing.plist'))
  })
  it('reflect-day matches fixture (22:00)', () => {
    expect(renderReflectDay(input)).toBe(fx('reflect-day.plist'))
  })
  it('ingest matches fixture (WatchPaths, no calendar)', () => {
    expect(renderIngest(input)).toBe(fx('ingest.plist'))
  })
  it('escapes XML in every value; spaces preserved', () => {
    const out = renderPlist({ label: 'a&b', args: ['<x>', `"'`], workingDirectory: 'p q' })
    expect(out).toContain('<string>a&amp;b</string>')
    expect(out).toContain('<string>&lt;x&gt;</string>')
    expect(out).toContain('<string>&quot;&apos;</string>')
    expect(out).toContain('<string>p q</string>')
    expect(escapeXml('&<>"\'')).toBe('&amp;&lt;&gt;&quot;&apos;')
  })
  it('every job sets GILBERTO_ROOT to the vault path', () => {
    for (const out of [
      renderMorningBriefing(input),
      renderReflectDay(input),
      renderIngest(input),
    ]) {
      expect(out).toContain(
        '  <key>EnvironmentVariables</key>\n  <dict>\n    <key>GILBERTO_ROOT</key>\n    <string>/Users/me/My Vault</string>\n  </dict>',
      )
    }
  })
  it('RunAtLoad false, never gilberto CLI', () => {
    for (const out of [
      renderMorningBriefing(input),
      renderReflectDay(input),
      renderIngest(input),
    ]) {
      expect(out).toContain('<key>RunAtLoad</key>\n  <false/>')
      expect(out).not.toMatch(/<string>[^<]*\/gilberto<\/string>/)
    }
  })
})
