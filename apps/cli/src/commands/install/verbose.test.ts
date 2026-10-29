import { afterEach, describe, expect, it, vi } from 'vitest'
import { createProgram } from '../../cli.js'
import { installCommand } from './index.js'

afterEach(() => vi.restoreAllMocks())

const parsed = async (...args: string[]) => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  vi.spyOn(installCommand, 'handle').mockResolvedValue(undefined)
  const parse = vi.spyOn(installCommand, 'parse')
  await createProgram().parseAsync(['node', 'g', '--no-banner', ...args])
  return parse.mock.results[0]?.value
}

describe('install --verbose reachability (r0-1)', () => {
  it('short flag -v reaches install parse', async () => {
    expect(await parsed('install', '-v')).toMatchObject({ command: 'install', verbose: true })
  })

  it('long flag reaches install parse with target', async () => {
    expect(await parsed('install', '--verbose', '/t')).toMatchObject({
      verbose: true,
      target: '/t',
    })
  })
})
