import { describe, expect, it } from 'vitest'
import { parseInstallCommand, parseSeedTopics } from './parser.js'
import { WizardExit } from './wizard/exit.js'

describe('parseSeedTopics', () => {
  it('parses multiple pillars', () => {
    expect(parseSeedTopics('intelligence=ai,product;pulse=health')).toEqual({
      intelligence: ['ai', 'product'],
      pulse: ['health'],
    })
  })

  it('tolerates spaces and trailing separator', () => {
    expect(parseSeedTopics(' pulse = a , b ;')).toEqual({ pulse: ['a', 'b'] })
  })

  it.each([
    ['unknown pillar', 'me=x', 'unknown pillar "me"'],
    ['no list', 'pulse', 'malformed entry "pulse"'],
    ['empty list', 'pulse=', 'malformed entry "pulse="'],
    ['double equals', 'pulse=a=b', 'malformed entry "pulse=a=b"'],
  ])('%s → exit 64 with actual and expected', (_n, raw, reason) => {
    const run = () => parseSeedTopics(raw)
    expect(run).toThrow(WizardExit)
    try {
      run()
    } catch (e) {
      const err = e as WizardExit
      expect(err.code).toBe(64)
      expect(err.message).toContain(reason)
      expect(err.message).toContain('pulse|intelligence|projects')
      expect(err.message).toContain(`got "${raw}"`)
    }
  })
})

describe('parseInstallCommand', () => {
  it('reads --non-interactive and --seed-topics', () => {
    expect(
      parseInstallCommand({ nonInteractive: true, seedTopics: 'projects=x' }, ['/p']),
    ).toMatchObject({ target: '/p', nonInteractive: true, seedTopics: { projects: ['x'] } })
  })
})
