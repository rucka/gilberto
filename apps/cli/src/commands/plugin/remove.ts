import { existsSync, readdirSync, readFileSync, rmdirSync, rmSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'
import { readRecord, recordRel, sha256 } from './record.js'
import { assertVault, hasPlugin, removeRow } from './registry.js'

export type RemoveOptions = { purge: boolean; dryRun: boolean }
export type RemoveResult = { name: string; removed: string[]; kept: string[]; dryRun: boolean }

const ROOTS = [join('anatomy', 'playbooks'), join('anatomy', 'templates')]

function prune(vault: string, rel: string): void {
  for (let d = dirname(rel); !ROOTS.includes(d) && d !== '.' && d !== 'anatomy'; d = dirname(d)) {
    const abs = join(vault, d)
    if (!existsSync(abs) || readdirSync(abs).length) return
    rmdirSync(abs)
  }
}

export function removePlugin(vault: string, name: string, opts: RemoveOptions): RemoveResult {
  assertVault(vault)
  if (!hasPlugin(vault, name)) throw new Error(`plugin "${name}" not installed`)
  const files = Object.entries(readRecord(vault, name)?.files ?? {}).filter(
    ([rel]) => basename(rel) !== 'core.md' && existsSync(join(vault, rel)),
  )
  const removed: string[] = []
  const kept: string[] = []
  for (const [rel, hash] of files)
    (opts.purge || sha256(readFileSync(join(vault, rel))) === hash ? removed : kept).push(rel)
  const result: RemoveResult = { name, removed, kept, dryRun: opts.dryRun }
  if (opts.dryRun) return result
  for (const rel of removed) {
    rmSync(join(vault, rel))
    prune(vault, rel)
  }
  rmSync(join(vault, recordRel(name)), { force: true })
  removeRow(vault, name)
  return result
}
