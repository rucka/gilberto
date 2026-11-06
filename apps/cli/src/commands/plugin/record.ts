import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

export type PluginRecord = { files: Record<string, string> }

export const recordRel = (name: string): string => join('anatomy', '.plugins', `${name}.json`)

export const sha256 = (data: Buffer | string): string =>
  createHash('sha256').update(data).digest('hex')

export function readRecord(vault: string, name: string): PluginRecord | undefined {
  try {
    const rec = JSON.parse(readFileSync(join(vault, recordRel(name)), 'utf8')) as PluginRecord
    return rec && typeof rec.files === 'object' && rec.files ? rec : undefined
  } catch {
    return undefined
  }
}
