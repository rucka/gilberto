import { Command } from 'commander'
import { describe, expect, it, vi } from 'vitest'
import { createProgram, runCli } from '../cli.js'
import { helloCommand, parseHelloCommand } from './_hello/index.js'
import {
  addCommandOptions,
  commandRegistry,
  dispatchCommand,
  normalizeOptionKeys,
  onlyStrings,
  registerCommandFromMetadata,
  type AnyCommandConfig,
  type CommandDeps,
} from './index.js'

const mkDeps = (): CommandDeps & { out: string[] } => {
  const out: string[] = []
  const noop = (): void => undefined
  return {
    out,
    logger: { debug: noop, info: noop, warn: noop, error: noop },
    cwd: '/tmp',
    env: {},
    write: t => void out.push(t),
  }
}

describe('registry shape (AC-7)', () => {
  it('each entry exposes name, parse, handle, metadata', () => {
    for (const e of commandRegistry)
      expect(Object.keys(e).sort()).toEqual(['handle', 'metadata', 'name', 'parse'])
    expect(commandRegistry.map(e => e.name)).toContain('_hello')
  })
})

describe('dispatchCommand (AC-6, AC-3)', () => {
  it('routes by discriminator with injected deps', async () => {
    const deps = mkDeps()
    await dispatchCommand({ command: '_hello', name: 'Gianluca' }, deps)
    expect(deps.out).toEqual(['Hello, Gianluca!\n'])
  })

  it('rejects an unknown discriminator at runtime', async () => {
    await expect(dispatchCommand({ command: 'nope' } as never, mkDeps())).rejects.toThrow(
      /unknown command/,
    )
  })

  it('rejects wrong config shapes at compile time', () => {
    // @ts-expect-error name must be a string
    const bad: AnyCommandConfig = { command: '_hello', name: 1 }
    // @ts-expect-error handler only accepts its own union member
    void helloCommand.handle({ command: 'other', name: 'x' }, mkDeps())
    expect(bad).toBeDefined()
  })
})

describe('helpers (AC-4)', () => {
  it('normalizeOptionKeys camelCases kebab keys', () => {
    expect(normalizeOptionKeys({ 'log-level': 'debug', 'a-b-c': 1, plain: true })).toEqual({
      logLevel: 'debug',
      aBC: 1,
      plain: true,
    })
  })

  it('onlyStrings drops non-strings, handles empty', () => {
    expect(onlyStrings(['a', 1, true, 'b', undefined])).toEqual(['a', 'b'])
    expect(onlyStrings([])).toEqual([])
  })

  it('addCommandOptions is a no-op for empty options', () => {
    const cmd = new Command('x')
    addCommandOptions(cmd, [])
    expect(cmd.options).toHaveLength(0)
  })

  it('addCommandOptions registers optional and required options', () => {
    const cmd = new Command('x')
    addCommandOptions(cmd, [
      { flags: '--a <a>', description: 'a', required: true },
      { flags: '--b <b>', description: 'b', defaultValue: 'd' },
    ])
    expect(cmd.options.map(o => o.long)).toEqual(['--a', '--b'])
    expect(cmd.options[0]?.mandatory).toBe(true)
    expect(cmd.options[1]?.defaultValue).toBe('d')
  })
})

describe('registerCommandFromMetadata (AC-2)', () => {
  it('throws on duplicate name', () => {
    const program = new Command()
    const deps = mkDeps()
    registerCommandFromMetadata(program, helloCommand, deps, dispatchCommand)
    expect(() => registerCommandFromMetadata(program, helloCommand, deps, dispatchCommand)).toThrow(
      'command "_hello" already registered',
    )
  })

  it('registers a metadata-only command with no options or notes', async () => {
    const program = new Command().exitOverride()
    const handle = vi.fn(async () => undefined)
    const entry = {
      name: 'foo' as const,
      metadata: { name: 'foo', description: 'd', usage: '', options: [], examples: [], notes: [] },
      parse: (_o: Record<string, unknown>, args: string[]) => ({ command: 'foo' as const, args }),
      handle,
    }
    registerCommandFromMetadata(program, entry, mkDeps(), handle)
    await program.parseAsync(['node', 'x', 'foo', 'p1'])
    expect(handle).toHaveBeenCalledWith({ command: 'foo', args: ['p1'] }, expect.anything())
  })
})

describe('_hello (AC-1, AC-5)', () => {
  it('parser returns discriminated config and requires --name', () => {
    expect(parseHelloCommand({ name: 'X' }, [])).toEqual({ command: '_hello', name: 'X' })
    expect(() => parseHelloCommand({}, [])).toThrow('--name is required')
  })

  it('prints greeting end-to-end via the program', async () => {
    const write = vi.spyOn(process.stdout, 'write').mockImplementation(() => true)
    try {
      await runCli(
        ['node', 'gilberto', '--no-banner', '_hello', '--name', 'Gianluca'],
        createProgram(),
      )
      expect(write).toHaveBeenCalledWith('Hello, Gianluca!\n')
    } finally {
      write.mockRestore()
    }
  })

  it('--help prints metadata description, usage, examples, notes', () => {
    const program = createProgram()
    const hello = program.commands.find(c => c.name() === '_hello')
    const help = hello?.helpInformation() ?? ''
    expect(help).toContain('admin smoke command')
    expect(help).toContain('Usage:')
    expect(help).toContain('--name <name>')
    let after = ''
    hello?.configureOutput({ writeOut: s => (after += s) })
    hello?.outputHelp()
    expect(after).toContain('gilberto _hello --name Gianluca')
    expect(after).toContain('internal command: underscore prefix')
  })
})
