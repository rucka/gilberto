import { spawnSync } from 'node:child_process'
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { Command } from 'commander'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { helloCommand } from './_hello/index.js'
import { dispatchCommand } from './dispatcher.js'
import { registerCommandFromMetadata } from './helpers.js'
import type { CommandDeps } from './types.js'

const cliDir = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const tscBin = createRequire(import.meta.url).resolve('typescript/bin/tsc')

const FOO_FILES: Record<string, string> = {
  'metadata.ts': `import type { CommandMetadata } from '../types.js'
export const fooMetadata = {
  name: 'foo',
  description: 'fixture command',
  usage: '--bar <bar>',
  options: [{ flags: '--bar <bar>', description: 'bar', required: true }],
  examples: [],
  notes: [],
} as const satisfies CommandMetadata
`,
  'parser.ts': `import type { CommandOptions } from '../types.js'
export type FooCommandConfig = { command: 'foo'; bar: string }
export const parseFooCommand = (options: CommandOptions, _args: string[]): FooCommandConfig => ({
  command: 'foo',
  bar: String(options['bar']),
})
`,
  'handler.ts': `import type { CommandDeps } from '../types.js'
import type { FooCommandConfig } from './parser.js'
export const handleFooCommand = async (config: FooCommandConfig, deps: CommandDeps): Promise<void> => {
  deps.write(\`foo:\${config.bar}\\n\`)
}
`,
  'index.ts': `import type { CommandRegistryEntry } from '../types.js'
import { handleFooCommand } from './handler.js'
import { fooMetadata } from './metadata.js'
import { parseFooCommand, type FooCommandConfig } from './parser.js'
export const fooCommand: CommandRegistryEntry<FooCommandConfig> = {
  name: 'foo',
  metadata: fooMetadata,
  parse: parseFooCommand,
  handle: handleFooCommand,
}
`,
}

type Tsc = { status: number | null; output: string }
type Variant = 'pristine' | 'withDispatcherCase' | 'indexOnly' | 'duplicateDir'

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

const patchIndex = (dir: string): void => {
  const file = join(dir, 'src/commands/index.ts')
  const src = readFileSync(file, 'utf8')
  if (!src.includes('[\n  helloCommand,'))
    throw new Error('index.ts no longer lists helloCommand first')
  writeFileSync(
    file,
    `import { fooCommand } from './foo/index.js'\n${src.replace('[\n  helloCommand,', '[\n  helloCommand,\n  fooCommand,')}`,
  )
}

const patchDuplicateIndex = (dir: string): void => {
  const file = join(dir, 'src/commands/index.ts')
  const src = readFileSync(file, 'utf8')
  if (!src.includes('[\n  helloCommand,'))
    throw new Error('index.ts no longer lists helloCommand first')
  writeFileSync(
    file,
    `import { helloCommand as copiedCommand } from './foo/index.js'\n${src.replace('[\n  helloCommand,', '[\n  helloCommand,\n  copiedCommand,')}`,
  )
}

const patchDispatcherCase = (dir: string): void => {
  const file = join(dir, 'src/commands/dispatcher.ts')
  const src = readFileSync(file, 'utf8')
  if (!src.includes("case '_hello':")) return
  writeFileSync(
    file,
    `import { handleFooCommand } from './foo/handler.js'\n${src.replace(
      "case '_hello':",
      "case 'foo':\n      return handleFooCommand(config, deps)\n    case '_hello':",
    )}`,
  )
}

const buildVariant = (root: string, variant: Variant, emit: boolean): { dir: string } & Tsc => {
  const dir = join(root, variant)
  mkdirSync(join(dir, 'src'), { recursive: true })
  const skipTests = (p: string): boolean => !p.endsWith('.test.ts')
  cpSync(join(cliDir, 'src/commands'), join(dir, 'src/commands'), {
    recursive: true,
    filter: skipTests,
  })
  cpSync(join(cliDir, 'src/ui'), join(dir, 'src/ui'), { recursive: true, filter: skipTests })
  if (variant !== 'duplicateDir') mkdirSync(join(dir, 'src/commands/foo'), { recursive: true })
  if (variant === 'duplicateDir') {
    cpSync(join(cliDir, 'src/commands/_hello'), join(dir, 'src/commands/foo'), { recursive: true })
    patchDuplicateIndex(dir)
  } else if (variant !== 'pristine') {
    for (const [name, body] of Object.entries(FOO_FILES))
      writeFileSync(join(dir, 'src/commands/foo', name), body)
    patchIndex(dir)
  }
  if (variant === 'withDispatcherCase') patchDispatcherCase(dir)
  writeFileSync(
    join(dir, 'tsconfig.json'),
    JSON.stringify({
      extends: '@gilberto/ts-config/node.json',
      compilerOptions: { noEmit: !emit, skipLibCheck: true, outDir: 'out', rootDir: 'src' },
      include: ['src/**/*.ts'],
    }),
  )
  if (emit) {
    mkdirSync(join(dir, 'out'), { recursive: true })
    writeFileSync(join(dir, 'out/package.json'), '{"type":"module"}')
  }
  const r = spawnSync(process.execPath, [tscBin, '-p', join(dir, 'tsconfig.json')], {
    cwd: dir,
    encoding: 'utf8',
    timeout: 100_000,
  })
  return { dir, status: r.status, output: `${r.stdout}${r.stderr}` }
}

