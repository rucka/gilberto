import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { main } from '../../cli.js'
import type { CommandDeps } from '../types.js'
import { handleInstallCommand } from './handler.js'
import { baseFlags, listing, stubPrompts, tmpRoot } from './wizard/test-utils/index.js'
import { installMetadata } from './metadata.js'
import { WizardExit } from './wizard/exit.js'
import { inquirerPrompts } from './wizard/prompts.js'
import { DEFAULT_TOPIC_SEEDS } from './wizard/state.js'

const makeDeps = (cwd = '/nonexistent-cwd') => {
  const logs: string[] = []
  const deps: CommandDeps = {
    logger: {
      debug: m => logs.push(m),
      info: m => logs.push(m),
      warn: m => logs.push(m),
      error: m => logs.push(m),
    },
    cwd,
    env: { HOME: '/home/u' },
    write: () => undefined,
  }
  return { deps, logs }
}

describe('handler + wizard', () => {
  it('AC7: --verbose prints one structured line per decision, paths quoted', async () => {
    const root = await tmpRoot()
    const target = join(root, 'My Vault')
    const { deps, logs } = makeDeps()
    await handleInstallCommand(baseFlags({ target, verbose: true }), deps, stubPrompts().prompts)
    expect(logs.slice(0, 5)).toEqual([
      `step=path resolved="${target}"`,
      'step=overwrite decision=continue reason=missing',
      'step=topics pillar=pulse selected=health,body,finance',
      'step=topics pillar=intelligence selected=ai,product',
      `step=topics pillar=projects selected=${DEFAULT_TOPIC_SEEDS.projects.join(',')}`,
    ])
    await expect(logs.slice(5).join('\n').replaceAll(target, '<vault>') + '\n').toMatchFileSnapshot(
      '../../../test/__snapshots__/install-verbose-default.txt',
    )
  })

  it('T-1: --verbose emits step=skeleton between topics and hooks; help lists flags and 8 steps', async () => {
    const root = await tmpRoot()
    const { deps, logs } = makeDeps()
    await handleInstallCommand(
      baseFlags({ target: join(root, 'v'), verbose: true }),
      deps,
      stubPrompts().prompts,
    )
    const ids = logs.flatMap(l => /^step=(\w+)/.exec(l)?.[1] ?? [])
    expect(ids).toContain('skeleton')
    expect(ids.indexOf('skeleton')).toBeGreaterThan(ids.lastIndexOf('topics'))
    expect(ids.indexOf('plugins')).toBeGreaterThan(ids.lastIndexOf('topics'))
    expect(ids.indexOf('anatomy')).toBeGreaterThan(ids.indexOf('plugins'))
    const help = JSON.stringify(installMetadata)
    for (const f of [
      '--seed-topics',
      '--no-hooks',
      '--no-launchd',
      '--launchd-in-ci',
      '--non-interactive',
      '--verbose',
    ])
      expect(help).toContain(f)
    for (const n of [
      '1 target path',
      '2 overwrite',
      '3 topic',
      '4 vault skeleton',
      '5 plugins',
      '6 anatomy',
      '7 .claude hooks',
      '8 launchd',
    ])
      expect(help).toContain(n)
  })

  it('without --verbose prints nothing', async () => {
    const root = await tmpRoot()
    const { deps, logs } = makeDeps()
    await handleInstallCommand(baseFlags({ target: join(root, 'v') }), deps, stubPrompts().prompts)
    expect(logs).toEqual([])
  })

  it('AC3: existing vault rejects with exit 2 and leaves the tree untouched', async () => {
    const root = await tmpRoot()
    await mkdir(join(root, 'anatomy'))
    await writeFile(join(root, 'anatomy', 'anatomy.md'), '#')
    const before = await listing(root)
    const { deps } = makeDeps()
    const err = await handleInstallCommand(
      baseFlags({ target: root }),
      deps,
      stubPrompts().prompts,
    ).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(WizardExit)
    expect((err as WizardExit).code).toBe(2)
    expect(await listing(root)).toEqual(before)
  })

  it('AC8: ExitPromptError maps to exit 130 "aborted by user"', async () => {
    const { prompts } = stubPrompts()
    prompts.input = () => Promise.reject(Object.assign(new Error('x'), { name: 'ExitPromptError' }))
    const err = await handleInstallCommand(baseFlags(), makeDeps().deps, prompts).catch(
      (e: unknown) => e,
    )
    expect(err).toMatchObject({ code: 130, message: 'aborted by user' })
  })

  it('other errors propagate untouched', async () => {
    const { prompts } = stubPrompts()
    prompts.input = () => Promise.reject(new Error('boom'))
    await expect(handleInstallCommand(baseFlags(), makeDeps().deps, prompts)).rejects.toThrow(
      'boom',
    )
  })
})

describe('gilberto install via main()', () => {
  let err: string
  let exit: MockInstance<typeof process.exit>
  beforeEach(() => {
    err = ''
    vi.spyOn(console, 'error').mockImplementation((...a: unknown[]) => {
      err += a.join(' ') + '\n'
    })
    exit = vi.spyOn(process, 'exit').mockImplementation((() => undefined) as never)
  })
  afterEach(() => vi.restoreAllMocks())

  const run = (...args: string[]) => main(['node', 'gilberto', '--no-banner', 'install', ...args])

  it('--non-interactive with path completes with exit 0', async () => {
    const root = await tmpRoot()
    await run(join(root, 'v'), '--non-interactive', '--no-launchd')
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('--non-interactive without path exits 64', async () => {
    await run('--non-interactive')
    expect(exit).toHaveBeenCalledWith(64)
    expect(err).toContain('missing required input: path')
  })

  it('bad --seed-topics exits 64', async () => {
    await run('/tmp/x', '--seed-topics', 'me=x')
    expect(exit).toHaveBeenCalledWith(64)
    expect(err).toContain('unknown pillar "me"')
  })

  it('existing vault exits 2 with the update hint', async () => {
    const root = await tmpRoot()
    await mkdir(join(root, 'anatomy'))
    await writeFile(join(root, 'anatomy', 'anatomy.md'), '#')
    await run(root, '--non-interactive')
    expect(exit).toHaveBeenCalledWith(2)
    expect(err).toContain('gilberto update')
  })

  it('declining the overwrite prompt exits 0', async () => {
    const root = await tmpRoot()
    vi.spyOn(inquirerPrompts, 'confirm').mockResolvedValue(false)
    await run(root)
    expect(exit).toHaveBeenCalledWith(0)
  })

  it('Ctrl+C during a prompt: "aborted by user" on stderr, exit 130', async () => {
    vi.spyOn(inquirerPrompts, 'input').mockRejectedValue(
      Object.assign(new Error('User force closed the prompt'), { name: 'ExitPromptError' }),
    )
    await run()
    expect(exit).toHaveBeenCalledWith(130)
    expect(err).toContain('aborted by user')
  })

  it('--seed-topics + path run with no prompt and exit 0', async () => {
    const root = await tmpRoot()
    const input = vi.spyOn(inquirerPrompts, 'checkbox')
    await run(join(root, 'v'), '--seed-topics', 'pulse=health', '--no-launchd')
    expect(input).not.toHaveBeenCalled()
    expect(exit).toHaveBeenCalledWith(0)
  })
})
