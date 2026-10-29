import { afterEach, describe, expect, it, vi } from 'vitest'
import { debug, error, getLogLevel, info, setLogLevel, warn } from './logger.js'

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
