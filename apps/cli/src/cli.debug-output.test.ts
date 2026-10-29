import chalk from 'chalk'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createProgram, main } from './cli.js'
import { setLogLevel } from './ui/logger.js'

const GRAY = '\u001b[90m'
let err: string[]
let out: string
let level: typeof chalk.level

beforeEach(() => {
  err = []
  out = ''
  level = chalk.level
  chalk.level = 1
  setLogLevel('info')
  vi.stubEnv('GILBERTO_LOG_LEVEL', '')
  vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => void err.push(a.join(' ')))
  vi.spyOn(process.stdout, 'write').mockImplementation(s => ((out += String(s)), true))
  vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
})
afterEach(() => {
  chalk.level = level
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
})

const run = (...args: string[]) =>
  main(['node', 'gilberto', '--no-banner', ...args], createProgram())

describe('AC-1: debug lines on the real _hello path', () => {
  it.each([
    ['--log-level debug', ['--log-level', 'debug']],
    ['-v alias', ['-v']],
  ])('%s: >=1 gray debug line on stderr, stdout only the greeting', async (_n, flags) => {
    await run(...flags, '_hello', '--name', 'X')
    expect(err.length).toBeGreaterThanOrEqual(1)
    expect(err.every(l => l.startsWith(GRAY))).toBe(true)
    expect(out).toBe('Hello, X!\n')
  })

  it('GILBERTO_LOG_LEVEL=debug: >=1 gray debug line on stderr', async () => {
    vi.stubEnv('GILBERTO_LOG_LEVEL', 'debug')
    await run('_hello', '--name', 'X')
    expect(err.length).toBeGreaterThanOrEqual(1)
    expect(err.every(l => l.startsWith(GRAY))).toBe(true)
    expect(out).toBe('Hello, X!\n')
  })

  it.each(['info', 'warn', 'error'])('control: --log-level %s emits no debug line', async lv => {
    await run('--log-level', lv, '_hello', '--name', 'X')
    expect(err).toEqual([])
    expect(out).toBe('Hello, X!\n')
  })

  it.each(['info', 'warn', 'error'])(
    'precedence: --log-level %s beats GILBERTO_LOG_LEVEL=debug, no debug line',
    async lv => {
      vi.stubEnv('GILBERTO_LOG_LEVEL', 'debug')
      await run('--log-level', lv, '_hello', '--name', 'X')
      expect(err).toEqual([])
      expect(out).toBe('Hello, X!\n')
    },
  )
})
