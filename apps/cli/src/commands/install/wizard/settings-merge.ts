export const HOOK_IDS = ['gilberto.session-start', 'gilberto.pre-compact', 'gilberto.session-end'] as const

export type HookId = (typeof HOOK_IDS)[number]

export type OwnedHook = { id: HookId; event: string; command: string }

export type MergeResult = {
  merged: Record<string, unknown>
  mergedKeys: HookId[]
  conflict: boolean
}

type Entry = { type?: unknown; command?: unknown }
type Group = { matcher?: unknown; hooks?: Entry[] }

const isObj = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

const base = (cmd: string): string => cmd.split('/').pop() ?? cmd

export const ownerOf = (command: unknown): HookId | undefined =>
  typeof command === 'string'
    ? HOOK_IDS.find(id => base(command) === id || base(command).startsWith(`${id}.`))
    : undefined

export const mergeSettings = (
  existing: Record<string, unknown>,
  owned: readonly OwnedHook[],
): MergeResult => {
  const hooks: Record<string, unknown> = isObj(existing['hooks']) ? { ...existing['hooks'] } : {}
  let conflict = false
  for (const { id, event, command } of owned) {
    const groups = Array.isArray(hooks[event]) ? (hooks[event] as Group[]) : []
    const kept: Group[] = []
    for (const g of groups) {
      const entries = Array.isArray(g?.hooks) ? g.hooks : []
      const rest = entries.filter(e => {
        if (ownerOf(e?.command) !== id) return true
        if (e.command !== command) conflict = true
        return false
      })
      if (rest.length === entries.length) kept.push(g)
      else if (rest.length) kept.push({ ...g, hooks: rest })
    }
    kept.push({ matcher: '', hooks: [{ type: 'command', command }] })
    hooks[event] = kept
  }
  return {
    merged: { ...existing, hooks },
    mergedKeys: owned.map(o => o.id),
    conflict,
  }
}
