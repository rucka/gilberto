import { execFileSync, spawnSync } from 'node:child_process'
import { readFileSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Command } from 'commander'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { createProgram, main, runCli } from './cli.js'
import { getLogLevel, setLogLevel } from './ui/logger.js'

const cliDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const pkg = JSON.parse(readFileSync(resolve(cliDir, 'package.json'), 'utf8')) as {
  version: string
  description: string
}

const argv = (...args: string[]) => ['node', 'gilberto', ...args]

let out: string
let err: string
let exit: MockInstance<typeof process.exit>

beforeEach(() => {
  out = ''
  err = ''
  setLogLevel('info')
  vi.spyOn(process.stdout, 'write').mockImplementation(s => ((out += String(s)), true))
  vi.spyOn(process.stderr, 'write').mockImplementation(s => ((err += String(s)), true))
  vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => {
    err += a.join(' ') + '\n'
  })
  exit = vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
})
afterEach(() => vi.restoreAllMocks())

const withCmd = (body: () => void = () => {}) => {
  const p = createProgram()
  p.command('noop').action(body)
  return p
}

describe('cli', () => {
  it('AC-1: --version prints package version, exit 0, stdout only', async () => {
    await main(argv('--version'))
    expect(out.trim()).toBe(pkg.version)
    expect(err).toBe('')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('AC-2: --help shows description and global options, exit 0', async () => {
    await main(argv('--help'))
    expect(out).toContain(pkg.description)
    for (const o of ['--log-level', '-v, --verbose', '--no-banner']) expect(out).toContain(o)
    expect(err).not.toContain('Error:')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('AC-3: --log-level debug accepted without subcommands', async () => {
    await expect(runCli(argv('--log-level', 'debug'))).resolves.toBeUndefined()
    await main(argv('--log-level', 'debug'))
    expect(err).toBe('')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('AC-3: pre-action hook applies log level; --verbose aliases debug', async () => {
    await runCli(argv('--log-level', 'warn', '--no-banner', 'noop'), withCmd())
    expect(getLogLevel()).toBe('warn')
    await runCli(argv('-v', '--no-banner', 'noop'), withCmd())
    expect(getLogLevel()).toBe('debug')
    await runCli(argv('--no-banner', 'noop'), withCmd())
    expect(getLogLevel()).toBe('info')
  })

  it('AC-4: banner on stderr before command body', async () => {
    let atBody = ''
    await runCli(
      argv('noop'),
      withCmd(() => (atBody = err)),
    )
    expect(err).toContain('gilberto')
    expect(atBody).toContain('gilberto')
    expect(out).toBe('')
  })

  it.each([['--no-banner'], ['--json']])('AC-5: %s suppresses banner', async flag => {
    await runCli(argv(flag, 'noop'), withCmd())
    expect(err).toBe('')
  })

  it('AC-7: help/version codes exit 0 silently; bare invocation exit 0', async () => {
    const p = withCmd()
    await main(argv(), p)
    expect(exit).toHaveBeenCalledWith(0)
    expect(err).not.toContain('Error:')
  })

  it('AC-8: unexpected error -> "Error: msg" and exit 1, no stack at info', async () => {
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {
        throw new Error('boom')
      }),
    )
    expect(err).toContain('Error: boom')
    expect(err).not.toContain('at ')
    expect(exit).toHaveBeenLastCalledWith(1)
  })

  it('AC-8: stack printed at debug level; non-Error values wrapped', async () => {
    await main(
      argv('--log-level', 'debug', '--no-banner', 'noop'),
      withCmd(() => {
        throw new Error('boom')
      }),
    )
    expect(err).toMatch(/Error: boom[\s\S]*at /)
    err = ''
    await main(
      argv('--no-banner', 'noop'),
      withCmd(() => {
        // eslint-disable-next-line no-throw-literal
        throw 'str'
      }),
    )
    expect(err).toContain('Error: str')
  })

  it('unknown flag: Commander error not re-wrapped, non-zero exit', async () => {
    await main(argv('--nope'))
    expect(err).toContain("error: unknown option '--nope'")
    expect(err).not.toContain('Error:')
    expect(exit).toHaveBeenCalledWith(1)
  })

  it('sorts subcommands in help', () => {
    const p = createProgram()
    p.command('zeta')
    p.command('alpha')
    expect(p).toBeInstanceOf(Command)
    expect(p.createHelp().sortSubcommands).toBe(true)
  })
})

describe('built binary', () => {
  const bin = resolve(cliDir, 'dist/cli.js')
  const run = (...a: string[]) => spawnSync(bin, a, { encoding: 'utf8' })

  it('AC-6: executes directly (shebang + 755)', () => {
    execFileSync('pnpm', ['run', 'build'], { cwd: cliDir, stdio: 'ignore' })
    expect(statSync(bin).mode & 0o777).toBe(0o755)
    const v = run('--version')
    expect(v.status).toBe(0)
    expect(v.stdout.trim()).toBe(pkg.version)
    const h = run('--help')
    expect(h.status).toBe(0)
    expect(h.stdout).toContain('--no-banner')
    expect(run().status).toBe(0)
    expect(run('--nope').status).not.toBe(0)
  }, 60_000)
})
