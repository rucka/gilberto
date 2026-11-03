import { mkdtempSync, readdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CommandDeps } from '../types.js'
import { handlePluginCommand } from './handler.js'
import { parsePluginCommand } from './parser.js'
import { resolveSource } from './source.js'
import { gitRepo, makePlugin, makeVault, pillarFiles, pillarManifest, write } from './testkit.js'

let tmpRoot = ''
const leftovers = (): string[] => readdirSync(tmpRoot).filter(n => n.startsWith('gilberto-plugin-'))

beforeEach(() => {
  tmpRoot = mkdtempSync(join(tmpdir(), 'cleanup-tmp-'))
  vi.stubEnv('TMPDIR', tmpRoot)
})
afterEach(() => vi.unstubAllEnvs())

const deps = (cwd: string): CommandDeps => {
  const noop = (): void => undefined
  return {
    cwd,
    env: {},
    write: noop,
    logger: { debug: noop, info: noop, warn: noop, error: noop },
  }
}

const install = (cwd: string, url: string) =>
  handlePluginCommand(parsePluginCommand({}, ['install', url]), deps(cwd))

describe('AC2 temp clone removed', () => {
  it('W-r0-3a handler install url success -> no gilberto-plugin-* temp left', async () => {
    const url = gitRepo(makePlugin(pillarManifest('remote'), pillarFiles))
    await install(makeVault(), url)
    expect(leftovers()).toEqual([])
  })

  it('W-r0-3b handler install url failure (invalid manifest) -> no temp left', async () => {
    const url = gitRepo(makePlugin({ name: 'bad' }))
    await expect(install(makeVault(), url)).rejects.toThrow(/plugin\.json/)
    expect(leftovers()).toEqual([])
  })

  it('B-r0-3c resolveSource clone failure -> no temp left', () => {
    expect(() => resolveSource('file:///does/not/exist.git')).toThrow(/git clone failed/)
    expect(leftovers()).toEqual([])
  })

  it('B-r0-3d resolveSource repo without manifest -> no temp left', () => {
    const parent = mkdtempSync(join(tmpdir(), 'empty-'))
    write(parent, 'README.md', 'x')
    expect(() => resolveSource(gitRepo(parent))).toThrow(/no plugin found/)
    expect(leftovers()).toEqual([])
  })

  it('C-r0-3e control: temp dir does exist while source is live, gone after cleanup', () => {
    const s = resolveSource(gitRepo(makePlugin(pillarManifest('live'), pillarFiles)))
    expect(leftovers()).toHaveLength(1)
    s.cleanup()
    expect(leftovers()).toEqual([])
  })
})
