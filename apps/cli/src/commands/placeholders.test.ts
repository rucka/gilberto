import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { createProgram, main } from '../cli.js'
import {
  handleInstallCommand,
  INSTALL_PLACEHOLDER_MESSAGE,
  parseInstallCommand,
} from './install/index.js'
import {
  handlePluginCommand,
  parsePluginCommand,
  PLUGIN_ACTIONS,
  pluginPlaceholderMessage,
} from './plugin/index.js'
import {
  handleStatusCommand,
  parseStatusCommand,
  STATUS_PLACEHOLDER_MESSAGE,
} from './status/index.js'
import {
  handleUpdateCommand,
  parseUpdateCommand,
  UPDATE_PLACEHOLDER_MESSAGE,
} from './update/index.js'
import type { CommandDeps } from './types.js'

const noop = (): void => undefined
const deps: CommandDeps = {
  logger: { debug: noop, info: noop, warn: noop, error: noop },
  cwd: '/tmp',
  env: {},
  write: noop,
}

let out: string
let err: string
let exit: MockInstance<typeof process.exit>

beforeEach(() => {
  out = ''
  err = ''
  vi.spyOn(process.stdout, 'write').mockImplementation(s => ((out += String(s)), true))
  vi.spyOn(process.stderr, 'write').mockImplementation(s => ((err += String(s)), true))
  vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => {
    err += a.join(' ') + '\n'
  })
  exit = vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
})
afterEach(() => vi.restoreAllMocks())

const run = (...args: string[]) => main(['node', 'gilberto', '--no-banner', ...args])

const MESSAGES = {
  install: 'install not yet implemented — Initiative #1 EP Bootstrap process (issue #10)',
  update: 'update not yet implemented — Initiative #5 EP Lifecycle (issue #25)',
  status: 'status not yet implemented — Initiative #5 EP Lifecycle (issue #25)',
}

describe('AC-1: root help lists the four commands sorted', () => {
  it('install, plugin, status, update in order with descriptions', async () => {
    await run('--help')
    const names = ['install', 'plugin', 'status', 'update']
    const idx = names.map(n => out.indexOf(`\n  ${n}`))
    expect(idx.every(i => i >= 0)).toBe(true)
    expect([...idx].sort((a, b) => a - b)).toEqual(idx)
    expect(out).toContain('manage gilberto plugins')
    expect(exit).toHaveBeenCalledWith(0)
  })
})

describe('AC-2: install --help', () => {
  it('shows [target], options, examples', async () => {
    await run('install', '--help')
    for (const s of [
      '[target]',
      '--seed-topics',
      '--no-hooks',
      '--no-launchd',
      '-v, --verbose',
      'Examples:',
      'gilberto install ~/vault --seed-topics',
    ])
      expect(out).toContain(s)
    expect(out).not.toContain('--source')
    expect(out).not.toContain('--offline')
    expect(exit).toHaveBeenCalledWith(0)
  })
})

