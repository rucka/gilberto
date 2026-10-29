import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { createProgram, main } from './cli.js'
import { getLogLevel, setLogLevel } from './ui/logger.js'

const argv = (...args: string[]) => ['node', 'gilberto', ...args]
let err: string
let out: string
let exit: MockInstance<typeof process.exit>

beforeEach(() => {
  err = out = ''
  setLogLevel('info')
  vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => {
    err += a.join(' ') + '\n'
  })
  vi.spyOn(process.stderr, 'write').mockImplementation(s => ((err += String(s)), true))
  vi.spyOn(process.stdout, 'write').mockImplementation(s => ((out += String(s)), true))
  exit = vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
})

const withCmd = (body: () => void) => {
  const p = createProgram()
  p.command('noop').action(body)
  return p
}

describe('env var level resolution', () => {
  it('AC-4: env honoured without flag', async () => {
    vi.stubEnv('GILBERTO_LOG_LEVEL', 'debug')
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {}),
    )
    expect(getLogLevel()).toBe('debug')
  })

  it('AC-4: flag overrides env', async () => {
    vi.stubEnv('GILBERTO_LOG_LEVEL', 'debug')
    await main(
      argv('--log-level', 'info', '--no-banner', 'noop'),
      withCmd(() => {}),
    )
    expect(getLogLevel()).toBe('info')
  })

  it('invalid env: info + one warn line', async () => {
    vi.stubEnv('GILBERTO_LOG_LEVEL', 'loud')
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {}),
    )
    expect(getLogLevel()).toBe('info')
    expect(err.match(/ignored invalid GILBERTO_LOG_LEVEL='loud'/g)).toHaveLength(1)
  })

  it('AC-3: default info', async () => {
    vi.stubEnv('GILBERTO_LOG_LEVEL', '')
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {}),
    )
    expect(getLogLevel()).toBe('info')
  })

  it('invalid --log-level rejected before handler, non-zero exit', async () => {
    const body = vi.fn()
    await main(argv('--log-level', 'loud', 'noop'), withCmd(body))
    expect(body).not.toHaveBeenCalled()
    expect(err).toContain('loud')
    expect(exit).toHaveBeenCalledWith(1)
  })
})

describe('error path', () => {
  it.each([
    ['null', null, 'Error: null'],
    ['undefined', undefined, 'Error: undefined'],
    ['object', { a: 1 }, 'Error: [object Object]'],
  ])('AC-5: non-Error throw (%s) -> single line, exit 1', async (_n, value, line) => {
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {
        throw value
      }),
    )
    expect(err).toBe(line + '\n')
    expect(exit).toHaveBeenLastCalledWith(1)
  })

  it('empty message -> Error: unknown', async () => {
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {
        throw new Error('')
      }),
    )
    expect(err).toBe('Error: unknown\n')
  })

  it('AC-6: debug adds stack after the Error line; stdout untouched', async () => {
    await main(
      argv('--log-level', 'debug', '--no-banner', 'noop'),
      withCmd(() => {
        throw new Error('boom')
      }),
    )
    expect(err.startsWith('Error: boom\n')).toBe(true)
    expect(err).toContain('    at ')
    expect(out).toBe('')
    expect(exit).toHaveBeenLastCalledWith(1)
  })

  it('AC-7: expected Commander exits are silent, exit 0', async () => {
    await main(argv('--help'))
    await main(argv('--version'))
    expect(err).not.toContain('Error:')
    expect(exit).toHaveBeenCalledWith(0)
    expect(exit).not.toHaveBeenCalledWith(1)
  })

  it('unhandledRejection routes through the same path', async () => {
    const before = process.listeners('unhandledRejection').length
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {}),
    )
    const handler = process.listeners('unhandledRejection').at(-1) as (r: unknown) => void
    expect(process.listeners('unhandledRejection').length).toBe(before + 1)
    handler('late')
    expect(err).toContain('Error: late')
    expect(exit).toHaveBeenLastCalledWith(1)
    process.removeListener('unhandledRejection', handler)
  })
})

describe('--json', () => {
  it('AC-8: banner suppressed, debug on stderr only', async () => {
    const p = createProgram()
    p.command('noop').action(() => {
      process.stdout.write('{"ok":true}')
    })
    await main(argv('--json', '--log-level', 'debug', 'noop'), p)
    expect(out).toBe('{"ok":true}')
    expect(err).not.toContain('gilberto')
  })
})