let root: string
let pristine: { dir: string } & Tsc
let withCase: { dir: string } & Tsc
let indexOnly: { dir: string } & Tsc
let duplicateDir: { dir: string } & Tsc

beforeAll(() => {
  mkdirSync(join(cliDir, '.tmp'), { recursive: true })
  root = mkdtempSync(join(cliDir, '.tmp', 'registry-contract-'))
  pristine = buildVariant(root, 'pristine', false)
  withCase = buildVariant(root, 'withDispatcherCase', false)
  indexOnly = buildVariant(root, 'indexOnly', true)
  duplicateDir = buildVariant(root, 'duplicateDir', true)
}, 280_000)

afterAll(() => rmSync(root, { recursive: true, force: true }))

const loadEmitted = async (
  variant: { dir: string } = indexOnly,
): Promise<typeof import('./index.js')> =>
  (await import(
    pathToFileURL(join(variant.dir, 'out/commands/index.js')).href
  )) as typeof import('./index.js')

describe('registry contract (r0-1, r0-2, r0-3)', () => {
  it('RC1: harness copy of the real commands tree type-checks (control)', () => {
    expect(pristine.output).toBe('')
    expect(pristine.status).toBe(0)
  })

  it('RW1: a second registry entry registers without TS2345 in registerCommandsOnProgram (r0-1)', () => {
    expect(withCase.output).not.toMatch(/TS2345/)
    expect(withCase.output).not.toContain('index.ts')
    expect(withCase.status).toBe(0)
  })

  it('RW2: a new command needs only commands/index.ts edit to type-check (r0-2)', () => {
    expect(indexOnly.output).not.toContain('dispatcher.ts')
    expect(indexOnly.output).toBe('')
    expect(indexOnly.status).toBe(0)
  })

  it('RW3: dispatchCommand routes {command:"foo"} to the foo handler with only index.ts edited (r0-2)', async () => {
    const { dispatchCommand: dispatch } = await loadEmitted()
    const deps = mkDeps()
    await dispatch({ command: 'foo', bar: 'x' } as never, deps)
    expect(deps.out).toEqual(['foo:x\n'])
  })

  it('RC2: both commands are registered on the program (control)', async () => {
    const { registerCommandsOnProgram } = await loadEmitted()
    const program = new Command().exitOverride()
    registerCommandsOnProgram(program, mkDeps())
    expect(program.commands.map(c => c.name()).sort()).toEqual([
      '_hello',
      'foo',
      'install',
      'plugin',
      'status',
      'update',
    ])
  })

  it('RW4: registered heterogeneous registry runs each command end to end (r0-1 x r0-2)', async () => {
    const { registerCommandsOnProgram } = await loadEmitted()
    const program = new Command().exitOverride()
    const deps = mkDeps()
    registerCommandsOnProgram(program, deps)
    await program.parseAsync(['node', 'x', '_hello', '--name', 'G'])
    await program.parseAsync(['node', 'x', 'foo', '--bar', 'b'])
    expect(deps.out).toEqual(['Hello, G!\n', 'foo:b\n'])
  })

  it('RC4: two distinct-named entries register without the duplicate error (r0-3, control)', () => {
    const program = new Command()
    const deps = mkDeps()
    const other = {
      ...helloCommand,
      name: 'other',
      metadata: { ...helloCommand.metadata, name: 'other' },
    }
    expect(() => {
      registerCommandFromMetadata(program, helloCommand, deps, dispatchCommand)
      registerCommandFromMetadata(program, other as never, deps, dispatchCommand)
    }).not.toThrow()
    expect(program.commands.map(c => c.name())).toEqual(['_hello', 'other'])
  })

  it('RW5: duplicate name from a copied commands/foo dir names both commands/_hello and commands/foo (r0-3)', async () => {
    expect(duplicateDir.status).toBe(0)
    const { registerCommandsOnProgram } = await loadEmitted(duplicateDir)
    let message = ''
    try {
      registerCommandsOnProgram(new Command(), mkDeps())
    } catch (e) {
      message = (e as Error).message
    }
    expect(message).toContain('"_hello"')
    expect(message).toContain('commands/_hello')
    expect(message).toContain('commands/foo')
  })
})
