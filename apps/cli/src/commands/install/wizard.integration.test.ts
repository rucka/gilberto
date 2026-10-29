import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { main } from '../../cli.js'
import type { CommandDeps } from '../types.js'
import { handleInstallCommand } from './handler.js'
import { baseFlags, listing, stubPrompts, tmpRoot } from './wizard/test-utils/index.js'
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
    expect(logs).toEqual([
      `step=path resolved="${target}"`,
      'step=overwrite decision=continue reason=missing',
      'step=topics pillar=pulse selected=health,body,finance',
      'step=topics pillar=intelligence selected=ai,product',
      `step=topics pillar=projects selected=${DEFAULT_TOPIC_SEEDS.projects.join(',')}`,
    ])
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
    await run(join(root, 'v'), '--non-interactive')
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
    await run(join(root, 'v'), '--seed-topics', 'pulse=health')
    expect(input).not.toHaveBeenCalled()
    expect(exit).toHaveBeenCalledWith(0)
  })
})
