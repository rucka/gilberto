import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const root = fileURLToPath(new URL('../../../../../', import.meta.url))
const prettier = `${root}tools/prettier-config/node_modules/.bin/prettier`

const different = (files: string[]) => {
  try {
    execFileSync(prettier, ['--list-different', ...files], { cwd: root, encoding: 'utf8' })
    return []
  } catch (e) {
    return String((e as { stdout?: string }).stdout)
      .split('\n')
      .filter(Boolean)
  }
}

const dir = 'apps/cli/src/commands/install'

describe('r1-4 prettier-clean r1 fix files', () => {
  it('r1-4 parser.ts is prettier-clean', () => {
    expect(different([`${dir}/parser.ts`])).toEqual([])
  })
  it('r1-4 04-skeleton.ts is prettier-clean', () => {
    expect(different([`${dir}/wizard/steps/04-skeleton.ts`])).toEqual([])
  })
  it('r1-4 control: untouched file is prettier-clean', () => {
    expect(different([`${dir}/handler.ts`])).toEqual([])
  })
})
