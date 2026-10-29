import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createProgram, main, runCli } from './cli.js'
import { getLogLevel, setLogLevel } from './ui/logger.js'

const argv = (...args: string[]) => ['node', 'gilberto', ...args]

beforeEach(() => {
  setLogLevel('info')
  vi.spyOn(console, 'error').mockImplementation(() => {})
})
afterEach(() => vi.restoreAllMocks())

describe('log level without sub-command', () => {
  it('r0-1 W1: --log-level debug is recorded', async () => {
    await runCli(argv('--log-level', 'debug'))
    expect(getLogLevel()).toBe('debug')
  })

  it('r0-1 W2: --verbose is recorded as debug', async () => {
    await runCli(argv('-v'))
    expect(getLogLevel()).toBe('debug')
  })

  it('r0-1 W3: --log-level wins over --verbose', async () => {
    await runCli(argv('-v', '--log-level', 'error'))
    expect(getLogLevel()).toBe('error')
  })

  it('r0-1 C1: no flags keeps info', async () => {
    await runCli(argv())
    expect(getLogLevel()).toBe('info')
  })

  it('r0-1 C2: --log-level warn with sub-command still recorded', async () => {
    const p = createProgram()
    p.command('noop').action(() => {})
    await runCli(argv('--log-level', 'warn', '--no-banner', 'noop'), p)
    expect(getLogLevel()).toBe('warn')
  })

  it('r0-1 W4: --log-level error then -v: log-level wins (reversed order)', async () => {
    await runCli(argv('--log-level', 'error', '-v'))
    expect(getLogLevel()).toBe('error')
  })
})

const withNoop = (body: () => void = () => {}) => {
  const p = createProgram()
  p.command('noop').action(body)
  return p
}

describe('log level with sub-command', () => {
  it('r0-1 C3: -v noop -> debug', async () => {
    await runCli(argv('-v', '--no-banner', 'noop'), withNoop())
    expect(getLogLevel()).toBe('debug')
  })

  it('r0-1 C4: --log-level error -v noop -> error', async () => {
    await runCli(argv('--log-level', 'error', '-v', '--no-banner', 'noop'), withNoop())
    expect(getLogLevel()).toBe('error')
  })

  it('r0-1 C5: -v --log-level error noop -> error', async () => {
    await runCli(argv('-v', '--log-level', 'error', '--no-banner', 'noop'), withNoop())
    expect(getLogLevel()).toBe('error')
  })

  it('r0-1 C6: noop --log-level debug (option after sub-command) -> debug', async () => {
    await runCli(argv('--no-banner', 'noop', '--log-level', 'debug'), withNoop())
    expect(getLogLevel()).toBe('debug')
  })

  it('r0-1 C7: noop -v (option after sub-command) -> debug', async () => {
    await runCli(argv('--no-banner', 'noop', '-v'), withNoop())
    expect(getLogLevel()).toBe('debug')
  })

  it('r0-1 C8: noop --log-level error -v (options after sub-command) -> error', async () => {
    await runCli(argv('--no-banner', 'noop', '--log-level', 'error', '-v'), withNoop())
    expect(getLogLevel()).toBe('error')
  })
})

describe('main() stack printing consumer', () => {
  const boom = () => {
    throw new Error('boom')
  }
  const stackOf = async (...flags: string[]) => {
    const lines: string[] = []
    vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
    vi.mocked(console.error).mockImplementation((...a: unknown[]) => {
      lines.push(a.join(' '))
    })
    await main(argv(...flags, '--no-banner', 'noop'), withNoop(boom))
    return lines.join('\n')
  }

  it('r0-1 consumer-main: --log-level debug prints the stack', async () => {
    expect(await stackOf('--log-level', 'debug')).toMatch(/Error: boom[\s\S]*\n\s+at /)
  })

  it('r0-1 consumer-main: -v prints the stack', async () => {
    expect(await stackOf('-v')).toMatch(/Error: boom[\s\S]*\n\s+at /)
  })

  it('r0-1 consumer-main: no flag prints no stack', async () => {
    const o = await stackOf()
    expect(o).toContain('Error: boom')
    expect(o).not.toMatch(/\n\s+at /)
  })
})
