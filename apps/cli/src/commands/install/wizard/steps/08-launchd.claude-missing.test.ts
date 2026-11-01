import { writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { makeCtx, tmpRoot } from '../test-utils/index.js'
import { launchdStep } from './08-launchd.js'

const MISSING = /claude.*(not found|missing|not resolved)|(not found|missing|not resolved).*claude/i

const run = async (path: string) => {
  const home = await tmpRoot()
  const vault = await tmpRoot()
  const h = makeCtx({ flags: { launchd: true }, env: { HOME: home, PATH: path } })
  h.ctx.platform = 'darwin'
  h.ctx.run = () => ({ status: 0, stderr: '' })
  const err = await launchdStep({ targetPath: vault }, h.ctx).then(
    () => '',
    (e: unknown) => (e as Error).message,
  )
  return `${h.out.join('\n')}\n${err}`
}

describe('step 8 launchd: claude binary resolution', () => {
  it('r0-4 witness: claude not on PATH → message names missing `claude`', async () => {
    expect(await run('')).toMatch(MISSING)
  })

  it('r0-4 control: claude on PATH → no missing-claude message', async () => {
    const bin = await tmpRoot()
    await writeFile(join(bin, 'claude'), '#!/bin/sh\n', { mode: 0o755 })
    expect(await run(bin)).not.toMatch(/claude/i)
  })
})
