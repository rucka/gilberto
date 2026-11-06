import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

export const PLUGINS_FILE = join('anatomy', 'plugins.md')

export type PluginRow = { name: string; version: string; installed: string }

export const registryPath = (vault: string): string => join(vault, PLUGINS_FILE)

export function assertVault(vault: string): void {
  if (!existsSync(registryPath(vault)))
    throw new Error(`not a vault: ${PLUGINS_FILE} not found in ${vault}`)
}

const cells = (line: string): string[] =>
  line
    .trim()
    .replace(/^\||\|$/g, '')
    .split('|')
    .map(c => c.trim())

const isRow = (line: string): boolean => line.trimStart().startsWith('|')
const isData = (line: string): boolean => {
  if (!isRow(line)) return false
  const [first = '', , third = ''] = cells(line)
  return !/^-+$/.test(first) && !(first === 'Plugin' && third === 'Installed')
}

const read = (vault: string): string => {
  assertVault(vault)
  return readFileSync(registryPath(vault), 'utf8')
}

export function readRows(vault: string): PluginRow[] {
  return read(vault)
    .split('\n')
    .filter(isData)
    .map(l => {
      const [name = '', version = '', installed = ''] = cells(l)
      return { name, version, installed }
    })
}

export const hasPlugin = (vault: string, name: string): boolean =>
  readRows(vault).some(r => r.name === name)

export function addRow(vault: string, row: PluginRow): void {
  const lines = read(vault).split('\n')
  const line = `| ${row.name} | ${row.version} | ${row.installed} |`
  const last = lines.map(isRow).lastIndexOf(true)
  if (last >= 0) lines.splice(last + 1, 0, line)
  else lines.push(line)
  writeFileSync(registryPath(vault), lines.join('\n'))
}

export function removeRow(vault: string, name: string): boolean {
  const lines = read(vault).split('\n')
  const i = lines.findIndex(l => isData(l) && cells(l)[0] === name)
  if (i < 0) return false
  lines.splice(i, 1)
  writeFileSync(registryPath(vault), lines.join('\n'))
  return true
}
