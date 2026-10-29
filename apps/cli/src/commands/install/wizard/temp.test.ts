import { chmod, mkdir, readFile, readdir, stat, symlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { describe, expect, it, vi } from 'vitest'
import { WizardExit } from './exit.js'
import { createTempDir, toExit } from './temp.js'
import { listing, tmpRoot } from './test-utils/index.js'

const exists = (p: string) =>
  stat(p).then(
    () => true,
    () => false,
  )

const make = async (over: { pid?: number; home?: string } = {}) => {
  const tmp = await tmpRoot()
  const t = await createTempDir({ tmp, pid: 4242, ...over })
  await writeFile(join(t.path, 'a.txt'), 'A')
  return { tmp, t }
}

describe('createTempDir', () => {
  it('AC1: creates <tmp>/gilberto-install-<pid>', async () => {
    const { tmp, t } = await make()
    expect(t.path).toBe(join(tmp, 'gilberto-install-4242'))
    expect((await stat(t.path)).isDirectory()).toBe(true)
  })

  it('wipes a stale dir left by a dead pid', async () => {
    const tmp = await tmpRoot()
    await mkdir(join(tmp, 'gilberto-install-1'))
    await writeFile(join(tmp, 'gilberto-install-1', 'old'), 'x')
    const t = await createTempDir({ tmp, pid: 1 })
    expect(await readdir(t.path)).toEqual([])
  })

  it('AC1: commitTo moves the dir atomically; temp path is gone', async () => {
    const { t } = await make()
    const target = join(await tmpRoot(), 'vault')
    await t.commitTo(target)
    expect(await readFile(join(target, 'a.txt'), 'utf8')).toBe('A')
    expect(await exists(t.path)).toBe(false)
  })

  it('AC5: creates missing parents, path with spaces', async () => {
    const { t } = await make()
    const target = join(await tmpRoot(), 'a b', 'c', 'my vault')
    await t.commitTo(target)
    expect(await exists(join(target, 'a.txt'))).toBe(true)
  })

  it('replaces an existing empty target dir', async () => {
    const { t } = await make()
    const target = join(await tmpRoot(), 'vault')
    await mkdir(target)
    await t.commitTo(target)
    expect(await exists(join(target, 'a.txt'))).toBe(true)
  })

  it('non-empty target → ENOTEMPTY, target unchanged, mapped to exit 1', async () => {
    const { t } = await make()
    const target = join(await tmpRoot(), 'vault')
    await mkdir(target)
    await writeFile(join(target, 'mine.txt'), 'm')
    const err = await t.commitTo(target).catch((e: unknown) => toExit(e, target))
    expect(err).toBeInstanceOf(WizardExit)
    expect((err as WizardExit).code).toBe(1)
    expect(await listing(target)).toEqual(['mine.txt'])
  })

  it.skipIf(process.getuid?.() === 0)('AC5: unwritable parent → EACCES → exit 13', async () => {
    const { t } = await make()
    const root = await tmpRoot()
    await chmod(root, 0o500)
    const target = join(root, 'x', 'vault')
    const err = await t.commitTo(target).catch((e: unknown) => toExit(e, target))
    await chmod(root, 0o700)
    expect((err as WizardExit).code).toBe(13)
    expect((err as WizardExit).message).toBe(`target became unwritable: ${target}`)
  })

  it('AC7: EXDEV falls back to copy into a sibling staging dir + rename', async () => {
    const { t } = await make()
    const target = join(await tmpRoot(), 'vault')
    const fs = await import('node:fs/promises')
    const real = fs.rename
    let first = true
    vi.resetModules()
    vi.doMock('node:fs/promises', async () => ({
      ...fs,
      rename: async (a: string, b: string) => {
        if (first) {
          first = false
          throw Object.assign(new Error('x'), { code: 'EXDEV' })
        }
        return real(a, b)
      },
    }))
    const mod = await import('./temp.js')
    const t2 = await mod.createTempDir({ tmp: await tmpRoot(), pid: 7 })
    await writeFile(join(t2.path, 'b.txt'), 'B')
    await t2.commitTo(target)
    vi.doUnmock('node:fs/promises')
    expect(await readFile(join(target, 'b.txt'), 'utf8')).toBe('B')
    expect(await readdir(join(target, '..'))).toEqual(['vault'])
    await t2.cleanup()
    expect(await exists(t2.path)).toBe(false)
    await t.cleanup()
  })

  it('symlink target inside home → follows realpath', async () => {
    const home = await tmpRoot()
    const { t } = await make({ home })
    await mkdir(join(home, 'real'))
    await symlink(join(home, 'real'), join(home, 'link'))
    await t.commitTo(join(home, 'link'))
    expect(await exists(join(home, 'real', 'a.txt'))).toBe(true)
  })

  it('symlink target outside home → exit 1, nothing moved', async () => {
    const home = await tmpRoot()
    const { t } = await make({ home })
    const outside = await tmpRoot()
    await symlink(outside, join(home, 'link'))
    const err = await t.commitTo(join(home, 'link')).catch((e: unknown) => e)
    expect((err as WizardExit).code).toBe(1)
    expect(await readdir(outside)).toEqual([])
    expect(await exists(t.path)).toBe(true)
  })

  it('dangling symlink → exit 1', async () => {
    const home = await tmpRoot()
    const { t } = await make({ home })
    await symlink(join(home, 'nope'), join(home, 'link'))
    const err = await t.commitTo(join(home, 'link')).catch((e: unknown) => e)
    expect((err as WizardExit).code).toBe(1)
  })

  it('cleanup is idempotent', async () => {
    const { t } = await make()
    await t.cleanup()
    await t.cleanup()
    expect(await exists(t.path)).toBe(false)
  })
})

describe('toExit', () => {
  const e = (c: string) => Object.assign(new Error(c), { code: c })
  it('maps errno to exit codes', () => {
    expect((toExit(e('EPERM'), '/t') as WizardExit).code).toBe(13)
    expect((toExit(e('ENOSPC'), '/t') as WizardExit).code).toBe(28)
  })
  it('passes WizardExit and unknown errors through', () => {
    const w = new WizardExit(2, 'x')
    expect(toExit(w, '/t')).toBe(w)
    const o = e('EIO')
    expect(toExit(o, '/t')).toBe(o)
  })
})
