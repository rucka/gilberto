import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { marketplaceHas } from './marketplace.js'
import { write } from './testkit.js'

const home = (json?: string): NodeJS.ProcessEnv => {
  const h = mkdtempSync(join(tmpdir(), 'home-'))
  if (json !== undefined) write(h, '.claude/plugins/installed_plugins.json', json)
  return { HOME: h }
}

describe('marketplaceHas', () => {
  it('detects <name>@<marketplace> key', () => {
    const env = home('{"version":2,"plugins":{"pulse@mk":[{}]}}')
    expect(marketplaceHas('pulse', env)).toBe(true)
    expect(marketplaceHas('pul', env)).toBe(false)
  })
  it('absent / malformed / no HOME / odd shape -> false, never throws', () => {
    expect(marketplaceHas('pulse', home())).toBe(false)
    expect(marketplaceHas('pulse', home('{nope'))).toBe(false)
    expect(marketplaceHas('pulse', home('{"plugins":null}'))).toBe(false)
    expect(marketplaceHas('pulse', {})).toBe(false)
  })
})