describe('AC-3/4/5: placeholder message on stderr, exit 0', () => {
  it.each([
    ['install', ['install', '/tmp/some-vault'], INSTALL_PLACEHOLDER_MESSAGE, MESSAGES.install],
    ['update', ['update'], UPDATE_PLACEHOLDER_MESSAGE, MESSAGES.update],
    ['status', ['status'], STATUS_PLACEHOLDER_MESSAGE, MESSAGES.status],
  ])('%s', async (_n, argv, constant, literal) => {
    await run(...argv)
    expect(constant).toBe(literal)
    expect(err).toContain(literal)
    expect(out).toBe('')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('install does not validate conflicting options and ignores unicode target', async () => {
    await run('install', '/tmp/véault', '--no-hooks', '--no-launchd', '-v')
    expect(err).toContain(MESSAGES.install)
    expect(exit).toHaveBeenCalledWith(0)
  })
})

describe('parsers', () => {
  it('install: target + flags, negated flags default true', () => {
    expect(parseInstallCommand({}, [])).toEqual({
      command: 'install',
      seedTopics: false,
      hooks: true,
      launchd: true,
      verbose: false,
    })
    expect(
      parseInstallCommand({ seedTopics: true, hooks: false, launchd: false, verbose: true }, [
        '/x',
      ]),
    ).toEqual({
      command: 'install',
      target: '/x',
      seedTopics: true,
      hooks: false,
      launchd: false,
      verbose: true,
    })
  })

  it('update: dryRun', () => {
    expect(parseUpdateCommand({}, [])).toEqual({ command: 'update', dryRun: false })
    expect(parseUpdateCommand({ dryRun: true }, [])).toEqual({ command: 'update', dryRun: true })
  })

  it('status: bare config', () => {
    expect(parseStatusCommand({}, [])).toEqual({ command: 'status' })
  })

  it('handlers resolve and emit only to stderr', async () => {
    await handleInstallCommand(parseInstallCommand({}, []), deps)
    await handleUpdateCommand(parseUpdateCommand({}, []), deps)
    await handleStatusCommand(parseStatusCommand({}, []), deps)
    expect(err).toBe(`${MESSAGES.install}\n${MESSAGES.update}\n${MESSAGES.status}\n`)
    expect(out).toBe('')
  })
})

describe('plugin', () => {
  it('AC-6: plugin --help lists six sorted sub-actions with descriptions', async () => {
    await run('plugin', '--help')
    const actions = ['disable', 'enable', 'install', 'list', 'remove', 'update']
    const idx = actions.map(a => out.indexOf(`\n  ${a}`))
    expect(idx.every(i => i >= 0)).toBe(true)
    expect([...idx].sort((a, b) => a - b)).toEqual(idx)
    for (const d of [
      'list installed plugins',
      'enable an installed plugin',
      'remove an installed plugin',
    ])
      expect(out).toContain(d)
    expect(exit).toHaveBeenCalledWith(0)
  })

  it.each(PLUGIN_ACTIONS)('AC-7: plugin %s prints canonical message, exit 0', async action => {
    await run('plugin', action)
    expect(err).toContain(
      `plugin ${action} not yet implemented — Initiative #3 EP Plugin protocol (issue #15)`,
    )
    expect(out).toBe('')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('AC-8: bare plugin prints help and exits 0', async () => {
    await run('plugin')
    expect(`${out}${err}`).toContain('Commands:')
    expect(`${out}${err}`).toContain('list')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('unknown sub-action: commander error, non-zero exit', async () => {
    await run('plugin', 'foo')
    expect(err).toContain("error: unknown command 'foo'")
    expect(exit).toHaveBeenCalledWith(1)
  })

  it('sub-action options are parsed even though the handler no-ops', async () => {
    const p = createProgram()
    await p.parseAsync(['node', 'gilberto', '--no-banner', 'plugin', 'install', 'src', '--force'])
    expect(err).toContain(pluginPlaceholderMessage('install'))
    expect(parsePluginCommand({ force: true }, ['install', 'src'])).toEqual({
      command: 'plugin',
      action: 'install',
      args: ['src'],
      force: true,
      dryRun: false,
      purge: false,
    })
    expect(parsePluginCommand({ dryRun: true }, ['update'])).toMatchObject({ dryRun: true })
    expect(parsePluginCommand({ purge: true }, ['remove', 'x'])).toMatchObject({ purge: true })
  })

  it('parser rejects missing/unknown action; handler rejects unreachable action', async () => {
    expect(() => parsePluginCommand({}, [])).toThrow(/unknown plugin action: \(none\)/)
    expect(() => parsePluginCommand({}, ['nope'])).toThrow(/unknown plugin action: nope/)
    await expect(handlePluginCommand({ action: 'nope' } as never, deps)).rejects.toThrow(
      /unknown plugin action: nope/,
    )
  })
})
