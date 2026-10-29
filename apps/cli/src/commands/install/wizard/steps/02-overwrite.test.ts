import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { WizardExit } from '../exit.js'
import { listing, makeCtx, tmpRoot } from '../test-utils/index.js'
import { overwriteStep } from './02-overwrite.js'

const run = async (targetPath: string, over: Parameters<typeof makeCtx>[0] = {}) => {
  const h = makeCtx(over)
  const before = await listing(join(targetPath, '..'))
  let error: WizardExit | undefined
  try {
    await overwriteStep({ targetPath }, h.ctx)
  } catch (e) {
    error = e as WizardExit
  }
  expect(await listing(join(targetPath, '..'))).toEqual(before)
  return { ...h, error }
}

describe('step 2 overwrite', () => {
  it('missing path → continue, no prompt', async () => {
    const root = await tmpRoot()
    const { error, calls, lines } = await run(join(root, 'new'))
    expect(error).toBeUndefined()
    expect(calls).toEqual([])
    expect(lines).toEqual(['step=overwrite decision=continue reason=missing'])
  })

  it('AC3: anatomy/anatomy.md → exit 2 with update hint', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(join(v, 'anatomy'), { recursive: true })
    await writeFile(join(v, 'anatomy', 'anatomy.md'), '#')
    const { error, calls } = await run(v)
    expect(error?.code).toBe(2)
    expect(error?.message).toBe(
      `vault already exists at "${v}"; use \`gilberto update\` (coming Initiative #5)`,
    )
    expect(calls).toEqual([])
  })

  it('AC3: .claude/skills/gilberto-* → exit 2, even non-interactive', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(join(v, '.claude', 'skills', 'gilberto-x'), { recursive: true })
    expect((await run(v, { flags: { nonInteractive: true } })).error?.code).toBe(2)
  })

  it('other .claude/skills entries are not a vault', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(join(v, '.claude', 'skills', 'other'), { recursive: true })
    expect((await run(v, { script: { confirm: true } })).error).toBeUndefined()
  })

  it('AC4: empty dir, confirm Yes → continue', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(v)
    const { error, calls, lines } = await run(v, { script: { confirm: true } })
    expect(error).toBeUndefined()
    expect(calls).toEqual(['confirm:Target path exists. Continue?'])
    expect(lines).toEqual(['step=overwrite decision=continue'])
  })

  it('AC4: default answer is No → exit 0', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(v)
    await writeFile(join(v, 'unrelated.txt'), 'x')
    const { error } = await run(v)
    expect(error?.code).toBe(0)
  })

  it('non-interactive + existing non-vault → continue, logged', async () => {
    const root = await tmpRoot()
    const v = join(root, 'v')
    await mkdir(v)
    const { error, calls, lines } = await run(v, { flags: { nonInteractive: true } })
    expect(error).toBeUndefined()
    expect(calls).toEqual([])
    expect(lines).toEqual(['step=overwrite decision=continue reason=non-interactive'])
  })

  it('requires a path from step 1', async () => {
    await expect(overwriteStep({}, makeCtx().ctx)).rejects.toThrow('requires targetPath')
  })
})
