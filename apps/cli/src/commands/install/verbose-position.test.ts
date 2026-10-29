import { afterEach, describe, expect, it, vi } from 'vitest'
import { createProgram } from '../../cli.js'
import { installCommand } from './index.js'

afterEach(() => vi.restoreAllMocks())

const parsed = async (...args: string[]) => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  const parse = vi.spyOn(installCommand, 'parse')
  await createProgram().parseAsync(['node', 'g', '--no-banner', ...args])
  return parse.mock.results[0]?.value
}

describe('install --verbose before the subcommand (r0-1)', () => {
  it('root -v before install reaches install parse', async () => {
    expect(await parsed('-v', 'install')).toMatchObject({ command: 'install', verbose: true })
  })

  it('root --verbose before install keeps the target', async () => {
    expect(await parsed('--verbose', 'install', '/t')).toMatchObject({
      verbose: true,
      target: '/t',
    })
  })
})
