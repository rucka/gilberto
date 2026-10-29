import { chmod, mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { WizardExit } from '../exit.js'
import { listing, makeCtx, tmpRoot } from '../test-utils/index.js'
import { DEFAULT_TARGET_PATH, expandHome, pathStep } from './01-path.js'

const exitOf = async (p: Promise<unknown>) => {
  try {
    await p
  } catch (e) {
    return e as WizardExit
  }
  throw new Error('expected WizardExit')
}

describe('step 1 path', () => {
  it('AC1: prompts with the Dropbox default', async () => {
    const { ctx, calls } = makeCtx({ env: { HOME: '/home/u' } })
    const out = await pathStep({}, ctx)
    expect(calls).toEqual(['input:Where should the vault be installed?'])
    expect(DEFAULT_TARGET_PATH).toBe('~/Dropbox/Gilberto/')
    expect(out.targetPath).toBe('/home/u/Dropbox/Gilberto')
  })

  it('AC2: positional target skips the prompt, relative resolves from cwd', async () => {
    const { ctx, calls, lines } = makeCtx({ flags: { target: 'v/' }, cwd: '/work' })
    expect((await pathStep({}, ctx)).targetPath).toBe('/work/v')
    expect(calls).toEqual([])
    expect(lines).toEqual(['step=path resolved="/work/v"'])
  })

  it('AC9: spaces and unicode kept verbatim and quoted', async () => {
    const root = await tmpRoot()
    const dir = join(root, 'My Vaults', 'Gilberto è v1')
    await mkdir(dir, { recursive: true })
    const { ctx, lines } = makeCtx({ flags: { target: `${dir}/` } })
    expect((await pathStep({}, ctx)).targetPath).toBe(dir)
    expect(lines).toEqual([`step=path resolved="${dir}"`])
  })

  it('expands ~ and $HOME', () => {
    const env = { HOME: '/h' }
    expect(expandHome('~', env)).toBe('/h')
    expect(expandHome('~/a', env)).toBe('/h/a')
    expect(expandHome('$HOME/a', env)).toBe('/h/a')
    expect(expandHome('~x/a', env)).toBe('~x/a')
  })

  it('existing file → exit 1', async () => {
    const root = await tmpRoot()
    const f = join(root, 'f.txt')
    await writeFile(f, 'x')
    const { ctx } = makeCtx({ flags: { target: f } })
    const e = await exitOf(pathStep({}, ctx))
    expect(e.code).toBe(1)
    expect(e.message).toBe(`target path is a file, not a directory: "${f}"`)
  })

  it.skipIf(process.getuid?.() === 0)('non-writable dir → exit 13', async () => {
    const root = await tmpRoot()
    const d = join(root, 'ro')
    await mkdir(d, { mode: 0o500 })
    await chmod(d, 0o500)
    const { ctx } = makeCtx({ flags: { target: d } })
    const e = await exitOf(pathStep({}, ctx))
    expect(e.code).toBe(13)
    expect(e.message).toBe(`target path is not writable: "${d}"`)
    await chmod(d, 0o700)
  })

  it('non-interactive without path → exit 64, no prompt', async () => {
    const { ctx, calls } = makeCtx({ flags: { nonInteractive: true } })
    const e = await exitOf(pathStep({}, ctx))
    expect(e.code).toBe(64)
    expect(e.message).toBe('missing required input: path')
    expect(calls).toEqual([])
  })

  it('does not mutate the filesystem', async () => {
    const root = await tmpRoot()
    await mkdir(join(root, 'a'))
    const before = await listing(root)
    const { ctx } = makeCtx({ flags: { target: join(root, 'a') } })
    await pathStep({}, ctx)
    expect(await listing(root)).toEqual(before)
  })
})
