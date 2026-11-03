import { chmodSync, cpSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

chmodSync(fileURLToPath(new URL('../dist/cli.js', import.meta.url)), 0o755)

const dest = fileURLToPath(new URL('../plugins', import.meta.url))
rmSync(dest, { recursive: true, force: true })
cpSync(fileURLToPath(new URL('../../../plugins', import.meta.url)), dest, {
  recursive: true,
  filter: src => !src.endsWith('.DS_Store'),
})
