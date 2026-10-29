import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  debug,
  error,
  getLogLevel,
  info,
  logger,
  resolveLogLevel,
  setLogLevel,
  warn,
} from './logger.js'

afterEach(() => {
  vi.restoreAllMocks()
  setLogLevel('info')
})

describe('logger', () => {
  it('writes to stderr, filtered by level', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    debug('d')
    info('i')
    warn('w')
    error('e')
    expect(spy.mock.calls.map(c => c[0])).toEqual(['i', 'w', 'e'])
    setLogLevel('debug')
    debug('d')
    expect(getLogLevel()).toBe('debug')
    expect(spy).toHaveBeenLastCalledWith('d')
    setLogLevel('error')
    warn('w2')
    expect(spy).toHaveBeenCalledTimes(4)
  })
})

describe('logger colours and streams', () => {
  it('AC-1: colours per level; nothing on stdout', async () => {
    const chalk = (await import('chalk')).default
    const prev = chalk.level
    chalk.level = 1
    setLogLevel('debug')
    const err = vi.spyOn(console, 'error').mockImplementation(() => {})
    const log = vi.spyOn(console, 'log').mockImplementation(() => {})
    const out = vi.spyOn(process.stdout, 'write').mockImplementation(() => true)
    logger.debug('d')
    logger.info('i')
    logger.warn('w')
    logger.error('e')
    chalk.level = prev
    expect(err.mock.calls.map(c => c[0])).toEqual([
      '\u001b[90md\u001b[39m',
      '\u001b[34mi\u001b[39m',
      '\u001b[33mw\u001b[39m',
      '\u001b[31me\u001b[39m',
    ])
    expect(log).not.toHaveBeenCalled()
    expect(out).not.toHaveBeenCalled()
  })

  it('no ANSI when colours are off', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    logger.info('plain')
    expect(console.error).toHaveBeenCalledWith('plain')
  })
})

describe('resolveLogLevel', () => {
  it('AC-4: flag > env > default', () => {
    expect(resolveLogLevel('warn', { GILBERTO_LOG_LEVEL: 'debug' })).toBe('warn')
    expect(resolveLogLevel(undefined, { GILBERTO_LOG_LEVEL: 'debug' })).toBe('debug')
    expect(resolveLogLevel(undefined, {})).toBe('info')
  })

  it('invalid env -> info + single warn line', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(resolveLogLevel(undefined, { GILBERTO_LOG_LEVEL: 'loud' })).toBe('info')
    expect(spy.mock.calls).toEqual([["ignored invalid GILBERTO_LOG_LEVEL='loud'"]])
  })

  it('invalid env: warn can be silenced; empty env is ignored', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    resolveLogLevel(undefined, { GILBERTO_LOG_LEVEL: 'loud' }, false)
    resolveLogLevel(undefined, { GILBERTO_LOG_LEVEL: '' })
    expect(spy).not.toHaveBeenCalled()
  })
})
