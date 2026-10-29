import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createProgram } from '../../cli.js'
import { getLogLevel, setLogLevel } from '../../ui/logger.js'

beforeEach(() => setLogLevel('info'))
afterEach(() => {
  vi.restoreAllMocks()
  setLogLevel('info')
})

const levelAfter = async (...args: string[]) => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  await createProgram().parseAsync(['node', 'g', '--no-banner', ...args])
  return getLogLevel()
}

describe('install -v keeps the root log-level alias (r0-1)', () => {
  it('install -v sets debug', async () => {
    expect(await levelAfter('install', '-v')).toBe('debug')
  })

  it('-v before install sets debug', async () => {
    expect(await levelAfter('-v', 'install')).toBe('debug')
  })

  it('--log-level error wins over install -v', async () => {
    expect(await levelAfter('install', '-v', '--log-level', 'error')).toBe('error')
  })
})
