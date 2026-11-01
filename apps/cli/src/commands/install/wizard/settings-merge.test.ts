import { describe, expect, it } from 'vitest'
import { HOOK_IDS, mergeSettings, ownerOf, type OwnedHook } from './settings-merge.js'

const owned: OwnedHook[] = [
  { id: 'gilberto.session-start', event: 'SessionStart', command: '/v/.claude/hooks/gilberto.session-start.sh' },
  { id: 'gilberto.pre-compact', event: 'PreCompact', command: '/v/.claude/hooks/gilberto.pre-compact.sh' },
  { id: 'gilberto.session-end', event: 'SessionEnd', command: '/v/.claude/hooks/gilberto.session-end.sh' },
]
const entry = (command: string) => ({ matcher: '', hooks: [{ type: 'command', command }] })

describe('mergeSettings', () => {
  it('empty → three hooks, no conflict', () => {
    const r = mergeSettings({}, owned)
    expect(r.conflict).toBe(false)
    expect(r.mergedKeys).toEqual([...HOOK_IDS])
    expect(r.merged).toEqual({
      hooks: {
        SessionStart: [entry(owned[0]!.command)],
        PreCompact: [entry(owned[1]!.command)],
        SessionEnd: [entry(owned[2]!.command)],
      },
    })
  })

  it('user-only: unrelated keys and hooks preserved', () => {
    const user = {
      mcpServers: { a: { command: 'x' } },
      hooks: { SessionStart: [entry('/usr/bin/mine')], Stop: [entry('/usr/bin/stop')] },
    }
    const r = mergeSettings(user, owned)
    expect(r.conflict).toBe(false)
    expect(r.merged['mcpServers']).toEqual(user.mcpServers)
    const h = r.merged['hooks'] as Record<string, unknown[]>
    expect(h['Stop']).toEqual(user.hooks.Stop)
    expect(h['SessionStart']).toEqual([entry('/usr/bin/mine'), entry(owned[0]!.command)])
  })

  it('gilberto-only same command → idempotent', () => {
    const once = mergeSettings({}, owned)
    const twice = mergeSettings(once.merged, owned)
    expect(twice.merged).toEqual(once.merged)
    expect(twice.conflict).toBe(false)
  })

  it('collision: owned id with different command → conflict, replaced, user entry kept in same group', () => {
    const user = {
      hooks: {
        SessionEnd: [
          {
            matcher: 'x',
            hooks: [
              { type: 'command', command: '/old/gilberto.session-end.sh' },
              { type: 'command', command: '/usr/bin/mine' },
            ],
          },
        ],
      },
    }
    const r = mergeSettings(user, owned)
    expect(r.conflict).toBe(true)
    const h = r.merged['hooks'] as Record<string, unknown[]>
    expect(h['SessionEnd']).toEqual([
      { matcher: 'x', hooks: [{ type: 'command', command: '/usr/bin/mine' }] },
      entry(owned[2]!.command),
    ])
  })

  it('does not mutate input; tolerates malformed hooks', () => {
    const user = { hooks: { SessionStart: 'nope' } }
    const copy = structuredClone(user)
    mergeSettings(user, owned)
    expect(user).toEqual(copy)
    expect(mergeSettings({ hooks: [] }, owned).mergedKeys).toHaveLength(3)
  })

  it('ownerOf recognizes only gilberto ids', () => {
    expect(ownerOf('/a/gilberto.pre-compact.sh')).toBe('gilberto.pre-compact')
    expect(ownerOf('/a/other.sh')).toBeUndefined()
    expect(ownerOf(42)).toBeUndefined()
  })
})
